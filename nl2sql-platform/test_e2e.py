"""
NL2SQL 平台 - 端到端完整测试

测试所有已完成的功能：
1. 意图识别
2. Schema 检索
3. SQL 生成 (GLM-4)
4. SQL 执行 (真实 MySQL)
5. 安全防护
"""
import asyncio
import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflows.graph import workflow_app
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


# 测试用例
TEST_CASES = [
    {
        "name": "简单查询 - 用户列表",
        "query": "查询所有用户",
        "expected": {
            "intent": True,  # 需要分析
            "has_sql": True,
            "success": True
        }
    },
    {
        "name": "聚合查询 - 统计订单",
        "query": "统计订单总数",
        "expected": {
            "intent": True,
            "has_sql": True,
            "success": True
        }
    },
    {
        "name": "复杂查询 - JOIN",
        "query": "查询用户和订单信息",
        "expected": {
            "intent": True,
            "has_sql": True,
            "success": True
        }
    },
    {
        "name": "闲聊 - 问候",
        "query": "你好",
        "expected": {
            "intent": False,  # 闲聊
            "has_sql": False,
            "success": True
        }
    },
    {
        "name": "闲聊 - 感谢",
        "query": "谢谢",
        "expected": {
            "intent": False,
            "has_sql": False,
            "success": True
        }
    },
]


def create_initial_state(query: str, thread_id: str) -> dict:
    """创建工作流初始状态"""
    return {
        "messages": [],
        "user_query": query,
        "thread_id": thread_id,
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


async def test_single_case(test_case: dict) -> bool:
    """测试单个用例"""
    print(f"\n{'='*60}")
    print(f"[测试] {test_case['name']}")
    print(f"  查询：'{test_case['query']}'")
    print(f"{'='*60}")
    
    try:
        # 执行工作流
        result = await workflow_app.ainvoke(
            create_initial_state(
                test_case['query'],
                f"test-{test_case['name']}"
            )
        )
        
        # 验证结果
        success = True
        
        # 1. 验证意图识别
        intent = result.get('intent_recognition_output', False)
        expected_intent = test_case['expected']['intent']
        if intent != expected_intent:
            print(f"  ❌ 意图识别失败：期望 {expected_intent}, 实际 {intent}")
            success = False
        else:
            print(f"  ✅ 意图识别：{'需要分析' if intent else '闲聊'}")
        
        # 2. 验证 SQL 生成
        has_sql = bool(result.get('generated_sql'))
        expected_has_sql = test_case['expected']['has_sql']
        if has_sql != expected_has_sql:
            print(f"  ❌ SQL 生成失败：期望 {expected_has_sql}, 实际 {has_sql}")
            success = False
        else:
            if has_sql:
                sql = result['generated_sql']
                print(f"  ✅ SQL 生成：{sql[:100]}...")
        
        # 3. 验证 SQL 执行
        sql_result = result.get('sql_result', {})
        if test_case['expected']['success']:
            if sql_result:
                if sql_result.get('success'):
                    row_count = sql_result.get('row_count', 0)
                    print(f"  ✅ SQL 执行成功：返回 {row_count} 行数据")
                    if sql_result.get('data'):
                        print(f"  📊 示例数据：{json.dumps(sql_result['data'][0], ensure_ascii=False, default=str)[:100]}")
                else:
                    print(f"  ❌ SQL 执行失败：{sql_result.get('error', 'Unknown error')}")
                    success = False
            elif not test_case['expected']['has_sql']:
                # 闲聊不需要 SQL 执行
                print(f"  ✅ 无需 SQL 执行")
        
        # 4. 检查错误
        if result.get('error'):
            print(f"  ⚠️ 错误：{result['error']}")
        
        return success
        
    except Exception as e:
        print(f"  ❌ 测试异常：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_security():
    """测试安全防护"""
    print(f"\n{'='*60}")
    print("[安全测试] 危险 SQL 拦截")
    print(f"{'='*60}")
    
    from app.workflows.nodes.sql_execute_node import _execute_sql
    
    dangerous_sqls = [
        "DELETE FROM users WHERE id=1",
        "DROP TABLE users",
        "UPDATE users SET username='hacked'",
        "INSERT INTO users VALUES (1, 'hacker', 'hacker@test.com')",
    ]
    
    all_blocked = True
    
    for sql in dangerous_sqls:
        print(f"\n  尝试执行：{sql[:50]}...")
        result = await _execute_sql(sql)
        
        if not result.get('success'):
            print(f"  ✅ 成功拦截：{result.get('error', 'Unknown error')}")
        else:
            print(f"  ❌ 拦截失败！危险 SQL 被执行了！")
            all_blocked = False
    
    return all_blocked


async def test_database_connection():
    """测试数据库连接"""
    print(f"\n{'='*60}")
    print("[数据库测试] MySQL 连接验证")
    print(f"{'='*60}")
    
    from app.workflows.nodes.sql_execute_node import _execute_sql
    
    # 测试连接
    result = await _execute_sql("SELECT 1 as test")
    
    if result.get('success'):
        print(f"  ✅ MySQL 连接成功")
        print(f"  📊 测试结果：{result['data']}")
        return True
    else:
        print(f"  ❌ MySQL 连接失败：{result.get('error')}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 NL2SQL 平台 - 端到端完整测试")
    print("="*60)
    print(f"\n数据库：{MySQLConfig.DATABASE}@{MySQLConfig.HOST}:{MySQLConfig.PORT}")
    print(f"LLM: ZhipuAI GLM-4")
    print(f"测试用例：{len(TEST_CASES)} 个")
    
    # 测试 1: 数据库连接
    db_ok = await test_database_connection()
    if not db_ok:
        print("\n❌ 数据库连接失败，终止测试！")
        return False
    
    # 测试 2: 安全防护
    security_ok = await test_security()
    if not security_ok:
        print("\n❌ 安全防护测试失败！")
        return False
    
    # 测试 3: 功能测试
    print("\n" + "="*60)
    print("[功能测试] NL2SQL 完整流程")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_case in TEST_CASES:
        success = await test_single_case(test_case)
        if success:
            passed += 1
        else:
            failed += 1
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    print(f"  总用例数：{len(TEST_CASES)}")
    print(f"  ✅ 通过：{passed}")
    print(f"  ❌ 失败：{failed}")
    print(f"  通过率：{passed/len(TEST_CASES)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print(f"\n⚠️ {failed} 个测试失败")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
