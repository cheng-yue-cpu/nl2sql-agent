"""
10. SQLGenerateNode - SQL 生成节点

完全参考 DataAgent 项目的 SqlGenerateNode 实现：
- 根据用户问题、表结构、业务知识生成 SQL
- 支持重试机制（最多 10 次）
- 使用独立 Prompt 文件 (new-sql-generate.txt, sql-error-fixer.txt)

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：SqlGenerateNode.java
"""
from app.workflows.state import NL2SQLState
from app.services.llm_service import call_llm
from app.services.prompt_loader import render_prompt
from app.services.sql_error_classifier import classify_sql_error, SqlErrorType
from app.config import settings
import structlog
import re

logger = structlog.get_logger()


# 最大重试次数（参考 DataAgent 的 maxSqlRetryCount）
MAX_SQL_RETRY_COUNT = 10


async def sql_generate_node(state: NL2SQLState) -> dict:
    """
    SQL 生成节点
    
    参考 DataAgent 的实现流程：
    1. 检查是否达到最大重试次数
    2. 获取当前执行步骤的 SQL 任务要求
    3. 判断是首次生成还是重试生成
    4. 构建 SQL 生成 Prompt
    5. 调用 LLM 生成 SQL
    6. 清理和验证 SQL
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含生成的 SQL
    """
    sql_generate_count = state.get("sql_generate_count", 0)
    
    # 检查是否达到最大重试次数
    if sql_generate_count >= MAX_SQL_RETRY_COUNT:
        logger.error(f"SQL 生成次数超限，最大尝试次数：{MAX_SQL_RETRY_COUNT}，已尝试次数：{sql_generate_count}")
        return {
            "generated_sql": "-- SQL 生成次数超限，请尝试重新描述问题",
            "sql_generate_count": sql_generate_count + 1,
            "error": f"已达到最大重试次数 ({MAX_SQL_RETRY_COUNT})，请检查问题描述或 Schema 配置"
        }
    
    # 获取用户查询（优先使用 canonical_query）
    user_query = state.get("canonical_query") or state["user_query"]
    
    # 获取表结构信息
    table_docs = state.get("table_documents", [])
    column_docs = state.get("column_documents", [])
    evidence = state.get("evidence", "")
    
    # 构建 Schema 信息
    schema_info = _build_schema_info(table_docs, column_docs)
    
    # 判断是重试还是首次生成
    sql_regenerate_reason = state.get("sql_regenerate_reason", "")
    original_sql = state.get("generated_sql", "")
    
    # ========== 流式反馈：判断是否重试 ==========
    if sql_regenerate_reason:
        # ========== 流式反馈：SQL 重试 ==========
        logger.info(f"检测到 SQL 生成失败，开始重新生成 SQL... (第 {sql_generate_count + 1} 次尝试)")
        logger.info(f"失败原因：{sql_regenerate_reason}")
        
        # 分类错误类型（参考 DataAgent 的错误分类）
        error_type = classify_sql_error(sql_regenerate_reason)
        
        if error_type == SqlErrorType.SEMANTIC_ERROR:
            # 语义错误：使用语义修复 Prompt
            logger.info(f"错误类型：语义错误，使用语义修复 Prompt")
            prompt = render_prompt(
                'sql-semantic-fixer',
                dialect="mysql",
                error_message=sql_regenerate_reason,
                schema_info=schema_info,
                execution_description=user_query,
                error_sql=original_sql,
                question=user_query,
                evidence=evidence or ""
            )
        else:
            # 执行错误：使用执行修复 Prompt
            logger.info(f"错误类型：执行错误，使用执行修复 Prompt")
            prompt = render_prompt(
                'sql-error-fixer',
                dialect="mysql",
                error_message=sql_regenerate_reason,
                schema_info=schema_info,
                execution_description=user_query,
                error_sql=original_sql,
                question=user_query,
                evidence=evidence or ""
            )
    else:
        # ========== 流式反馈：开始 SQL 生成 ==========
        logger.info(f"开始生成 SQL... (第 {sql_generate_count + 1} 次尝试)")
        logger.info(f"用户查询：{user_query[:100]}")
        
        # 从文件加载 SQL 生成 Prompt
        prompt = render_prompt(
            'new-sql-generate',
            dialect="mysql",
            schema_info=schema_info,
            evidence=evidence or "",
            question=user_query,
            execution_description=user_query
        )
    
    # ========== 流式反馈：调用 LLM ==========
    logger.info(f"使用智谱 AI GLM 模型：{settings.zhipuai_model} (流式输出)")
    
    # 调用 LLM 生成 SQL（启用流式）
    try:
        sql = await call_llm(prompt, streaming=True)
        
        # ========== 流式反馈：清理 SQL ==========
        logger.info("正在清理和验证 SQL...")
        
        # 清理 SQL
        sql = _clean_sql(sql)
        
        # ========== 流式反馈：SQL 生成完成 ==========
        logger.info(f"SQL 生成完成。SQL: {sql[:200]}")
        
        return {
            "generated_sql": sql,
            "sql_generate_count": sql_generate_count + 1,
            "sql_regenerate_reason": ""  # 清除重试原因
        }
        
    except Exception as e:
        logger.error(f"SQL 生成失败：{str(e)}")
        return {
            "generated_sql": "",
            "sql_generate_count": sql_generate_count + 1,
            "sql_regenerate_reason": f"LLM 调用失败：{str(e)}"
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


def _clean_sql(sql: str) -> str:
    """
    清理 SQL
    
    Args:
        sql: 原始 SQL
        
    Returns:
        str: 清理后的 SQL
    """
    sql = sql.strip()
    
    # 移除 markdown 标记
    sql = re.sub(r'^```sql\s*', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'^```\s*', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'```$', '', sql)
    
    # 移除转义的反引号 (\\` → `)
    sql = sql.replace('\\\\`', '`')
    sql = sql.replace('\\`', '`')
    
    # 移除前后空白
    sql = sql.strip()
    
    return sql
