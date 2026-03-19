"""
MySQL Schema 导入工具

从 MySQL 数据库读取表结构信息并导入到向量库
"""
import asyncio
import sys
import os
import pymysql

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from app.services.schema_service import get_schema_service
from app.config.mysql import MySQLConfig
import structlog

logger = structlog.get_logger()


class MySQLSchemaImporter:
    """MySQL Schema 导入器"""
    
    def __init__(self, datasource_id: int = 1):
        """
        初始化导入器
        
        Args:
            datasource_id: 数据源 ID
        """
        self.datasource_id = datasource_id
        self.schema_service = get_schema_service()
        self.connection = None
    
    def connect(self):
        """连接到 MySQL 数据库"""
        logger.info("Connecting to MySQL", 
                   host=MySQLConfig.HOST, 
                   database=MySQLConfig.DATABASE)
        
        try:
            self.connection = pymysql.connect(
                **MySQLConfig.get_connection_params()
            )
            logger.info("MySQL connected successfully")
            return True
        except Exception as e:
            logger.error("MySQL connection failed", error=str(e))
            return False
    
    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            logger.info("MySQL connection closed")
    
    async def _clear_existing_index(self):
        """
        清除已存在的 FAISS 索引
        
        避免多次初始化导致重复文档
        """
        try:
            # 重新创建空的 FAISS 索引
            import faiss
            from langchain_community.vectorstores import FAISS
            from langchain_community.docstore.in_memory import InMemoryDocstore
            
            index = faiss.IndexFlatL2(len(self.schema_service.embeddings.embed_query("test")))
            docstore = InMemoryDocstore()
            index_to_docstore_id = {}
            
            self.schema_service.vector_store = FAISS(
                embedding_function=self.schema_service.embeddings,
                index=index,
                docstore=docstore,
                index_to_docstore_id=index_to_docstore_id
            )
            
            # 保存空索引
            self.schema_service._save_faiss_index()
            
            logger.info("Existing FAISS index cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear existing index: {str(e)}", exc_info=True)
            raise
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                logger.info("Found tables", count=len(tables), tables=tables)
                return tables
        except Exception as e:
            logger.error("Failed to get tables", error=str(e))
            return []
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        获取表详细信息
        
        Args:
            table_name: 表名
            
        Returns:
            Dict: 表信息
        """
        if not self.connection:
            return None
        
        try:
            with self.connection.cursor() as cursor:
                # 获取表注释
                cursor.execute("""
                    SELECT TABLE_COMMENT 
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """, (MySQLConfig.DATABASE, table_name))
                
                result = cursor.fetchone()
                description = result[0] if result and result[0] else ""
                
                # 获取主键
                cursor.execute("""
                    SELECT COLUMN_NAME 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
                """, (MySQLConfig.DATABASE, table_name))
                
                primary_keys = [row[0] for row in cursor.fetchall()]
                
                # 获取外键
                cursor.execute("""
                    SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (MySQLConfig.DATABASE, table_name))
                
                foreign_keys = []
                for row in cursor.fetchall():
                    fk = f"{table_name}.{row[0]}={row[1]}.{row[2]}"
                    foreign_keys.append(fk)
                
                foreign_key_str = ",".join(foreign_keys) if foreign_keys else ""
                
                return {
                    "name": table_name,
                    "description": description,
                    "schema": MySQLConfig.DATABASE,
                    "primary_key": primary_keys,
                    "foreign_key": foreign_key_str
                }
                
        except Exception as e:
            logger.error("Failed to get table info", table=table_name, error=str(e))
            return None
    
    def get_columns(self, table_name: str) -> List[Dict]:
        """
        获取列信息
        
        Args:
            table_name: 表名
            
        Returns:
            List[Dict]: 列信息列表
        """
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        COLUMN_TYPE,
                        COLUMN_COMMENT,
                        COLUMN_KEY
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (MySQLConfig.DATABASE, table_name))
                
                columns = []
                for row in cursor.fetchall():
                    column = {
                        "name": row[0],
                        "type": row[1],
                        "description": row[2] if row[2] else "",
                        "is_primary": row[3] == "PRI"
                    }
                    columns.append(column)
                
                logger.info("Got columns", table=table_name, count=len(columns))
                return columns
                
        except Exception as e:
            logger.error("Failed to get columns", table=table_name, error=str(e))
            return []
    
    async def import_schema(self, clear_existing: bool = True) -> Dict:
        """
        导入完整 Schema
        
        Args:
            clear_existing: 是否先清除已存在的索引
            
        Returns:
            Dict: 导入统计信息
        """
        logger.info("Starting schema import", 
                    datasource_id=self.datasource_id,
                    clear_existing=clear_existing)
        
        # 清除已存在的索引（避免重复）
        if clear_existing:
            logger.info("Clearing existing FAISS index...")
            await self._clear_existing_index()
        
        stats = {
            "tables": 0,
            "columns": 0,
            "errors": []
        }
        
        # 获取所有表
        tables = self.get_tables()
        if not tables:
            logger.warning("No tables found")
            return stats
        
        # 导入每个表
        for table_name in tables:
            try:
                logger.info("Importing table", table=table_name)
                
                # 获取表信息
                table_info = self.get_table_info(table_name)
                if not table_info:
                    stats["errors"].append(f"Failed to get info for table: {table_name}")
                    continue
                
                # 添加表文档
                await self.schema_service.add_table_document(
                    self.datasource_id, 
                    table_info
                )
                stats["tables"] += 1
                
                # 获取并添加列信息
                columns = self.get_columns(table_name)
                if columns:
                    await self.schema_service.add_column_documents(
                        self.datasource_id,
                        table_name,
                        columns
                    )
                    stats["columns"] += len(columns)
                
                logger.info("Table imported", 
                           table=table_name, 
                           columns=len(columns))
                
            except Exception as e:
                error_msg = f"Error importing table {table_name}: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        logger.info("Schema import completed", 
                   tables=stats["tables"], 
                   columns=stats["columns"],
                   errors=len(stats["errors"]))
        
        return stats


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("🗄️ MySQL Schema 导入工具")
    print("="*60)
    
    # 创建导入器
    importer = MySQLSchemaImporter(datasource_id=1)
    
    # 连接数据库
    if not importer.connect():
        print("\n❌ 数据库连接失败！")
        print(f"请检查 MySQL 服务是否运行，以及连接信息是否正确：")
        print(f"  Host: {MySQLConfig.HOST}")
        print(f"  Port: {MySQLConfig.PORT}")
        print(f"  Database: {MySQLConfig.DATABASE}")
        print(f"  Username: {MySQLConfig.USERNAME}")
        return
    
    try:
        # 导入 Schema（自动清除旧索引）
        print("\n📥 开始导入 Schema...")
        print("⚠️  将清除旧的索引数据，避免重复...")
        stats = await importer.import_schema(clear_existing=True)
        
        # 打印统计信息
        print("\n" + "="*60)
        print("✅ Schema 导入完成！")
        print("="*60)
        print(f"  表数量：{stats['tables']}")
        print(f"  列数量：{stats['columns']}")
        
        if stats["errors"]:
            print(f"\n⚠️ 错误：{len(stats['errors'])}")
            for error in stats["errors"]:
                print(f"  - {error}")
        
        print("\n" + "="*60)
        
    finally:
        importer.close()


if __name__ == "__main__":
    asyncio.run(main())
