"""
Schema 导入后测试

验证 GLM 能否基于真实 Schema 生成准确的 SQL
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflows.graph import workflow_app
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


async def test_nl2sql_with_real_schema():
    """测试 NL2SQL 完整流程（真实 Schema + 真实数据库）"""
    print("\n" + "="*60)
    print("🚀 NL2SQL 完整流程测试（真实 Schema + 真实数据库）")
    print("="*60)
    
    # 测试查询
    test_queries = [
        "查询所有用户",
        "查询订单信息",
        "查询商品列表",
        "统计订单数量",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"[查询] '{query}'")
        print(f"{'='*60}")
        
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
            
            # 显示结果
            print(f"\n✅ 工作流执行完成")
            print(f"  意图识别：{'需要分析' if result.get('intent_recognition_output') else '闲聊'}")
            
            if result.get("generated_sql"):
                print(f"\n📝 生成的 SQL:")
                print(f"  {result['generated_sql'][:200]}")
            
            sql_result = result.get("sql_result", {})
            if sql_result:
                if sql_result.get("success"):
                    print(f"\n✅ SQL 执行成功")
                    print(f"  返回行数：{sql_result.get('row_count', 0)}")
                    print(f"  列名：{sql_result.get('columns', [])}")
                    if sql_result.get("data"):
                        print(f"  第 1 行数据：{sql_result['data'][0]}")
                else:
                    print(f"\n❌ SQL 执行失败：{sql_result.get('error', 'Unknown error')}")
            
            if result.get("error"):
                print(f"\n⚠️ 错误：{result['error']}")
            
        except Exception as e:
            print(f"\n❌ 工作流执行失败：{str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)


async def main():
    """主测试函数"""
    try:
        await test_nl2sql_with_real_schema()
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
