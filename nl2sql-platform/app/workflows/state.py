"""
LangGraph State 定义
参考 DataAgent 的 OverAllState 设计
"""
from typing import TypedDict, List, Annotated, Optional, Any, Dict
from langgraph.graph import add_messages
import operator


class NL2SQLState(TypedDict):
    """
    NL2SQL 工作流状态
    
    完全参考 DataAgent 的状态设计，包含：
    - 输入相关
    - 检索相关
    - 规划相关
    - SQL 相关
    - 控制相关
    """
    
    # ========== 输入相关 ==========
    messages: Annotated[List, add_messages]  # LangChain 消息历史
    user_query: str                           # 用户原始问题
    thread_id: str                            # 会话 ID
    agent_id: str                             # 智能体 ID
    multi_turn_context: Optional[str]         # 多轮对话上下文
    
    # ========== 检索相关 ==========
    evidence: Optional[str]                   # RAG 检索结果
    canonical_query: Optional[str]            # 重写后的查询
    table_documents: List                     # 表结构文档
    column_documents: List                    # 列信息文档
    schema_relations: Optional[Dict]          # 表关系分析结果
    
    # ========== 规划相关 ==========
    is_feasible: Optional[bool]               # 可行性评估结果
    plan: Optional[Dict]                      # 执行计划 (JSON)
    plan_validation_status: Optional[bool]    # 计划校验状态
    plan_validation_error: Optional[str]      # 计划校验错误
    plan_current_step: int                    # 当前执行步骤 (从 1 开始)
    plan_next_node: Optional[str]             # 下一个节点
    plan_repair_count: int                    # 计划修复次数
    is_only_nl2sql: bool                      # 是否纯 NL2SQL 模式 (单步骤)
    
    # ========== SQL 相关 ==========
    generated_sql: Optional[str]              # 生成的 SQL
    sql_validation: Optional[Dict]            # SQL 校验结果
    sql_result: Optional[Any]                 # SQL 执行结果
    sql_generate_count: int                   # SQL 生成次数
    sql_regenerate_reason: Optional[str]      # 重新生成 SQL 的原因
    
    # ========== 语义一致性 ==========
    semantic_consistency_output: Optional[Dict]  # 语义一致性校验结果
    
    # ========== 控制相关 ==========
    is_only_nl2sql: bool                      # 是否纯 NL2SQL 模式
    human_review_enabled: bool                # 是否启用人工复核
    human_feedback_data: Optional[Dict]       # 人工反馈数据
    intent_recognition_output: Optional[bool] # 意图识别结果
    feasibility_assessment_output: Optional[bool]  # 可行性评估结果
    
    # ========== 错误处理 ==========
    error: Optional[str]                      # 错误信息
