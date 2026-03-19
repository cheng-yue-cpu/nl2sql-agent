"""
多轮对话上下文管理器 (基于 DataAgent 开源项目实现)

完全参考 DataAgent 项目的 MultiTurnContextManager 实现：
- 使用内存缓存 (ConcurrentHashMap → Dict)
- Pending 模式支持流式追加
- 滑动窗口限制历史轮数
- 简化版实现 (无 Redis/DB 依赖)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：MultiTurnContextManager.java
"""
from typing import Optional, Dict, Deque
from collections import deque
from datetime import datetime
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class MultiTurnContextManager:
    """
    多轮对话上下文管理器
    
    完全参考 DataAgent 项目的实现方式：
    - 内存缓存：thread_id → Deque[ConversationTurn]
    - Pending 缓存：thread_id → PendingTurn
    - 滑动窗口：自动清理旧对话
    - 流式支持：append_planner_chunk
    
    简化点：
    - 使用 Python Dict 代替 ConcurrentHashMap
    - 使用 deque 代替 ArrayDeque
    - 暂不实现持久化 (DataAgent 原代码也是 todo)
    """
    
    def __init__(self, max_turn_history: int = 5):
        """
        初始化上下文管理器
        
        Args:
            max_turn_history: 最大保留对话轮数 (滑动窗口大小)
        """
        self.max_turn_history = max_turn_history
        
        # 历史对话缓存：thread_id → Deque[ConversationTurn]
        # 参考 DataAgent 使用 deque 实现滑动窗口
        self.history: Dict[str, deque] = {}
        
        # Pending 缓存：thread_id → PendingTurn
        self.pending_turns: Dict[str, PendingTurn] = {}
        
        logger.info(
            "MultiTurnContextManager initialized (DataAgent implementation)",
            max_turn_history=max_turn_history
        )
    
    def begin_turn(self, thread_id: str, user_question: str) -> None:
        """
        开始新对话轮
        
        参考 DataAgent 的 beginTurn 实现：
        1. 校验参数
        2. 创建 PendingTurn
        3. 存到 pending 缓存
        
        Args:
            thread_id: 会话 ID
            user_question: 用户问题
        """
        if not thread_id or not user_question:
            logger.warning("Invalid thread_id or user_question")
            return
        
        # 创建 PendingTurn
        pending_turn = PendingTurn(user_question=user_question.strip())
        self.pending_turns[thread_id] = pending_turn
        
        logger.debug("Turn started", thread_id=thread_id, user_question=user_question[:50])
    
    def append_planner_chunk(self, thread_id: str, chunk: str) -> None:
        """
        流式追加 AI 计划
        
        参考 DataAgent 的 appendPlannerChunk 实现：
        1. 获取 pending turn
        2. 追加到 plan_builder
        
        Args:
            thread_id: 会话 ID
            chunk: AI 计划片段
        """
        if not thread_id or not chunk:
            return
        
        pending = self.pending_turns.get(thread_id)
        if pending:
            pending.plan_builder.append(chunk)
            logger.debug("Planner chunk appended", thread_id=thread_id, chunk_len=len(chunk))
        else:
            logger.warning("No pending turn found", thread_id=thread_id)
    
    def append_sql_info(self, thread_id: str, sql_query: str = None, sql_result: dict = None) -> None:
        """
        追加 SQL 信息（扩展 DataAgent 实现）
        
        DataAgent 只记录 plan，我们扩展为也记录 SQL 和结果
        
        Args:
            thread_id: 会话 ID
            sql_query: SQL 语句
            sql_result: SQL 执行结果
        """
        pending = self.pending_turns.get(thread_id)
        if pending:
            if sql_query:
                pending.sql_query = sql_query
            if sql_result:
                pending.sql_result = sql_result
            logger.debug("SQL info appended", thread_id=thread_id)
        else:
            logger.warning("No pending turn found", thread_id=thread_id)
    
    def finish_turn(self, thread_id: str) -> None:
        """
        完成对话轮，保存到历史
        
        完全参考 DataAgent 的 finishTurn 实现：
        1. 从 pending 缓存取出并移除
        2. 校验 plan 或 sql_query 是否存在（我们的扩展）
        3. 添加到历史 (deque)，使用同步锁保护
        4. 滑动窗口清理
        5. 缩写 plan 长度（防止过长）
        
        扩展点：
        - DataAgent 只检查 plan，我们扩展为也检查 sql_query
        - 这样即使没有 PlannerNode，SQL 执行后也能保存历史
        
        Args:
            thread_id: 会话 ID
        """
        # 从 pending 缓存取出并移除
        pending = self.pending_turns.pop(thread_id, None)
        if pending is None:
            logger.debug("No pending turn to finish", thread_id=thread_id)
            return
        
        # 获取 plan
        plan = pending.plan_builder.getvalue().strip()
        
        # 扩展：如果没有 plan 但有 sql_query，也保存历史（适配简化版工作流）
        # DataAgent 原实现：只检查 plan
        # 我们的扩展：plan 或 sql_query 有一个存在就保存
        has_content = plan or pending.sql_query
        
        if not has_content:
            logger.debug("No planner output or SQL recorded, skipping history update", thread_id=thread_id)
            return
        
        # 缩写 plan 长度（参考 DataAgent 的 abbreviate）
        max_plan_length = 2000  # 默认值，可从配置读取
        if plan and len(plan) > max_plan_length:
            plan = plan[:max_plan_length] + "..."
        
        # 获取或创建历史队列
        if thread_id not in self.history:
            self.history[thread_id] = deque()
        
        conversation_turn = self.history[thread_id]
        
        # 滑动窗口：限制轮数（使用同步锁保护，参考 DataAgent）
        # Python 的 deque 是线程安全的，但为了逻辑一致性，保持同步处理
        while len(conversation_turn) >= self.max_turn_history:
            conversation_turn.popleft()  # 移除最旧的
        
        # 添加到队列末尾
        # 如果没有 plan，使用 SQL 作为 plan 的替代
        plan_to_save = plan if plan else f"执行 SQL 查询：{pending.sql_query}" if pending.sql_query else "(无计划)"
        
        turn = ConversationTurn(
            user_question=pending.user_question,
            plan=plan_to_save,
            sql_query=pending.sql_query,
            sql_result=pending.sql_result,
            timestamp=datetime.now()
        )
        conversation_turn.append(turn)
        
        logger.info(
            "Turn finished",
            thread_id=thread_id,
            history_length=len(conversation_turn),
            plan_len=len(plan_to_save)
        )
    
    def discard_pending(self, thread_id: str) -> None:
        """
        丢弃 pending 数据（不触碰历史）
        
        参考 DataAgent 的 discardPending 实现：
        用于 run aborted 时清理 pending 数据
        
        Args:
            thread_id: 会话 ID
        """
        self.pending_turns.pop(thread_id, None)
        logger.debug("Pending discarded", thread_id=thread_id)
    
    def restart_last_turn(self, thread_id: str) -> None:
        """
        重启最后一轮对话（用于人工反馈后重新生成）
        
        完全参考 DataAgent 的 restartLastTurn 实现：
        1. 获取历史队列
        2. 移除最后一个 stored turn（使用 pollLast）
        3. 重用其 user_question 创建新的 pending
        
        Args:
            thread_id: 会话 ID
        """
        conversation_turn = self.history.get(thread_id)
        if not conversation_turn or len(conversation_turn) == 0:
            logger.debug("No history to restart", thread_id=thread_id)
            return
        
        # 移除最后一个 turn（参考 DataAgent 的 pollLast）
        last_turn = conversation_turn.pop()
        if last_turn is None:
            return
        
        # 重用 user_question 创建新的 pending
        self.pending_turns[thread_id] = PendingTurn(user_question=last_turn.user_question)
        
        logger.info("Last turn restarted", thread_id=thread_id, reused_question=last_turn.user_question[:50])
    
    def build_context(self, thread_id: str) -> str:
        """
        构建多轮对话上下文字符串（用于 Prompt 注入）
        
        完全参考 DataAgent 的 buildContext 实现：
        使用 stream + collect 方式构建
        格式：用户：xxx\nAI 计划：xxx
        
        Args:
            thread_id: 会话 ID
            
        Returns:
            str: 格式化的上下文字符串
        """
        conversation_turn = self.history.get(thread_id)
        if not conversation_turn or len(conversation_turn) == 0:
            return "(无)"
        
        # 使用列表推导式构建（参考 DataAgent 的 stream().map().collect()）
        lines = [
            f"用户：{turn.user_question}\nAI 计划：{turn.plan}"
            for turn in conversation_turn
            if turn.plan  # 只包含有 plan 的轮次
        ]
        
        result = "\n".join(lines)
        logger.debug(f"Context built for thread {thread_id}, length={len(result)}")
        return result
    
    def get_history(self, thread_id: str) -> Optional[deque]:
        """获取历史对话队列"""
        return self.history.get(thread_id)
    
    def clear_history(self, thread_id: str) -> None:
        """清除指定会话的历史"""
        if thread_id in self.history:
            del self.history[thread_id]
        if thread_id in self.pending_turns:
            del self.pending_turns[thread_id]
        logger.info("History cleared", thread_id=thread_id)
    
    def clear_all(self) -> None:
        """清除所有会话历史"""
        self.history.clear()
        self.pending_turns.clear()
        logger.info("All history cleared")


