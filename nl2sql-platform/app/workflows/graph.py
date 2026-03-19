"""
LangGraph 工作流图构建

参考 DataAgent 的完整节点设计，当前实现：
- IntentRecognitionNode - 意图识别
- QueryEnhanceNode - 查询重写（多轮对话）
- SchemaRecallNode - Schema 检索
- TableRelationNode - 表关系分析
- FeasibilityAssessmentNode - 可行性评估
- PlannerNode - 任务规划 ✨ NEW
- PlanExecutorNode - 计划执行调度 ✨ NEW
- SQLGenerateNode - SQL 生成
- SemanticConsistencyNode - 语义一致性校验 ✨ NEW
- SQLExecuteNode - SQL 执行
"""
from langgraph.graph import StateGraph, END
from app.workflows.state import NL2SQLState
from app.workflows.nodes import (
    intent_recognition_node,
    query_enhance_node,
    schema_recall_node,
    table_relation_node,
    feasibility_assessment_node,
    planner_node,
    plan_executor_node,
    sql_generate_node,
    semantic_consistency_node,
    sql_execute_node
)
import structlog

logger = structlog.get_logger()


def _route_after_intent(state: dict) -> str:
    """
    意图识别后的路由逻辑
    
    参考 DataAgent 的条件边设计：
    - need_analysis=true → QUERY_ENHANCE_NODE
    - need_analysis=false → END（闲聊直接结束）
    """
    intent_output = state.get("intent_recognition_output")
    if not intent_output:
        logger.warning("No intent output found, routing to END")
        return END
    
    need_analysis = getattr(intent_output, 'need_analysis', False)
    if isinstance(intent_output, dict):
        need_analysis = intent_output.get('need_analysis', False)
    
    if need_analysis:
        logger.debug("Intent requires analysis, routing to QUERY_ENHANCE_NODE")
        return "QUERY_ENHANCE_NODE"
    else:
        logger.info("Intent is chat-only, routing to END")
        return END


def _route_after_feasibility(state: dict) -> str:
    """
    可行性评估后的路由逻辑
    
    - is_feasible=true → PLANNER_NODE
    - is_feasible=false → END（提前结束）
    """
    is_feasible = state.get("is_feasible", False)
    
    if is_feasible:
        logger.debug("Feasibility check passed, routing to PLANNER_NODE")
        return "PLANNER_NODE"
    else:
        logger.info("Feasibility check failed, routing to END")
        return END


def _route_after_plan_executor(state: dict) -> str:
    """
    计划执行调度后的路由逻辑
    
    根据 plan_next_node 决定下一个节点
    """
    plan_next_node = state.get("plan_next_node")
    plan_validation_status = state.get("plan_validation_status", False)
    
    if not plan_validation_status:
        logger.warning("Plan validation failed")
        return "PLANNER_NODE"  # 重新规划
    
    if not plan_next_node:
        logger.warning("No plan_next_node found, routing to END")
        return END
    
    logger.info(f"Plan executor routing to: {plan_next_node}")
    return plan_next_node


