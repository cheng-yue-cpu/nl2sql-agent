"""
LLM 服务模块

提供统一的 LLM 调用接口，支持流式输出
"""
from app.config import settings
import structlog
from typing import AsyncGenerator

logger = structlog.get_logger()


async def stream_llm_tokens(prompt: str, temperature: float = 0) -> AsyncGenerator[str, None]:
    """
    流式调用 LLM，逐 token 返回
    
    Args:
        prompt: Prompt
        temperature: 温度 (0-1)
        
    Yields:
        str: 每个 token
    """
    from langchain_community.chat_models import ChatZhipuAI
    
    llm = ChatZhipuAI(
        model=settings.zhipuai_model,
        temperature=temperature,
        zhipuai_api_key=settings.zhipuai_api_key,
        streaming=True
    )
    
    async for chunk in llm.astream(prompt):
        if chunk.content:
            yield chunk.content


async def call_llm(prompt: str, streaming: bool = False) -> str:
    """
    调用 LLM
    
    Args:
        prompt: Prompt
        streaming: 是否流式输出
        
    Returns:
        str: LLM 输出
    """
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    
    if streaming:
        logger.info("使用流式调用 LLM")
        
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=0,
            zhipuai_api_key=settings.zhipuai_api_key,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )
        
        # 收集完整响应 (修正：不使用 await)
        full_response = []
        async for chunk in llm.astream(prompt):
            if chunk.content:
                full_response.append(chunk.content)
        
        return "".join(full_response).strip()
    else:
        logger.info("使用同步调用 LLM")
        
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=0,
            zhipuai_api_key=settings.zhipuai_api_key,
        )
        
        response = await llm.ainvoke(prompt)
        return response.content.strip()


async def stream_llm_tokens_with_temperature(
    prompt: str, 
    temperature: float = 0.1
) -> AsyncGenerator[str, None]:
    """
    流式调用 LLM（可指定温度），逐 token 返回
    
    Args:
        prompt: Prompt
        temperature: 温度 (0-1)
        
    Yields:
        str: 每个 token
    """
    from langchain_community.chat_models import ChatZhipuAI
    
    llm = ChatZhipuAI(
        model=settings.zhipuai_model,
        temperature=temperature,
        zhipuai_api_key=settings.zhipuai_api_key,
        streaming=True
    )
    
    async for chunk in llm.astream(prompt):
        if chunk.content:
            yield chunk.content


async def call_llm_with_temperature(
    prompt: str, 
    temperature: float = 0.1,
    streaming: bool = False
) -> str:
    """
    调用 LLM（可指定温度）
    
    Args:
        prompt: Prompt
        temperature: 温度 (0-1)
        streaming: 是否流式输出（收集完整响应）
        
    Returns:
        str: LLM 输出
    """
    from langchain_community.chat_models import ChatZhipuAI
    from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    
    if streaming:
        logger.info(f"使用流式调用 LLM (temperature={temperature})")
        
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=temperature,
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
        logger.info(f"使用同步调用 LLM (temperature={temperature})")
        
        llm = ChatZhipuAI(
            model=settings.zhipuai_model,
            temperature=temperature,
            zhipuai_api_key=settings.zhipuai_api_key,
        )
        
        response = await llm.ainvoke(prompt)
        return response.content.strip()
