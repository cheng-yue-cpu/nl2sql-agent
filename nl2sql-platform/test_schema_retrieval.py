"""
Schema 检索测试脚本

测试功能：
1. 添加表结构到向量库
2. 添加列信息到向量库
3. 检索相关表
4. 检索列信息
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.schema_service import get_schema_service, VectorType
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


async def test_schema_retrieval():
    """测试 Schema 检索"""
    print("\n" + "="*60)
    print("🧪 Schema 检索测试")
    print("="*60)
    
    # 获取 Schema 服务
    schema_service = get_schema_service()
    
    # 测试数据
    datasource_id = 1
    
    # 1. 添加表信息
    print("\n[1] 添加表信息到向量库")
    tables = [
        {
            "name": "users",
            "description": "用户信息表，存储用户基本信息",
            "schema": "public",
            "primary_key": ["id"],
            "foreign_key": ""
        },
        {
            "name": "orders",
            "description": "订单表，存储用户订单信息",
            "schema": "public",
            "primary_key": ["id"],
            "foreign_key": "orders.user_id=users.id"
        },
        {
            "name": "products",
            "description": "商品表，存储商品信息",
            "schema": "public",
            "primary_key": ["id"],
            "foreign_key": ""
        },
        {
            "name": "order_items",
            "description": "订单明细表，存储订单中的商品信息",
            "schema": "public",
            "primary_key": ["id"],
            "foreign_key": "order_items.order_id=orders.id,order_items.product_id=products.id"
        }
    ]
    
    for table in tables:
        doc_id = await schema_service.add_table_document(datasource_id, table)
        print(f"  ✅ 添加表：{table['name']} (doc_id: {doc_id})")
    
    # 2. 添加列信息
    print("\n[2] 添加列信息到向量库")
    columns_data = {
        "users": [
            {"name": "id", "type": "INT", "description": "用户 ID", "is_primary": True},
            {"name": "username", "type": "VARCHAR(50)", "description": "用户名"},
            {"name": "email", "type": "VARCHAR(100)", "description": "邮箱"},
            {"name": "created_at", "type": "DATETIME", "description": "创建时间"}
        ],
        "orders": [
            {"name": "id", "type": "INT", "description": "订单 ID", "is_primary": True},
            {"name": "user_id", "type": "INT", "description": "用户 ID"},
            {"name": "total_amount", "type": "DECIMAL(10,2)", "description": "订单总金额"},
            {"name": "status", "type": "VARCHAR(20)", "description": "订单状态"},
            {"name": "created_at", "type": "DATETIME", "description": "创建时间"}
        ],
        "products": [
            {"name": "id", "type": "INT", "description": "商品 ID", "is_primary": True},
            {"name": "name", "type": "VARCHAR(100)", "description": "商品名称"},
            {"name": "price", "type": "DECIMAL(10,2)", "description": "商品价格"},
            {"name": "stock", "type": "INT", "description": "库存数量"}
        ],
        "order_items": [
            {"name": "id", "type": "INT", "description": "明细 ID", "is_primary": True},
            {"name": "order_id", "type": "INT", "description": "订单 ID"},
            {"name": "product_id", "type": "INT", "description": "商品 ID"},
            {"name": "quantity", "type": "INT", "description": "购买数量"},
            {"name": "price", "type": "DECIMAL(10,2)", "description": "商品单价"}
        ]
    }
    
    for table_name, columns in columns_data.items():
        doc_ids = await schema_service.add_column_documents(datasource_id, table_name, columns)
        print(f"  ✅ 添加表 {table_name} 的 {len(columns)} 个列")
    
    # 3. 测试表检索
    print("\n[3] 测试表检索")
    test_queries = [
        "查询用户信息",
        "统计订单数量",
        "查询商品销售情况"
    ]
    
    for query in test_queries:
        print(f"\n  查询：'{query}'")
        table_docs = await schema_service.search_tables(
            datasource_id=datasource_id,
            query=query,
            top_k=3,
            threshold=0.2
        )
        
        print(f"    找到 {len(table_docs)} 个相关表:")
        for doc in table_docs:
            table_name = doc.metadata.get("name", "unknown")
            description = doc.metadata.get("description", "")
            print(f"      - {table_name}: {description}")
    
    # 4. 测试列检索
    print("\n[4] 测试列检索")
    table_names = ["users", "orders"]
    column_docs = await schema_service.search_columns(
        datasource_id=datasource_id,
        table_names=table_names
    )
    print(f"  找到 {len(column_docs)} 个列")
    
    # 5. 测试外键关系提取
    print("\n[5] 测试外键关系提取")
    relations = schema_service.extract_foreign_key_relations(table_docs)
    print(f"  提取到关联表：{relations}")
    
    print("\n" + "="*60)
    print("✅ Schema 检索测试完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_schema_retrieval())
