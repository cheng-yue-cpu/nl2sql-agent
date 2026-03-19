"""
5. TableRelationNode - 表关系分析节点

参考 DataAgent 的 TableRelationNode 实现：
- 分析表 JOIN 关系
- 提取外键路径
- 支持重试 (最多 3 次)
- 加载缺失的关联表
"""
from typing import List, Dict, Set
from app.workflows.state import NL2SQLState
from app.services.schema_service import get_schema_service
from langchain_core.messages import AIMessage
import structlog

logger = structlog.get_logger()


async def table_relation_node(state: NL2SQLState) -> dict:
    """
    表关系分析节点
    
    功能：
    1. 从外键提取表关联
    2. 构建 JOIN 路径
    3. 加载缺失的关联表
    4. 支持重试 (max_retry=3)
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含表关系信息
    """
    table_documents = state.get("table_documents", [])
    column_documents = state.get("column_documents", [])
    agent_id = state.get("agent_id", "1")
    
    logger.info("Starting table relation analysis", 
                tables=len(table_documents), 
                columns=len(column_documents))
    
    # ========== 流式反馈：开始分析表关联关系 ==========
    logger.info("开始分析表关联关系...")
    
    schema_service = get_schema_service()
    
    # 获取 datasource_id
    datasource_id = int(agent_id) if agent_id.isdigit() else 1
    
    max_retry = 3
    retry_count = 0
    
    try:
        # 1. 提取外键关联
        fk_relations = schema_service.extract_foreign_key_relations(table_documents)
        
        # ========== 流式反馈：外键关联提取完成 ==========
        logger.info(f"外键关联提取完成，关联表数量：{len(fk_relations)}")
        
        # 2. 计算缺失的表（外键关联但未被检索到的表）
        existing_table_names = {
            doc.metadata.get("name") 
            for doc in table_documents 
            if doc.metadata.get("name")
        }
        
        missing_table_names = list(fk_relations - existing_table_names)
        
        # ========== 流式反馈：检查缺失表 ==========
        if missing_table_names:
            logger.info(f"检测到缺失的关联表：{missing_table_names}")
        else:
            logger.info("未检测到缺失的关联表")
        
        # 3. 加载缺失的表 (重试机制)
        while missing_table_names and retry_count < max_retry:
            logger.info(f"加载缺失表 (尝试 {retry_count + 1}/{max_retry})", 
                       missing=missing_table_names)
            
            # ========== 流式反馈：正在加载缺失表 ==========
            logger.info(f"正在加载缺失表：{', '.join(missing_table_names)}...")
            
            table_documents = await schema_service.load_missing_tables(
                datasource_id=datasource_id,
                existing_tables=table_documents,
                missing_table_names=missing_table_names
            )
            
            # 重新加载列信息
            all_table_names = [
                doc.metadata.get("name") 
                for doc in table_documents 
                if doc.metadata.get("name")
            ]
            
            column_documents = await schema_service.search_columns(
                datasource_id=datasource_id,
                table_names=all_table_names,
                query=None  # 获取所有列
            )
            
            # 重新提取外键
            fk_relations = schema_service.extract_foreign_key_relations(table_documents)
            
            # 重新计算缺失表
            existing_table_names = {
                doc.metadata.get("name") 
                for doc in table_documents 
                if doc.metadata.get("name")
            }
            missing_table_names = list(fk_relations - existing_table_names)
            
            retry_count += 1
            
            if missing_table_names:
                logger.warning(f"仍有缺失表，继续重试 (剩余 {max_retry - retry_count} 次)", 
                              missing=missing_table_names)
        
        if missing_table_names:
            logger.error(f"缺失表加载失败，已达最大重试次数", 
                        missing=missing_table_names)
        else:
            logger.info("所有关联表已加载完成")
        
        # 4. 构建 JOIN 路径
        join_paths = _build_join_paths(table_documents)
        
        # 5. 构建表关系信息
        schema_relations = {
            "tables": list(existing_table_names),
            "foreign_keys": list(fk_relations),
            "join_paths": join_paths
        }
        
        # ========== 流式反馈：表关系分析完成 ==========
        logger.info(f"表关系分析完成。表：{len(table_documents)}, 列：{len(column_documents)}, JOIN 路径：{len(join_paths)}")
        
        return {
            "table_documents": table_documents,
            "column_documents": column_documents,
            "schema_relations": schema_relations
        }
        
    except Exception as e:
        logger.error(f"表关系分析失败：{str(e)}", exc_info=True)
        return {
            "table_documents": table_documents,
            "column_documents": column_documents,
            "schema_relations": None,
            "error": f"表关系分析失败：{str(e)}"
        }


def _build_join_paths(table_documents: List) -> List[Dict]:
    """
    构建 JOIN 路径
    
    Args:
        table_documents: 表文档列表
        
    Returns:
        List[Dict]: JOIN 路径列表
    """
    join_paths = []
    
    for doc in table_documents:
        foreign_key_str = doc.metadata.get("foreign_key", "")
        if foreign_key_str:
            for pair in foreign_key_str.split(","):
                parts = pair.split("=")
                if len(parts) == 2:
                    left_parts = parts[0].strip().split(".")
                    right_parts = parts[1].strip().split(".")
                    
                    if len(left_parts) == 2 and len(right_parts) == 2:
                        join_paths.append({
                            "left_table": left_parts[0],
                            "left_column": left_parts[1],
                            "right_table": right_parts[0],
                            "right_column": right_parts[1],
                            "type": "INNER JOIN",
                            "condition": f"{parts[0].strip()} = {parts[1].strip()}"
                        })
    
    logger.info(f"Built {len(join_paths)} join paths", join_paths=join_paths)
    
    return join_paths