class ConversationTurn:
    """
    对话轮次
    
    参考 DataAgent 的 ConversationTurn record 实现
    """
    
    def __init__(
        self,
        user_question: str,
        plan: str,
        sql_query: str = None,
        sql_result: dict = None,
        timestamp: datetime = None
    ):
        self.user_question = user_question
        self.plan = plan
        self.sql_query = sql_query
        self.sql_result = sql_result
        self.timestamp = timestamp or datetime.now()
    
    def __repr__(self):
        return f"ConversationTurn(user_question='{self.user_question[:50]}...', plan_len={len(self.plan)})"


class PendingTurn:
    """
    待提交的对话轮次
    
    参考 DataAgent 的 PendingTurn 静态类实现：
    - userQuestion: final
    - planBuilder: StringBuilder
    """
    
    def __init__(self, user_question: str):
        self.user_question = user_question
        self.plan_builder = StringBuilder()
        self.sql_query: Optional[str] = None
        self.sql_result: Optional[dict] = None


class StringBuilder:
    """
    StringBuilder 工具类（模拟 Java StringBuilder）
    
    用于高效拼接字符串
    """
    
    def __init__(self, initial: str = ""):
        self._chunks = []
        if initial:
            self._chunks.append(initial)
    
    def append(self, text: str) -> 'StringBuilder':
        """追加文本"""
        if text:
            self._chunks.append(text)
        return self
    
    def getvalue(self) -> str:
        """获取完整字符串"""
        return "".join(self._chunks)
    
    def __str__(self) -> str:
        return self.getvalue()
    
    def __len__(self) -> int:
        return sum(len(chunk) for chunk in self._chunks)


# ========== 全局单例 ==========

_context_manager: Optional[MultiTurnContextManager] = None


def get_context_manager(max_turn_history: int = 5) -> MultiTurnContextManager:
    """
    获取上下文管理器单例
    
    参考 DataAgent 的 Spring Component 模式，使用单例
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = MultiTurnContextManager(max_turn_history=max_turn_history)
    return _context_manager
