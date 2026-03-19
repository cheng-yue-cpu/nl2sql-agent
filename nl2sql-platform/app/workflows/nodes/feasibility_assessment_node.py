"""
6. FeasibilityAssessmentNode - 可行性评估节点

完全参考 DataAgent 项目的 FeasibilityAssessmentNode 实现：
- 使用 LLM 评估问题是否可用当前 Schema 解答
- 检查表结构是否完整
- 不可答则提前结束
- 使用独立 Prompt 文件 (feasibility-assessment.txt)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：FeasibilityAssessmentNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.context_manager import get_context_manager
from app.services.prompt_loader import render_prompt
from app.config import settings
from langchain_community.chat_models import ChatZhipuAI
import structlog
import re

logger = structlog.get_logger()


async def feasibility_assessment_node(state: NL2SQLState) -> dict:
    """
    可行性评估节点
    
    参考 DataAgent 的实现流程：
    1. 获取规范化查询
    2. 获取 Schema 信息
    3. 获取多轮对话上下文
    4. 使用 LLM 评估可行性
    5. 解析 LLM 响应
    6. 根据评估结果返回
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含可行性评估结果
    """
    # ========== 流式反馈：开始可行性评估 ==========
    logger.info("开始可行性评估...")
    
    # 1. 获取规范化查询
    canonical_query = state.get("canonical_query") or state.get("user_query", "")
    user_query = state.get("user_query", "")
    
    # 2. 获取 Schema 信息
    table_documents = state.get("table_documents", [])
    column_documents = state.get("column_documents", [])
    recalled_schema = _build_schema_string(table_documents, column_documents)
    
    # 3. 获取多轮对话上下文
    thread_id = state.get("thread_id", "")
    context_manager = get_context_manager()
    multi_turn_context = context_manager.build_context(thread_id)
    
    # 获取 Evidence
    evidence = state.get("evidence", "")
    
    logger.info("可行性评估输入",
                query=canonical_query[:100],
                tables=len(table_documents),
                columns=len(column_documents))
    
    # 4. 从文件加载并渲染 Prompt
    prompt = render_prompt(
        'feasibility-assessment',
        canonical_query=canonical_query,
        recalled_schema=recalled_schema,
        evidence=evidence or "(无相关信息)",
        multi_turn=multi_turn_context or "(无多轮对话)"
    )
    
    # 5. 使用 LLM 评估可行性
    logger.info("使用 LLM 评估可行性...")
    
    llm = ChatZhipuAI(
        model=settings.zhipuai_model,
        temperature=0.1,  # 低温度，确保评估稳定
        zhipuai_api_key=settings.zhipuai_api_key,
    )
    
    response = await llm.ainvoke(prompt)
    
    # 6. 解析 LLM 响应
    assessment = _parse_assessment(response.content, user_query)
    
    logger.info("LLM 评估完成", 
                need_analysis=assessment.get("need_analysis"),
                requirement_type=assessment.get("requirement_type"),
                reason=assessment.get("reason", "")[:100])
    
    # 7. 根据评估结果返回
    if assessment.get("need_analysis", False):
        # ========== 流式反馈：可行性评估通过 ==========
        logger.info("可行性评估通过，问题可解答", 
                   requirement_type=assessment.get("requirement_type"),
                   tables=len(table_documents), 
                   columns=len(column_documents))
        
        return {
            "is_feasible": True,
            "feasibility_reason": f"Schema 完整，需求类型：{assessment.get('requirement_type')}，问题可解答",
            "requirement_type": assessment.get("requirement_type"),
            "requirement_content": assessment.get("requirement_content", canonical_query)
        }
    else:
        # ========== 流式反馈：可行性评估不通过 ==========
        reason = assessment.get("reason", "无法评估")
        logger.info("可行性评估不通过，问题无法解答", reason=reason[:200])
        
        return {
            "is_feasible": False,
            "feasibility_reason": reason,
            "requirement_type": assessment.get("requirement_type"),
            "requirement_content": assessment.get("requirement_content", "")
        }


def _build_schema_string(table_documents: list, column_documents: list) -> str:
    """
    构建 Schema 字符串
    
    Args:
        table_documents: 表文档列表
        column_documents: 列文档列表
        
    Returns:
        str: Schema 字符串
    """
    schema_parts = []
    
    for doc in table_documents:
        if hasattr(doc, 'page_content'):
            schema_parts.append(doc.page_content)
        else:
            schema_parts.append(str(doc))
    
    return "\n\n".join(schema_parts)


def _parse_assessment(llm_output: str, user_query: str) -> dict:
    """
    解析可行性评估输出
    
    参考 DataAgent 的解析逻辑
    
    Args:
        llm_output: LLM 输出
        user_query: 用户查询
        
    Returns:
        dict: 评估结果 {need_analysis, requirement_type, requirement_content, reason}
    """
    # 提取需求类型
    type_match = re.search(r'【需求类型】[：:]\s*《([^》]+)》', llm_output)
    requirement_type = type_match.group(1).strip() if type_match else ""
    
    # 提取需求内容
    content_match = re.search(r'【需求内容】[：:]\s*(.+?)(?:\n---|\n$|$)', llm_output, re.DOTALL)
    requirement_content = content_match.group(1).strip() if content_match else ""
    
    # 判断是否需要分析
    need_analysis = requirement_type == "数据分析"
    
    # 生成理由
    if need_analysis:
        reason = f"Schema 包含所需表结构，需求类型：{requirement_type}"
    elif requirement_type == "需要澄清":
        reason = f"需要用户澄清：{requirement_content}"
    elif requirement_type == "自由闲聊":
        reason = "与业务无关的闲聊"
    else:
        reason = f"未知需求类型：{requirement_type}"
    
    return {
        "need_analysis": need_analysis,
        "requirement_type": requirement_type,
        "requirement_content": requirement_content,
        "reason": reason
    }
