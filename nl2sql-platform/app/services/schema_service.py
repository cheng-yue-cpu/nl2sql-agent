"""
Schema 检索服务

参考 DataAgent 项目的 Schema 检索设计，实现：
- 表结构向量检索
- 列信息检索
- 外键关系分析
"""
from typing import List, Dict, Optional, Set
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.embeddings import Embeddings
from fastembed import TextEmbedding
from app.config import settings
import structlog
import os
import faiss

logger = structlog.get_logger()


class VectorType:
    """向量类型枚举"""
    TABLE = "table"
    COLUMN = "column"
    BUSINESS_TERM = "business_term"


class FastEmbedEmbeddings(Embeddings):
    """FastEmbed 适配器，兼容 LangChain"""
    
    def __init__(self, model_name: str = "BAAI/bge-large-zh-v1.5"):
        logger.info("Initializing Chinese TextEmbedding model...", model=model_name)
        self.embeddings_model = TextEmbedding(model_name=model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        embeddings = list(self.embeddings_model.embed(texts))
        return [emb.tolist() for emb in embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        embeddings = list(self.embeddings_model.embed([text]))
        return embeddings[0].tolist()


class SchemaService:
    """Schema 检索服务"""
    
    # FAISS 持久化目录
    PERSIST_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "faiss_index"
    )
    
    def __init__(self):
        """初始化向量库"""
        # 使用 fastembed 中文 embeddings 模型（参考 DataAgent 项目优化）
        # BAAI/bge-small-zh-v1.5 支持中文，轻量级
        self.embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
        
        # 尝试加载已持久化的 FAISS 向量库
        if os.path.exists(self.PERSIST_DIR):
            logger.info("Loading persisted FAISS index...", path=self.PERSIST_DIR)
            try:
                self.vector_store = FAISS.load_local(
                    self.PERSIST_DIR,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS index loaded successfully")
            except Exception as e:
                logger.warning("Failed to load FAISS index, creating new one", error=str(e))
                self.vector_store = FAISS.from_embeddings(
                    embedding_function=self.embeddings
                )
        else:
            # 创建新的 FAISS 向量库
            logger.info("Creating new FAISS index...")
            try:
                # 创建空的 FAISS 索引
                index = faiss.IndexFlatL2(len(self.embeddings.embed_query("test")))
                docstore = InMemoryDocstore()
                index_to_docstore_id = {}
                
                self.vector_store = FAISS(
                    embedding_function=self.embeddings,
                    index=index,
                    docstore=docstore,
                    index_to_docstore_id=index_to_docstore_id
                )
                # 保存空索引
                self._save_faiss_index()
                logger.info("New FAISS index created and saved")
            except Exception as e:
                logger.error(f"Failed to create FAISS index: {str(e)}", exc_info=True)
                raise
        
        logger.info("SchemaService initialized with FAISS", persist_dir=self.PERSIST_DIR)
    
    def _save_faiss_index(self):
        """保存 FAISS 索引到磁盘"""
        try:
            os.makedirs(self.PERSIST_DIR, exist_ok=True)
            self.vector_store.save_local(self.PERSIST_DIR)
            logger.info("FAISS index saved", path=self.PERSIST_DIR)
        except Exception as e:
            logger.error("Failed to save FAISS index", error=str(e))
    
    async def add_table_document(self, datasource_id: int, table_info: Dict) -> str:
        """
        添加表文档到向量库
        
        Args:
            datasource_id: 数据源 ID
            table_info: 表信息字典
                {
                    "name": "users",
                    "description": "用户信息表",
                    "schema": "public",
                    "primary_key": ["id"],
                    "foreign_key": "users.dept_id=departments.id"
                }
        
        Returns:
            str: 文档 ID
        """
        doc = self._convert_table_to_document(datasource_id, table_info)
        result = await self.vector_store.aadd_documents([doc])
        
        # 保存 FAISS 索引
        self._save_faiss_index()
        
        logger.info("Table document added", table_name=table_info["name"])
        return result[0]
    
    async def add_column_documents(self, datasource_id: int, table_name: str, columns: List[Dict]) -> List[str]:
        """
        添加列文档到向量库
        
        Args:
            datasource_id: 数据源 ID
            table_name: 表名
            columns: 列信息列表
                [
                    {
                        "name": "id",
                        "type": "INT",
                        "description": "用户 ID",
                        "is_primary": True,
                        "samples": ["1", "2", "3"]
                    }
                ]
        
        Returns:
            List[str]: 文档 ID 列表
        """
        docs = [
            self._convert_column_to_document(datasource_id, table_name, col)
            for col in columns
        ]
        result = await self.vector_store.aadd_documents(docs)
        
        # 保存 FAISS 索引
        self._save_faiss_index()
        
        logger.info("Column documents added", table_name=table_name, count=len(columns))
        return result
    
    def _convert_table_to_document(self, datasource_id: int, table_info: Dict) -> Document:
        """将表信息转换为 Document"""
        # 构建内容：包含表名、描述、主键、外键
        content_parts = [
            f"表名：{table_info['name']}",
        ]
        
        if table_info.get('description'):
            content_parts.append(f"描述：{table_info['description']}")
        
        if table_info.get('primary_key'):
            content_parts.append(f"主键：{', '.join(table_info['primary_key'])}")
        
        if table_info.get('foreign_key'):
            content_parts.append(f"外键：{table_info['foreign_key']}")
        
        content = "\n".join(content_parts)
        
        # 构建元数据
        metadata = {
            "vector_type": VectorType.TABLE,
            "datasource_id": str(datasource_id),
            "name": table_info["name"],
            "schema": table_info.get("schema", ""),
            "description": table_info.get("description", ""),
            "primary_key": table_info.get("primary_key", []),
            "foreign_key": table_info.get("foreign_key", "")
        }
        
        return Document(page_content=content, metadata=metadata)
    
    def _convert_column_to_document(self, datasource_id: int, table_name: str, column_info: Dict) -> Document:
        """将列信息转换为 Document"""
        # 构建内容：包含列名、类型、描述、示例
        content_parts = [
            f"列名：{column_info['name']}",
            f"表名：{table_name}",
        ]
        
        if column_info.get('type'):
            content_parts.append(f"类型：{column_info['type']}")
        
        if column_info.get('description'):
            content_parts.append(f"描述：{column_info['description']}")
        
        if column_info.get('samples'):
            content_parts.append(f"示例值：{', '.join(column_info['samples'])}")
        
        content = "\n".join(content_parts)
        
        # 构建元数据
        metadata = {
            "vector_type": VectorType.COLUMN,
            "datasource_id": str(datasource_id),
            "table_name": table_name,
            "name": column_info["name"],
            "type": column_info.get("type", ""),
            "description": column_info.get("description", ""),
            "primary": column_info.get("is_primary", False),
            "samples": column_info.get("samples", [])
        }
        
        return Document(page_content=content, metadata=metadata)
    
    async def search_tables(
        self,
        datasource_id: int,
        query: str,
        top_k: int = 10,
        threshold: float = 0.2
    ) -> List[Document]:
        """
        检索相关表
        
        Args:
            datasource_id: 数据源 ID
            query: 查询文本
            top_k: 返回数量（低阈值，尽可能不遗漏）
            threshold: 相似度阈值
        
        Returns:
            List[Document]: 表文档列表
        """
        logger.info("Searching tables", datasource_id=datasource_id, query=query, top_k=top_k)
        
        try:
            # InMemoryVectorStore 不支持 filter，使用简单搜索
            results = await self.vector_store.asimilarity_search(
                query=query,
                k=top_k
            )
            
            # 手动过滤
            filtered_results = [
                doc for doc in results
                if doc.metadata.get("datasource_id") == str(datasource_id)
                and doc.metadata.get("vector_type") == VectorType.TABLE
            ]
            
            logger.info("Table search completed", found=len(filtered_results))
            return filtered_results
            
        except Exception as e:
            logger.error("Table search failed", error=str(e))
            return []
    
    async def search_columns(
        self,
        datasource_id: int,
        table_names: List[str],
        query: Optional[str] = None
    ) -> List[Document]:
        """
        检索列文档
        
        Args:
            datasource_id: 数据源 ID
            table_names: 表名列表
            query: 查询文本（可选，为空则返回所有列）
        
        Returns:
            List[Document]: 列文档列表
        """
        if not table_names:
            return []
        
        logger.info("Searching columns", datasource_id=datasource_id, tables=table_names)
        
        try:
            # 计算需要获取的列数量
            top_k = len(table_names) * 50  # 每表最多 50 列
            
            # InMemoryVectorStore 不支持 filter，获取所有后手动过滤
            results = await self.vector_store.asimilarity_search(
                query=query or " ",
                k=top_k
            )
            
            # 手动过滤
            filtered_results = [
                doc for doc in results
                if doc.metadata.get("datasource_id") == str(datasource_id)
                and doc.metadata.get("vector_type") == VectorType.COLUMN
                and doc.metadata.get("table_name") in table_names
            ]
            
            logger.info("Column search completed", found=len(filtered_results))
            return filtered_results
            
        except Exception as e:
            logger.error("Column search failed", error=str(e))
            return []
    
    def extract_foreign_key_relations(self, table_docs: List[Document]) -> Set[str]:
        """
        从外键中提取关联表名
        
        Args:
            table_docs: 表文档列表
        
        Returns:
            Set[str]: 关联表名集合
        """
        relations = set()
        
        for doc in table_docs:
            foreign_key_str = doc.metadata.get("foreign_key", "")
            if foreign_key_str:
                # 示例："orders.user_id=users.id"
                for pair in foreign_key_str.split(","):
                    parts = pair.split("=")
                    if len(parts) == 2:
                        # 提取表名
                        left_table = parts[0].strip().split(".")[0]
                        right_table = parts[1].strip().split(".")[0]
                        relations.add(left_table)
                        relations.add(right_table)
        
        logger.info("Extracted foreign key relations", relations=relations)
        return relations
    
    async def load_missing_tables(
        self,
        datasource_id: int,
        existing_tables: List[Document],
        missing_table_names: List[str]
    ) -> List[Document]:
        """
        加载缺失的表（外键关联）
        
        Args:
            datasource_id: 数据源 ID
            existing_tables: 已有的表文档
            missing_table_names: 缺失的表名列表
        
        Returns:
            List[Document]: 完整的表文档列表
        """
        if not missing_table_names:
            return existing_tables
        
        logger.info("Loading missing tables", missing=missing_table_names)
        
        filter_expr = {
            "datasource_id": str(datasource_id),
            "vector_type": VectorType.TABLE,
            "name": {"$in": missing_table_names}
        }
        
        try:
            found_docs = await self.vector_store.asimilarity_search(
                query=" ",
                k=len(missing_table_names) + 5,
                filter=filter_expr
            )
            
            # 去重
            existing_ids = {doc.metadata.get("name") for doc in existing_tables}
            unique_docs = [
                doc for doc in found_docs 
                if doc.metadata.get("name") not in existing_ids
            ]
            
            logger.info("Missing tables loaded", loaded=len(unique_docs))
            return existing_tables + unique_docs
            
        except Exception as e:
            logger.error("Load missing tables failed", error=str(e))
            return existing_tables
    
    async def build_schema_dto(
        self,
        table_docs: List[Document],
        column_docs: List[Document]
    ) -> Dict:
        """
        从 Document 构建 Schema DTO
        
        Args:
            table_docs: 表文档列表
            column_docs: 列文档列表
        
        Returns:
            Dict: Schema 字典
        """
        tables = []
        
        # 构建表信息
        for table_doc in table_docs:
            meta = table_doc.metadata
            table = {
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
                "primary_keys": meta.get("primary_key", []),
                "columns": []
            }
            tables.append(table)
        
        # 为表附加列
        for col_doc in column_docs:
            meta = col_doc.metadata
            table_name = meta.get("table_name")
            
            column = {
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
                "type": meta.get("type", ""),
                "is_primary": meta.get("primary", False)
            }
            
            for table in tables:
                if table["name"] == table_name:
                    table["columns"].append(column)
                    break
        
        # 提取外键
        foreign_keys = []
        for table_doc in table_docs:
            fk = table_doc.metadata.get("foreign_key", "")
            if fk:
                foreign_keys.extend(fk.split(","))
        
        schema = {
            "tables": tables,
            "foreign_keys": foreign_keys
        }
        
        logger.info("Schema DTO built", tables=len(tables), columns=len(column_docs))
        return schema


# 全局 Schema 服务实例
_schema_service: Optional[SchemaService] = None


def get_schema_service() -> SchemaService:
    """获取 Schema 服务实例"""
    global _schema_service
    if _schema_service is None:
        _schema_service = SchemaService()
    return _schema_service