def create_workflow() -> StateGraph:
    """
    创建 NL2SQL 工作流（10 节点完整版，支持多步骤分析 + 语义一致性校验）
    
    工作流顺序：
    1. IntentRecognitionNode → 意图识别
    2. QueryEnhanceNode → 查询重写
    3. SchemaRecallNode → Schema 检索
    4. TableRelationNode → 表关系分析
    5. FeasibilityAssessmentNode → 可行性评估
    6. PlannerNode → 任务规划 ✨
    7. PlanExecutorNode → 计划执行调度 ✨
    8. SQLGenerateNode → SQL 生成
    9. SemanticConsistencyNode → 语义一致性校验 ✨ NEW
    10. SQLExecuteNode → SQL 执行
    
    Returns:
        StateGraph: 编译后的工作流
    """
    logger.info("Creating NL2SQL workflow (10 nodes)")
    
    # 创建工作流图
    workflow = StateGraph(NL2SQLState)
    
    # ========== 添加节点 ==========
    workflow.add_node("INTENT_RECOGNITION_NODE", intent_recognition_node)
    workflow.add_node("QUERY_ENHANCE_NODE", query_enhance_node)
    workflow.add_node("SCHEMA_RECALL_NODE", schema_recall_node)
    workflow.add_node("TABLE_RELATION_NODE", table_relation_node)
    workflow.add_node("FEASIBILITY_ASSESSMENT_NODE", feasibility_assessment_node)
    workflow.add_node("PLANNER_NODE", planner_node)
    workflow.add_node("PLAN_EXECUTOR_NODE", plan_executor_node)
    workflow.add_node("SQL_GENERATE_NODE", sql_generate_node)
    workflow.add_node("SEMANTIC_CONSISTENCY_NODE", semantic_consistency_node)
    workflow.add_node("SQL_EXECUTE_NODE", sql_execute_node)
    
    # ========== 定义边 ==========
    
    # 设置入口节点
    workflow.set_entry_point("INTENT_RECOGNITION_NODE")
    
    # 1. IntentRecognitionNode → QueryEnhanceNode or END
    workflow.add_conditional_edges(
        "INTENT_RECOGNITION_NODE",
        lambda state: _route_after_intent(state),
        {
            "QUERY_ENHANCE_NODE": "QUERY_ENHANCE_NODE",
            END: END
        }
    )
    
    # 2. QueryEnhanceNode → SchemaRecallNode or END
    workflow.add_conditional_edges(
        "QUERY_ENHANCE_NODE",
        lambda state: "SCHEMA_RECALL_NODE" if state.get("canonical_query") else END,
        {
            "SCHEMA_RECALL_NODE": "SCHEMA_RECALL_NODE",
            END: END
        }
    )
    
    # 3. SchemaRecallNode → TableRelationNode or END
    workflow.add_conditional_edges(
        "SCHEMA_RECALL_NODE",
        lambda state: "TABLE_RELATION_NODE" if state.get("table_documents") else END,
        {
            "TABLE_RELATION_NODE": "TABLE_RELATION_NODE",
            END: END
        }
    )
    
    # 4. TableRelationNode → FeasibilityAssessmentNode or END
    workflow.add_conditional_edges(
        "TABLE_RELATION_NODE",
        lambda state: "FEASIBILITY_ASSESSMENT_NODE" if state.get("schema_relations") else END,
        {
            "FEASIBILITY_ASSESSMENT_NODE": "FEASIBILITY_ASSESSMENT_NODE",
            END: END
        }
    )
    
    # 5. FeasibilityAssessmentNode → PlannerNode or END
    workflow.add_conditional_edges(
        "FEASIBILITY_ASSESSMENT_NODE",
        lambda state: "PLANNER_NODE" if state.get("is_feasible") else END,
        {
            "PLANNER_NODE": "PLANNER_NODE",
            END: END
        }
    )
    
    # 6. PlannerNode → PlanExecutorNode
    workflow.add_edge("PLANNER_NODE", "PLAN_EXECUTOR_NODE")
    
    # 7. PlanExecutorNode → 动态路由到具体节点
    # 注意：目前只实现了 SQL_GENERATE_NODE，其他节点待实现
    workflow.add_conditional_edges(
        "PLAN_EXECUTOR_NODE",
        lambda state: _route_after_plan_executor(state),
        {
            "SQL_GENERATE_NODE": "SQL_GENERATE_NODE",
            # 以下节点待实现
            # "PYTHON_GENERATE_NODE": "PYTHON_GENERATE_NODE",
            # "REPORT_GENERATOR_NODE": "REPORT_GENERATOR_NODE",
            # "HUMAN_FEEDBACK_NODE": "HUMAN_FEEDBACK_NODE",
            END: END
        }
    )
    
    # 8. SQL_GENERATE_NODE → SemanticConsistencyNode
    workflow.add_edge("SQL_GENERATE_NODE", "SEMANTIC_CONSISTENCY_NODE")
    
    # 9. SemanticConsistencyNode → SQL_EXECUTE_NODE or SQL_GENERATE_NODE (重试)
    workflow.add_conditional_edges(
        "SEMANTIC_CONSISTENCY_NODE",
        lambda state: (
            "SQL_EXECUTE_NODE" 
            if state.get("sql_validation", {}).get("is_valid", False)
            else "PLAN_EXECUTOR_NODE"  # 语义不一致，重新规划/重试
        ),
        {
            "SQL_EXECUTE_NODE": "SQL_EXECUTE_NODE",
            "PLAN_EXECUTOR_NODE": "PLAN_EXECUTOR_NODE"
        }
    )
    
    # 10. SQL_EXECUTE_NODE → PlanExecutorNode (执行下一步) or END
    workflow.add_conditional_edges(
        "SQL_EXECUTE_NODE",
        lambda state: (
            "PLAN_EXECUTOR_NODE" 
            if state.get("sql_regenerate_reason") and not state.get("generated_sql", "").startswith("--")
            else "PLAN_EXECUTOR_NODE"  # 执行完成后回到 PlanExecutorNode
        ),
        {
            "PLAN_EXECUTOR_NODE": "PLAN_EXECUTOR_NODE"
        }
    )
    
    # ========== 编译工作流 ==========
    app = workflow.compile()
    
    logger.info("NL2SQL workflow created successfully (9 nodes)")
    
    return app


# 创建全局工作流实例
workflow_app = create_workflow()
