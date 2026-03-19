#!/usr/bin/env python3
"""
NL2SQL 工作流测试脚本

测试现有功能：
1. IntentRecognitionNode - 意图识别
2. SQLGenerateNode - SQL 生成（Mock）
3. SQLExecuteNode - SQL 执行（Mock）
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workflows.graph import workflow_app
import structlog

# 配置日志输出到控制台
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


async def test_intent_recognition():
    """测试 1: 意图识别"""
    print("\n" + "="*60)
    print("测试 1: 意图识别")
    print("="*60)
    
    # 测试用例 1: 查询类问题（应该识别为需要分析）
    print("\n[测试 1.1] 查询类问题")
    initial_state = {
        "messages": [],
        "user_query": "查询订单数量最多的用户",
        "thread_id": "test-1",
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
    
    result = await workflow_app.ainvoke(initial_state)
    
    print(f"用户问题：{result['user_query']}")
    print(f"意图识别结果：{result['intent_recognition_output']}")
    print(f"生成的 SQL: {result.get('generated_sql', 'N/A')[:100] if result.get('generated_sql') else 'N/A'}")
    print(f"SQL 执行结果：{result.get('sql_result', {})}")
    
    assert result['intent_recognition_output'] == True, "应该识别为需要分析"
    print("✅ 测试 1.1 通过")
    
    # 测试用例 2: 闲聊（应该识别为不需要分析）
    print("\n[测试 1.2] 闲聊问候")
    initial_state["user_query"] = "你好"
    initial_state["thread_id"] = "test-2"
    
    result = await workflow_app.ainvoke(initial_state)
    
    print(f"用户问题：{result['user_query']}")
    print(f"意图识别结果：{result['intent_recognition_output']}")
    print(f"回复消息：{result.get('messages', [])}")
    
    assert result['intent_recognition_output'] == False, "应该识别为闲聊"
    print("✅ 测试 1.2 通过")
    
    print("\n✅ 测试 1 全部通过！")


async def test_sql_generation():
    """测试 2: SQL 生成"""
    print("\n" + "="*60)
    print("测试 2: SQL 生成（Mock）")
    print("="*60)
    
    initial_state = {
        "messages": [],
        "user_query": "统计销售额",
        "thread_id": "test-3",
        "agent_id": "1",
        "multi_turn_context": None,
        "evidence": None,
        "canonical_query": "统计销售额",
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
        "intent_recognition_output": True,
        "feasibility_assessment_output": None,
        "error": None
    }
    
    result = await workflow_app.ainvoke(initial_state)
    
    print(f"用户问题：{result['user_query']}")
    print(f"生成的 SQL: {result.get('generated_sql', 'N/A')}")
    print(f"SQL 执行结果：{result.get('sql_result', {})}")
    
    # 验证 SQL 生成（Mock 实现应该返回 SELECT * FROM users LIMIT 10;）
    assert result.get('generated_sql') is not None, "应该生成 SQL"
    print("✅ 测试 2 通过！")


async def test_full_workflow():
    """测试 3: 完整工作流"""
    print("\n" + "="*60)
    print("测试 3: 完整工作流（Intent → SQL Generate → SQL Execute）")
    print("="*60)
    
    test_cases = [
        "查询订单数量",
        "统计用户总数",
        "计算平均价格",
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n[测试 3.{i}] 查询：{query}")
        
        initial_state = {
            "messages": [],
            "user_query": query,
            "thread_id": f"test-full-{i}",
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
        
        result = await workflow_app.ainvoke(initial_state)
        
        print(f"  意图识别：{'✅ 需要分析' if result['intent_recognition_output'] else '❌ 不需要'}")
        print(f"  生成 SQL: {result.get('generated_sql', 'N/A')[:80] if result.get('generated_sql') else 'N/A'}")
        
        sql_result = result.get('sql_result', {})
        if sql_result:
            success = sql_result.get('success', False)
            row_count = sql_result.get('row_count', 0)
            print(f"  执行结果：{'✅ 成功' if success else '❌ 失败'} (返回 {row_count} 行)")
        
        print()


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 NL2SQL 工作流测试")
    print("="*60)
    
    try:
        # 测试 1: 意图识别
        await test_intent_recognition()
        
        # 测试 2: SQL 生成
        await test_sql_generation()
        
        # 测试 3: 完整工作流
        await test_full_workflow()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
