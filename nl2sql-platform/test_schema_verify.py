"""
Schema 导入后验证测试

直接测试 Schema 服务，验证数据已导入
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.schema_service import get_schema_service
import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


async def test_schema_service():
    """测试 Schema 服务"""
    print("\n" + "="*60)
    print("📊 Schema 服务验证测试")
    print("="*60)
    
    # 获取 Schema 服务（会重新初始化向量库）
    print("\n初始化 Schema 服务...")
    schema_service = get_schema_service()
    
    # 重新导入 Schema
    print("\n重新导入 Schema 到内存向量库...")
    
    from app.config.mysql import MySQLConfig
    import pymysql
    
    # 连接 MySQL
    connection = pymysql.connect(
        **MySQLConfig.get_connection_params()
    )
    
    try:
        with connection.cursor() as cursor:
            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"找到 {len(tables)} 个表")
            
            # 导入前 5 个表作为测试
            for table_name in tables[:5]:
                print(f"\n导入表：{table_name}")
                
                # 获取表信息
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
                
                # 添加表文档
                await schema_service.add_table_document(1, {
                    "name": table_name,
                    "description": description,
                    "schema": MySQLConfig.DATABASE,
                    "primary_key": primary_keys,
                    "foreign_key": ""
                })
                
                # 获取列信息
                cursor.execute("""
                    SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (MySQLConfig.DATABASE, table_name))
                
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "description": row[2] if row[2] else "",
                        "is_primary": row[3] == "PRI"
                    })
                
                # 添加列文档
                await schema_service.add_column_documents(1, table_name, columns)
                print(f"  ✅ 导入 {len(columns)} 个列")
        
        # 测试检索
        print("\n" + "="*60)
        print("测试向量检索")
        print("="*60)
        
        test_queries = [
            "用户",
            "订单",
            "商品"
        ]
        
        for query in test_queries:
            print(f"\n查询：'{query}'")
            table_docs = await schema_service.search_tables(
                datasource_id=1,
                query=query,
                top_k=3,
                threshold=0.2
            )
            
            if table_docs:
                print(f"  找到 {len(table_docs)} 个相关表:")
                for doc in table_docs:
                    table_name = doc.metadata.get("name", "unknown")
                    description = doc.metadata.get("description", "")
                    print(f"    - {table_name}: {description}")
            else:
                print(f"  未找到相关表")
        
    finally:
        connection.close()
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)


async def main():
    """主测试函数"""
    try:
        await test_schema_service()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
