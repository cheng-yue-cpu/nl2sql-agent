"""
11. SemanticConsistencyNode - 语义一致性校验节点

完全参考 DataAgent 项目的 SemanticConsistencyNode 实现：
- 校验生成的 SQL 是否与用户意图语义一致
- 检查表名、字段名、条件、聚合等
- 提供改进建议
- 使用独立 Prompt 文件 (semantic-consistency.txt)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：SemanticConsistencyNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.llm_service import call_llm
from app.services.prompt_loader import render_prompt
from app.config import settings
import structlog
import json
import re

logger = structlog.get_logger()


class ConsistencyOutput:
    """语义一致性校验输出"""
    def __init__(self, is_consistent: bool, consistency_score: float, 
                 issues: list, suggestion: str):
        self.is_consistent = is_consistent
        self.consistency_score = consistency_score
        self.issues = issues
        self.suggestion = suggestion
    
    def to_dict(self) -> dict:
        return {
            "is_consistent": self.is_consistent,
            "consistency_score": self.consistency_score,
            "issues": self.issues,
            "suggestion": self.suggestion
        }


async def semantic_consistency_node(state: NL2SQLState) -> dict:
    """
    语义一致性校验节点
    
    参考 DataAgent 的实现流程：
    1. 获取生成的 SQL
    2. 获取用户问题和 Schema
    3. 构建校验 Prompt
    4. 调用 LLM 进行一致性校验
    5. 解析校验结果
    6. 根据结果决定下一步
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含校验结果
    """
    logger.info("Starting semantic consistency check")
    
    # ========== 流式反馈：开始语义一致性校验 ==========
    logger.info("开始语义一致性校验...")
    
    # 1. 获取生成的 SQL
    generated_sql = state.get("generated_sql", "")
    if not generated_sql or generated_sql.startswith("--"):
        logger.warning("SQL 为空或无效，跳过一致性校验")
        return {
            "semantic_consistency_output": None,
            "sql_validation": {"is_valid": False, "reason": "SQL 为空或无效"}
        }
    
    # 2. 获取用户问题和 Schema
    user_question = state.get("user_query", "")
    execution_description = state.get("execution_description", "")
    
    table_docs = state.get("table_documents", [])
    column_docs = state.get("column_documents", [])
    schema_info = _build_schema_info(table_docs, column_docs)
    
    logger.info(f"语义一致性校验输入：SQL={generated_sql[:100]}, 问题={user_question[:50]}")
    
    # 3. 构建校验 Prompt
    prompt = render_prompt(
        'semantic-consistency',
        user_question=user_question,
        generated_sql=generated_sql,
        schema_info=schema_info,
        execution_description=execution_description or user_question
    )
    
    # 4. 调用 LLM 进行一致性校验
    logger.info("使用 LLM 进行语义一致性校验...")
    
    llm_output = await call_llm(prompt, streaming=False)
    
    # 5. 解析校验结果
    consistency_output = _parse_consistency_output(llm_output)
    
    logger.info(
        "语义一致性校验完成",
        is_consistent=consistency_output.is_consistent,
        score=consistency_output.consistency_score,
        issues_count=len(consistency_output.issues)
    )
    
    # 6. 根据结果决定下一步
    if consistency_output.is_consistent:
        # ========== 流式反馈：语义一致性校验通过 ==========
        logger.info("语义一致性校验通过，SQL 与用户意图一致")
        
        return {
            "semantic_consistency_output": consistency_output.to_dict(),
            "sql_validation": {
                "is_valid": True,
                "reason": "语义一致性校验通过"
            }
        }
    else:
        # ========== 流式反馈：语义一致性校验不通过 ==========
        logger.warning(
            "语义一致性校验不通过",
            issues=consistency_output.issues,
            suggestion=consistency_output.suggestion
        )
        
        return {
            "semantic_consistency_output": consistency_output.to_dict(),
            "sql_validation": {
                "is_valid": False,
                "reason": consistency_output.suggestion,
                "issues": consistency_output.issues
            },
            "sql_regenerate_reason": f"语义不一致：{consistency_output.suggestion}"
        }


def _build_schema_info(table_docs: list, column_docs: list) -> str:
    """
    构建 Schema 信息字符串
    
    Args:
        table_docs: 表文档列表
        column_docs: 列文档列表
        
    Returns:
        str: Schema 信息字符串
    """
    lines = []
    
    for doc in table_docs:
        meta = doc.metadata if hasattr(doc, 'metadata') else doc.get('metadata', {})
        table_name = meta.get('name', 'unknown')
        description = meta.get('description', '')
        
        if description and description != table_name:
            lines.append(f"# Table: {table_name}, {description}")
        else:
            lines.append(f"# Table: {table_name}")
        
        table_columns = [
            col for col in column_docs
            if (hasattr(col, 'metadata') and col.metadata.get('name') and 
                (col.metadata.get('table_name') == table_name or 
                 (isinstance(col, dict) and col.get('table_name') == table_name)))
        ]
        
        if table_columns:
            lines.append("[")
            column_lines = []
            for col in table_columns:
                col_meta = col.metadata if hasattr(col, 'metadata') else col.get('metadata', {})
                col_name = col_meta.get('name', 'unknown')
                col_type = col_meta.get('type', '')
                col_desc = col_meta.get('description', '')
                
                col_line = f"  ({col_name}"
                if col_type:
                    col_line += f", {col_type}"
                if col_desc:
                    col_line += f", {col_desc}"
                col_line += ")"
                column_lines.append(col_line)
            
            lines.append(",\n".join(column_lines))
            lines.append("]")
        
        lines.append("")
    
    return "\n".join(lines)


def _parse_consistency_output(llm_output: str) -> ConsistencyOutput:
    """
    解析语义一致性校验输出
    
    参考 DataAgent 的 JsonParseUtil
    
    Args:
        llm_output: LLM 输出
        
    Returns:
        ConsistencyOutput: 校验结果
    """
    try:
        # 提取 JSON
        json_str = _extract_json(llm_output)
        if not json_str:
            logger.warning(f"无法从输出中提取 JSON: {llm_output[:100]}")
            return ConsistencyOutput(
                is_consistent=False,
                consistency_score=0.0,
                issues=["无法解析校验结果"],
                suggestion="请重新生成 SQL"
            )
        
        # 解析 JSON
        data = json.loads(json_str)
        
        # 转换为输出对象
        return ConsistencyOutput(
            is_consistent=data.get("is_consistent", False),
            consistency_score=float(data.get("consistency_score", 0.0)),
            issues=data.get("issues", []),
            suggestion=data.get("suggestion", "")
        )
        
    except Exception as e:
        logger.error(f"解析一致性输出失败：{str(e)}")
        return ConsistencyOutput(
            is_consistent=False,
            consistency_score=0.0,
            issues=[f"解析失败：{str(e)}"],
            suggestion="请重新生成 SQL"
        )


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
