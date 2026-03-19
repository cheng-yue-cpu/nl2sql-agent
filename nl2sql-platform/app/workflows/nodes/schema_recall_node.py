"""
4. SchemaRecallNode - 表结构检索节点

完全参考 DataAgent 项目的 SchemaRecallNode 实现：
- 根据用户问题向量检索相关表结构
- 加载关联列信息
- 通过外键补全缺失的表
- 支持流式反馈

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：SchemaRecallNode.java
"""
from typing import List, Dict
from app.workflows.state import NL2SQLState
from app.services.schema_service import get_schema_service, VectorType
from langchain_core.messages import AIMessage
import structlog

logger = structlog.get_logger()


async def schema_recall_node(state: NL2SQLState) -> dict:
    """
    Schema 检索节点
    
    完全参考 DataAgent 的 SchemaRecallNode 实现：
    1. 检索相关表（低阈值，尽可能不遗漏）
    2. 提取表名
    3. 检索列信息
    4. 从外键提取关联表
    5. 计算缺失的表（外键关联但未被检索到的表）
    6. 加载缺失的表
    7. 构建表关系信息
    
    优化点：
    - 使用 canonical_query + user_query 组合检索，提高召回率
    - 降低阈值到 0.05，确保不遗漏相关表
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含检索到的表结构和列信息
    """
    # 优先使用重写后的查询，同时保留原始查询用于扩展检索
    canonical_query = state.get("canonical_query")
    user_query = state.get("user_query")
    agent_id = state["agent_id"]
    
    # 组合查询用于检索（提高召回率）
    query_for_search = canonical_query or user_query
    if canonical_query and user_query and canonical_query != user_query:
        # 组合两个查询，增加语义覆盖
        query_for_search = f"{canonical_query} {user_query}"
    
    logger.info(f"Starting schema recall", query=query_for_search, canonical=canonical_query, original=user_query)
    
    # 获取 Schema 服务
    schema_service = get_schema_service()
    
    # TODO: 从数据源配置获取 datasource_id
    # 当前使用 agent_id 作为 datasource_id
    datasource_id = int(agent_id) if agent_id.isdigit() else 1
    
    try:
        # ========== 流式反馈：开始检索 ==========
        # 参考 DataAgent: emitter.next(ChatResponseUtil.createResponse("开始初步召回 Schema 信息..."))
        logger.info("开始初步召回 Schema 信息...")
        
        # 1. 检索相关表（低阈值，尽可能不遗漏）
        # 参考 DataAgent 实现，使用极低阈值确保召回率
        table_docs = await schema_service.search_tables(
            datasource_id=datasource_id,
            query=query_for_search,
            top_k=20,  # 增加召回数量
            threshold=0.05  # 极低阈值，确保召回
        )
        
        # 2. 提取表名
        table_names = [
            doc.metadata.get("name") 
            for doc in table_docs 
            if doc.metadata.get("name")
        ]
        
        # ========== 流式反馈：表召回完成 ==========
        # 参考 DataAgent: emitter.next(ChatResponseUtil.createResponse("初步表信息召回完成，数量：X，表名：..."))
        logger.info(
            f"初步表信息召回完成，数量：{len(table_docs)}，表名：{', '.join(table_names) if table_names else '无'}"
        )
        
        if not table_docs:
            # 没有找到相关表
            logger.warning("未检索到相关数据表", query=query_for_search)
            # ========== 流式反馈：失败提示 ==========
            return {
                "table_documents": [],
                "column_documents": [],
                "schema_relations": None,
                "messages": [AIMessage(
                    content=f"""未检索到相关数据表

这可能是因为：
1. 数据源尚未初始化。
2. 您的提问与当前数据库中的表结构无关。
3. 请尝试点击"初始化数据源"或换一个与业务相关的问题。
4. 如果你用 A 嵌入模型初始化数据源，却更换为 B 嵌入模型，请重新初始化数据源

流程已终止。"""
                )]
            }
        
        # ========== 流式反馈：开始检索列信息 ==========
        logger.info("开始检索列信息...")
        
        # 3. 检索列信息
        column_docs = await schema_service.search_columns(
            datasource_id=datasource_id,
            table_names=table_names,
            query=None  # 获取所有列
        )
        
        # ========== 流式反馈：列检索完成 ==========
        logger.info(f"列信息检索完成，数量：{len(column_docs)}")
        
        # 4. 从外键提取关联表
        # ========== 流式反馈：开始提取外键 ==========
        logger.info("开始分析表关联关系...")
        
        fk_relations = schema_service.extract_foreign_key_relations(table_docs)
        
        # ========== 流式反馈：外键提取完成 ==========
        logger.info(f"外键关联提取完成，关联表数量：{len(fk_relations)}")
        
        # 5. 计算缺失的表（外键关联但未被检索到的表）
        existing_table_names = set(table_names)
        missing_table_names = list(fk_relations - existing_table_names)
        
        if missing_table_names:
            # ========== 流式反馈：加载缺失表 ==========
            logger.info(f"检测到缺失的关联表：{missing_table_names}，开始加载...")
            
            table_docs = await schema_service.load_missing_tables(
                datasource_id=datasource_id,
                existing_tables=table_docs,
                missing_table_names=missing_table_names
            )
            
            # 重新加载列
            all_table_names = [
                doc.metadata.get("name") 
                for doc in table_docs 
                if doc.metadata.get("name")
            ]
            column_docs = await schema_service.search_columns(
                datasource_id=datasource_id,
                table_names=all_table_names,
                query=None
            )
            
            # ========== 流式反馈：缺失表加载完成 ==========
            logger.info(f"缺失表加载完成，总表数：{len(table_docs)}，总列数：{len(column_docs)}")
        
        # 6. 构建表关系信息
        schema_relations = _build_schema_relations(table_docs)
        
        # ========== 流式反馈：Schema 召回完成 ==========
        # 参考 DataAgent: emitter.next(ChatResponseUtil.createResponse("初步 Schema 信息召回完成."))
        logger.info(f"Schema 召回完成。表：{len(table_docs)}, 列：{len(column_docs)}, 关系：{len(schema_relations.get('foreign_keys', []))}")
        logger.info("初步 Schema 信息召回完成.")
        
        return {
            "table_documents": table_docs,
            "column_documents": column_docs,
            "schema_relations": schema_relations
        }
        
    except Exception as e:
        logger.error(f"Schema 检索失败：{str(e)}", exc_info=True)
        return {
            "table_documents": [],
            "column_documents": [],
            "schema_relations": None,
            "error": f"Schema 检索失败：{str(e)}"
        }


def _build_schema_relations(table_docs: List) -> Dict:
    """
    构建表关系信息
    
    参考 DataAgent 的 SchemaDTO 设计
    
    Args:
        table_docs: 表文档列表
        
    Returns:
        Dict: 表关系字典
    """
    relations = {
        "tables": [],
        "foreign_keys": [],
        "join_paths": []
    }
    
    for doc in table_docs:
        meta = doc.metadata
        table_name = meta.get("name", "")
        
        if table_name:
            relations["tables"].append(table_name)
        
        # 提取外键
        foreign_key_str = meta.get("foreign_key", "")
        if foreign_key_str:
            relations["foreign_keys"].append(foreign_key_str)
            
            # 解析 JOIN 路径
            for pair in foreign_key_str.split(","):
                parts = pair.split("=")
                if len(parts) == 2:
                    relations["join_paths"].append({
                        "left": parts[0].strip(),
                        "right": parts[1].strip()
                    })
    
    logger.info(f"表关系构建完成。表：{len(relations['tables'])}, 外键：{len(relations['foreign_keys'])}, JOIN 路径：{len(relations['join_paths'])}")
    
    return relations
