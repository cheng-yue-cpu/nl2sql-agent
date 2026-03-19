"""
真实数据库 SQL 执行测试

测试功能：
1. 连接 MySQL 数据库
2. 执行真实的 SQL 查询
3. 验证返回结果
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflows.nodes.sql_execute_node import _execute_sql
from app.config.mysql import MySQLConfig
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


async def test_mysql_connection():
    """测试 MySQL 连接和 SQL 执行"""
    print("\n" + "="*60)
    print("🔌 真实 MySQL 数据库连接测试")
    print("="*60)
    
    print(f"\n数据库信息:")
    print(f"  Host: {MySQLConfig.HOST}:{MySQLConfig.PORT}")
    print(f"  Database: {MySQLConfig.DATABASE}")
    print(f"  Username: {MySQLConfig.USERNAME}")
    
    # 测试 1: 简单查询
    print("\n" + "-"*60)
    print("[测试 1] 简单查询：SELECT 1")
    print("-"*60)
    
    result = await _execute_sql("SELECT 1 as test")
    
    if result["success"]:
        print(f"✅ 执行成功")
        print(f"  列：{result['columns']}")
        print(f"  数据：{result['data']}")
        print(f"  行数：{result['row_count']}")
    else:
        print(f"❌ 执行失败：{result['error']}")
        return False
    
    # 测试 2: 查询表结构
    print("\n" + "-"*60)
    print("[测试 2] 查询数据库表：SELECT table_name FROM information_schema.tables")
    print("-"*60)
    
    result = await _execute_sql(f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{MySQLConfig.DATABASE}'
        LIMIT 10
    """)
    
    if result["success"]:
        print(f"✅ 执行成功")
        print(f"  找到 {result['row_count']} 个表:")
        for row in result['data'][:10]:  # 只显示前 10 个
            table_name = list(row.values())[0]
            print(f"    - {table_name}")
        if result['row_count'] > 10:
            print(f"    ... 还有 {result['row_count'] - 10} 个表")
    else:
        print(f"❌ 执行失败：{result['error']}")
        return False
    
    # 测试 3: 查询具体表数据
    print("\n" + "-"*60)
    print("[测试 3] 查询用户表：SELECT * FROM users LIMIT 5")
    print("-"*60)
    
    result = await _execute_sql("SELECT * FROM users LIMIT 5")
    
    if result["success"]:
        print(f"✅ 执行成功")
        print(f"  列：{result['columns']}")
        print(f"  行数：{result['row_count']}")
        if result['data']:
            print(f"  前 3 行数据:")
            for i, row in enumerate(result['data'][:3], 1):
                print(f"    {i}. {row}")
    else:
        print(f"❌ 执行失败：{result['error']}")
        print(f"  可能 users 表不存在，这是正常的")
    
    # 测试 4: 安全测试 - 阻止 DELETE
    print("\n" + "-"*60)
    print("[测试 4] 安全测试：尝试执行 DELETE (应该被阻止)")
    print("-"*60)
    
    result = await _execute_sql("DELETE FROM users WHERE id=1")
    
    if not result["success"]:
        print(f"✅ 安全拦截成功")
        print(f"  拦截原因：{result['error']}")
    else:
        print(f"❌ 安全拦截失败！危险 SQL 被执行了！")
        return False
    
    # 测试 5: 安全测试 - 阻止 DROP
    print("\n" + "-"*60)
    print("[测试 5] 安全测试：尝试执行 DROP (应该被阻止)")
    print("-"*60)
    
    result = await _execute_sql("DROP TABLE users")
    
    if not result["success"]:
        print(f"✅ 安全拦截成功")
        print(f"  拦截原因：{result['error']}")
    else:
        print(f"❌ 安全拦截失败！危险 SQL 被执行了！")
        return False
    
    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)
    
    return True


async def test_workflow_with_real_db():
    """测试完整工作流 + 真实数据库"""
    print("\n" + "="*60)
    print("🚀 完整工作流 + 真实数据库测试")
    print("="*60)
    
    from app.workflows.graph import workflow_app
    
    # 测试查询
    test_queries = [
        "查询所有表",
        "你好",  # 闲聊测试
    ]
    
    for query in test_queries:
        print(f"\n[测试] 查询：'{query}'")
        print("-"*60)
        
        initial_state = {
            "messages": [],
            "user_query": query,
            "thread_id": f"test-{query}",
            "agent_id": "1",
            "multi_turn_context": None,
            "evidence": None,
            "canonical_query": None,
            "table_documents": [],
            "column_documents": [],
            "schema_relations": None,
            "is_feasible": None,
            "plan": None,
            "plan_validation_status": None,
            "plan_validation_error": None,
            "plan_current_step": 1,
            "plan_next_node": None,
            "plan_repair_count": 0,
            "generated_sql": None,
            "sql_validation": None,
            "sql_result": None,
            "sql_generate_count": 0,
            "sql_regenerate_reason": None,
            "semantic_consistency_output": None,
            "is_only_nl2sql": True,
            "human_review_enabled": False,
            "human_feedback_data": None,
            "intent_recognition_output": None,
            "feasibility_assessment_output": None,
            "error": None
        }
        
        try:
            result = await workflow_app.ainvoke(initial_state)
            
            print(f"  意图识别：{'需要分析' if result.get('intent_recognition_output') else '闲聊'}")
            
            if result.get("generated_sql"):
                print(f"  生成 SQL: {result['generated_sql'][:100]}")
            
            sql_result = result.get("sql_result", {})
            if sql_result:
                if sql_result.get("success"):
                    print(f"  ✅ SQL 执行成功：返回 {sql_result.get('row_count', 0)} 行数据")
                    if sql_result.get("data"):
                        print(f"  示例数据：{sql_result['data'][0]}")
                else:
                    print(f"  ❌ SQL 执行失败：{sql_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"  ❌ 工作流执行失败：{str(e)}")
    
    print("\n" + "="*60)


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 真实数据库连接测试套件")
    print("="*60)
    
    try:
        # 测试 1: MySQL 连接
        success = await test_mysql_connection()
        
        if success:
            # 测试 2: 完整工作流
            await test_workflow_with_real_db()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
