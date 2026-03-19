"""
1. IntentRecognitionNode - 意图识别节点

完全参考 DataAgent 项目的 IntentRecognitionNode 实现：
- 使用 LLM 进行意图识别
- 支持多轮对话上下文注入
- 返回结构化输出 (JSON 格式)
- 支持流式输出
- 使用独立 Prompt 文件

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：IntentRecognitionNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.context_manager import get_context_manager
from app.services.llm_service import call_llm
from app.services.prompt_loader import render_prompt
from app.config import settings
from pydantic import BaseModel
import structlog
import json

logger = structlog.get_logger()


class IntentRecognitionOutput(BaseModel):
    """
    意图识别输出 DTO
    
    参考 DataAgent 的 IntentRecognitionOutputDTO 设计
    """
    need_analysis: bool  # 是否需要分析
    intent_type: str  # 意图类型：DATA_ANALYSIS 或 CHAT
    confidence: float  # 置信度 (0-1)
    reason: str  # 判断理由


async def intent_recognition_node(state: NL2SQLState) -> dict:
    """
    意图识别节点
    
    参考 DataAgent 的实现流程：
    1. 获取用户输入
    2. 获取多轮对话上下文
    3. 构建意图识别 Prompt
    4. 调用 LLM
    5. 解析 JSON 输出
    6. 开始新对话轮（如果需要分析）
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含意图识别结果
    """
    # 获取用户输入
    user_input = state.get("user_query", "")
    logger.info(f"User input for intent recognition: {user_input[:100]}")
    
    # 获取多轮对话上下文
    thread_id = state.get("thread_id", "")
    context_manager = get_context_manager()
    multi_turn_context = context_manager.build_context(thread_id)
    
    logger.debug(f"Multi-turn context: {multi_turn_context[:200] if multi_turn_context != '(无)' else '(无)'}")
    
    # 构建意图识别 Prompt
    prompt = _build_intent_recognition_prompt(multi_turn_context, user_input)
    logger.debug("Built intent recognition prompt")
    
    # 调用 LLM 进行意图识别（启用流式）
    llm_output = await call_llm(prompt, streaming=True)
    
    # 解析 JSON 输出
    intent_output = _parse_intent_output(llm_output)
    
    if intent_output is None:
        logger.warning("Failed to parse intent output, defaulting to analysis")
        intent_output = IntentRecognitionOutput(
            need_analysis=True,
            intent_type="DATA_ANALYSIS",
            confidence=0.5,
            reason="解析失败，默认需要分析"
        )
    
    logger.info(
        "Intent recognition completed",
        intent_type=intent_output.intent_type,
        need_analysis=intent_output.need_analysis,
        confidence=intent_output.confidence
    )
    
    # 如果需要分析，开始新对话轮
    if intent_output.need_analysis:
        context_manager.begin_turn(thread_id, user_input)
        logger.debug("Turn started in pending mode", thread_id=thread_id)
    
    return {
        "intent_recognition_output": intent_output
    }


def _build_intent_recognition_prompt(multi_turn_context: str, user_input: str) -> str:
    """
    构建意图识别 Prompt
    
    从独立 Prompt 文件加载模板
    
    Args:
        multi_turn_context: 多轮对话上下文
        user_input: 用户输入
        
    Returns:
        str: Prompt
    """
    return render_prompt(
        'intent-recognition',
        multi_turn_context=multi_turn_context,
        user_input=user_input
    )


# 已迁移到 app/services/llm_service.py


def _parse_intent_output(llm_output: str) -> IntentRecognitionOutput:
    """
    解析意图识别输出
    
    参考 DataAgent 的 JsonParseUtil.tryConvertToObject
    
    Args:
        llm_output: LLM 输出
        
    Returns:
        IntentRecognitionOutput: 意图识别输出 DTO
    """
    try:
        # 尝试提取 JSON
        json_str = _extract_json(llm_output)
        if not json_str:
            logger.warning(f"No JSON found in output: {llm_output[:100]}")
            return None
        
        # 解析 JSON
        data = json.loads(json_str)
        
        # 转换为 DTO
        return IntentRecognitionOutput(
            need_analysis=data.get("need_analysis", False),
            intent_type=data.get("intent_type", "CHAT"),
            confidence=data.get("confidence", 0.5),
            reason=data.get("reason", "")
        )
        
    except Exception as e:
        logger.error(f"Failed to parse intent output: {str(e)}")
        return None


def _extract_json(text: str) -> str:
    """
    从文本中提取 JSON
    
    Args:
        text: 原始文本
        
    Returns:
        str: JSON 字符串
    """
    # 尝试找到 JSON 块
    start = text.find('{')
    end = text.rfind('}') + 1
    
    if start != -1 and end > start:
        return text[start:end]
    
    return text
