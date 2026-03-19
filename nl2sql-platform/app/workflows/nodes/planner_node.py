"""
7. PlannerNode - 任务规划节点

完全参考 DataAgent 项目的 PlannerNode 实现：
- 解析用户问题，生成多步骤执行计划
- 支持 NL2SQL 单步骤模式
- 支持复杂多步骤分析任务
- 使用独立 Prompt 文件 (planner.txt)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：PlannerNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.llm_service import call_llm_with_temperature
from app.services.prompt_loader import render_prompt, load_prompt
from app.config import settings
import structlog
import json
import re

logger = structlog.get_logger()


async def planner_node(state: NL2SQLState) -> dict:
    """
    任务规划节点
    
    参考 DataAgent 的实现流程：
    1. 检查是否为 NL2SQL 单步骤模式
    2. 获取用户查询和 Schema 信息
    3. 构建 Planner Prompt
    4. 调用 LLM 生成计划
    5. 解析并验证计划
    6. 返回执行计划
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含生成的执行计划
    """
    # 检查是否为 NL2SQL 单步骤模式
    is_only_nl2sql = state.get("is_only_nl2sql", True)
    
    logger.info("Starting planning", 
                is_only_nl2sql=is_only_nl2sql,
                user_query=state.get("user_query", "")[:100])
    
    # ========== 流式反馈：开始规划 ==========
    logger.info("开始生成任务执行计划...")
    
    try:
        # NL2SQL 单步骤模式：直接生成 SQL
        if is_only_nl2sql:
            logger.info("NL2SQL 单步骤模式，生成简单计划")
            plan = _create_nl2sql_plan()
            return {
                "plan": plan,
                "plan_validation_status": True,
                "plan_current_step": 1
            }
        
        # 多步骤分析模式：生成完整计划
        logger.info("多步骤分析模式，生成完整计划")
        
        # 获取规划所需信息
        canonical_query = state.get("canonical_query") or state.get("user_query", "")
        table_docs = state.get("table_documents", [])
        column_docs = state.get("column_documents", [])
        evidence = state.get("evidence", "")
        plan_validation_error = state.get("plan_validation_error", "")
        
        # 构建 Schema 字符串
        schema_str = _build_schema_string(table_docs, column_docs)
        
        # 从文件加载并渲染 Prompt
        prompt = render_prompt(
            'planner',
            user_question=canonical_query,
            schema=schema_str,
            evidence=evidence or "(无相关信息)",
            semantic_model="",
            plan_validation_error=_format_validation_error(plan_validation_error),
            format=_get_json_format_description()
        )
        
        logger.info(f"调用 LLM 生成计划，Prompt 长度：{len(prompt)}")
        
        # 调用 LLM（启用流式）
        plan_json = await call_llm_with_temperature(prompt, temperature=0.1, streaming=True)
        
        # 解析计划
        plan = _parse_plan(plan_json)
        
        logger.info(f"计划生成完成，共 {len(plan.get('execution_plan', []))} 个步骤")
        
        return {
            "plan": plan,
            "plan_validation_status": True,
            "plan_current_step": 1
        }
        
    except Exception as e:
        logger.error(f"计划生成失败：{str(e)}", exc_info=True)
        
        # 降级：返回简单计划
        logger.warning("计划生成失败，降级为 NL2SQL 单步骤模式")
        plan = _create_nl2sql_plan()
        
        return {
            "plan": plan,
            "plan_validation_status": False,
            "plan_validation_error": f"计划生成失败：{str(e)}",
            "plan_current_step": 1
        }


def _create_nl2sql_plan() -> dict:
    """创建 NL2SQL 单步骤计划"""
    return {
        "thought_process": "简单 NL2SQL 查询，直接生成 SQL",
        "execution_plan": [{
            "step": 1,
            "tool_to_use": "SQL_GENERATE_NODE",
            "tool_parameters": {
                "instruction": "根据用户问题生成 SQL 查询"
            }
        }]
    }


def _build_schema_string(table_docs: list, column_docs: list) -> str:
    """构建 Schema 字符串"""
    schema_parts = []
    for doc in table_docs:
        if hasattr(doc, 'page_content'):
            schema_parts.append(doc.page_content)
        else:
            schema_parts.append(str(doc))
    return "\n\n".join(schema_parts)


def _parse_plan(plan_json: str) -> dict:
    """解析计划 JSON"""
    try:
        # 提取 JSON
        start = plan_json.find('{')
        end = plan_json.rfind('}') + 1
        if start != -1 and end > start:
            plan_json = plan_json[start:end]
        return json.loads(plan_json)
    except Exception as e:
        logger.error(f"Failed to parse plan: {e}")
        return _create_nl2sql_plan()


def _format_validation_error(error: str) -> str:
    """格式化验证错误"""
    if error:
        return f"**用户反馈/计划验证错误**:\n{error}\n"
    return ""


def _get_json_format_description() -> str:
    """获取 JSON 格式描述"""
    return """
{
  "thought_process": "思考过程摘要",
  "execution_plan": [
    {
      "step": 1,
      "tool_to_use": "SQL_GENERATE_NODE",
      "tool_parameters": {
        "instruction": "具体指令"
      }
    }
  ]
}
"""
