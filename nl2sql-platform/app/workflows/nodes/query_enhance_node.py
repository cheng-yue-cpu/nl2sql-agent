"""
3. QueryEnhanceNode - 查询增强节点

完全参考 DataAgent 项目的 QueryEnhanceNode 实现：
- 基于多轮对话上下文重写查询
- 结合 evidence 信息进行业务翻译
- 查询改写和扩展
- 返回结构化输出 (JSON 格式)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：QueryEnhanceNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.context_manager import get_context_manager
from app.config import settings
from pydantic import BaseModel
import structlog
import json

logger = structlog.get_logger()


class QueryEnhanceOutput(BaseModel):
    """
    查询增强输出 DTO
    
    参考 DataAgent 的 QueryEnhanceOutputDTO 设计
    """
    canonical_query: str  # 重写后的标准查询
    original_query: str  # 原始查询
    rewrite_reason: str  # 重写理由
    is_rewritten: bool  # 是否被重写


async def query_enhance_node(state: NL2SQLState) -> dict:
    """
    查询增强节点
    
    参考 DataAgent 的实现流程：
    1. 获取用户输入
    2. 获取多轮对话上下文
    3. 获取 evidence 信息
    4. 构建查询增强 Prompt
    5. 调用 LLM
    6. 解析 JSON 输出
    7. 返回重写后的查询
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含查询增强结果
    """
    # 获取用户输入
    user_input = state.get("user_query", "")
    logger.info(f"User input for query enhance: {user_input[:100]}")
    
    # 获取多轮对话上下文
    thread_id = state.get("thread_id", "")
    context_manager = get_context_manager()
    multi_turn_context = context_manager.build_context(thread_id)
    
    # 获取 evidence 信息
    evidence = state.get("evidence", "")
    
    logger.debug(
        "Query enhance context",
        multi_turn_context=multi_turn_context[:200] if multi_turn_context != "(无)" else "(无)",
        evidence=evidence[:100] if evidence else "无"
    )
    
    # 构建查询增强 Prompt
    prompt = _build_query_enhance_prompt(multi_turn_context, user_input, evidence)
    logger.debug("Built query enhance prompt")
    
    # 调用 LLM 进行查询增强（启用流式）
    llm_output = await _call_llm(prompt, streaming=True)
    
    # 解析 JSON 输出
    enhance_output = _parse_enhance_output(llm_output, user_input)
    
    if enhance_output is None:
        logger.warning("Failed to parse enhance output, using original query")
        enhance_output = QueryEnhanceOutput(
            canonical_query=user_input,
            original_query=user_input,
            rewrite_reason="解析失败，使用原查询",
            is_rewritten=False
        )
    
    logger.info(
        "Query enhance completed",
        original=enhance_output.original_query[:50],
        canonical=enhance_output.canonical_query[:50],
        is_rewritten=enhance_output.is_rewritten
    )
    
    return {
        "query_enhance_node_output": enhance_output,
        "canonical_query": enhance_output.canonical_query
    }


def _build_query_enhance_prompt(
    multi_turn_context: str,
    user_input: str,
    evidence: str
) -> str:
    """
    构建查询增强 Prompt
    
    从独立 Prompt 文件加载模板
    
    Args:
        multi_turn_context: 多轮对话上下文
        user_input: 用户输入
        evidence: 业务知识证据
        
    Returns:
        str: Prompt
    """
    from app.services.prompt_loader import render_prompt
    
    return render_prompt(
        'query-enhancement',
        multi_turn_context=multi_turn_context,
        user_input=user_input,
        evidence=evidence if evidence else "无"
    )


async def _call_llm(prompt: str, streaming: bool = False) -> str:
    """
    调用 LLM
    
    Args:
        prompt: Prompt
        
    Returns:
        str: LLM 输出
    """
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    
    if streaming:
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=0,
            zhipuai_api_key=settings.zhipuai_api_key,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        
        full_response = []
        async for chunk in llm.astream(prompt):
            if chunk.content:
                full_response.append(chunk.content)
        
        return "".join(full_response).strip()
    else:
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=0,  # 确定性输出
            zhipuai_api_key=settings.zhipuai_api_key,
        )
        
        response = await llm.ainvoke(prompt)
        return response.content.strip()


def _parse_enhance_output(llm_output: str, original_query: str) -> QueryEnhanceOutput:
    """
    解析查询增强输出
    
    参考 DataAgent 的 JsonParseUtil.tryConvertToObject
    
    Args:
        llm_output: LLM 输出
        original_query: 原始查询
        
    Returns:
        QueryEnhanceOutput: 查询增强输出 DTO
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
        return QueryEnhanceOutput(
            canonical_query=data.get("canonical_query", original_query),
            original_query=data.get("original_query", original_query),
            rewrite_reason=data.get("rewrite_reason", ""),
            is_rewritten=data.get("is_rewritten", False)
        )
        
    except Exception as e:
        logger.error(f"Failed to parse enhance output: {str(e)}")
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
