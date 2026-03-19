"""
8. PlanExecutorNode - 计划执行调度节点

完全参考 DataAgent 项目的 PlanExecutorNode 实现：
- 解析执行计划
- 验证计划合法性
- 决定下一个执行节点
- 管理执行步骤进度
- 支持人工复核

项目地址：https://github.com/spring-ai-alibaba/spring-ai-alibaba
文件：PlanExecutorNode.java
"""
from app.workflows.state import NL2SQLState
from langgraph.graph import StateGraph, END
import structlog

logger = structlog.get_logger()


# 支持的节点类型
SUPPORTED_NODES = {
    "SQL_GENERATE_NODE",
    "PYTHON_GENERATE_NODE",
    "REPORT_GENERATOR_NODE",
    "HUMAN_FEEDBACK_NODE"
}


async def plan_executor_node(state: NL2SQLState) -> dict:
    """
    计划执行调度节点
    
    参考 DataAgent 的实现流程：
    1. 获取并验证执行计划
    2. 验证计划结构
    3. 验证每个步骤
    4. 检查人工复核
    5. 获取当前步骤
    6. 决定下一个节点
    7. 返回执行指令
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含下一个节点信息
    """
    logger.info("Starting plan execution")
    
    # ========== 流式反馈：开始执行计划 ==========
    logger.info("开始执行任务计划...")
    
    try:
        # 1. 获取计划
        plan = state.get("plan")
        if not plan:
            logger.error("计划为空")
            return {
                "plan_validation_status": False,
                "plan_validation_error": "计划为空",
                "plan_next_node": END
            }
        
        # 2. 验证计划格式
        try:
            execution_plan = plan.get("execution_plan", [])
            if not execution_plan:
                raise ValueError("执行计划为空")
        except Exception as e:
            logger.error(f"计划解析失败：{str(e)}")
            return {
                "plan_validation_status": False,
                "plan_validation_error": f"计划格式错误：{str(e)}",
                "plan_next_node": "PLANNER_NODE"  # 重新规划
            }
        
        # 3. 验证计划结构
        if not _validate_execution_plan_structure(plan):
            logger.error("计划结构验证失败")
            return {
                "plan_validation_status": False,
                "plan_validation_error": "计划结构验证失败：执行计划为空或没有步骤",
                "plan_next_node": "PLANNER_NODE"
            }
        
        # 4. 验证每个步骤
        validation_error = _validate_steps(execution_plan)
        if validation_error:
            logger.error(f"步骤验证失败：{validation_error}")
            return {
                "plan_validation_status": False,
                "plan_validation_error": validation_error,
                "plan_next_node": "PLANNER_NODE"
            }
        
        logger.info("计划验证通过")
        
        # 5. 检查人工复核
        human_review_enabled = state.get("human_review_enabled", False)
        if human_review_enabled:
            logger.info("人工复核已启用，路由到人工复核节点")
            return {
                "plan_validation_status": True,
                "plan_next_node": "HUMAN_FEEDBACK_NODE"
            }
        
        # 6. 获取当前步骤
        current_step = state.get("plan_current_step", 1)
        total_steps = len(execution_plan)
        
        logger.info(f"当前步骤：{current_step}, 总步骤数：{total_steps}")
        
        # 7. 检查是否完成
        if current_step > total_steps:
            logger.info("计划执行完成")
            return {
                "plan_current_step": 1,  # 重置为 1，为下次查询准备
                "plan_next_node": END,
                "plan_validation_status": True
            }
        
        # 8. 获取当前步骤
        current_step_data = execution_plan[current_step - 1]
        tool_to_use = current_step_data.get("tool_to_use", "")
        
        logger.info(f"步骤 {current_step} 的工具：{tool_to_use}")
        
        # 9. 决定下一个节点
        if tool_to_use in SUPPORTED_NODES:
            logger.info(f"路由到节点：{tool_to_use}")
            return {
                "plan_next_node": tool_to_use,
                "plan_current_step": current_step + 1,
                "plan_validation_status": True
            }
        else:
            logger.error(f"不支持的节点类型：{tool_to_use}")
            return {
                "plan_validation_status": False,
                "plan_validation_error": f"不支持的节点类型：{tool_to_use}",
                "plan_next_node": "PLANNER_NODE"
            }
        
    except Exception as e:
        logger.error(f"计划执行失败：{str(e)}", exc_info=True)
        return {
            "plan_validation_status": False,
            "plan_validation_error": f"计划执行失败：{str(e)}",
            "plan_next_node": "PLANNER_NODE"
        }


def _validate_execution_plan_structure(plan: dict) -> bool:
    """
    验证执行计划结构
    
    Args:
        plan: 执行计划
        
    Returns:
        bool: 是否有效
    """
    if not plan:
        return False
    
    execution_plan = plan.get("execution_plan", [])
    if not execution_plan:
        return False
    
    if not isinstance(execution_plan, list):
        return False
    
    return True


def _validate_steps(execution_plan: list) -> str:
    """
    验证每个执行步骤
    
    Args:
        execution_plan: 执行步骤列表
        
    Returns:
        str: 错误信息（如果有），否则为 None
    """
    for i, step in enumerate(execution_plan):
        # 验证步骤编号
        if "step" not in step:
            return f"验证失败：步骤 {i+1} 缺少 step 字段"
        
        # 验证工具名称
        tool_to_use = step.get("tool_to_use")
        if not tool_to_use:
            return f"验证失败：步骤 {step.get('step')} 缺少 tool_to_use 字段"
        
        if tool_to_use not in SUPPORTED_NODES:
            return f"验证失败：步骤 {step.get('step')} 包含不支持的工具：'{tool_to_use}'"
        
        # 验证工具参数
        tool_parameters = step.get("tool_parameters")
        if not tool_parameters:
            return f"验证失败：步骤 {step.get('step')} 缺少 tool_parameters"
        
        # 根据节点类型验证特定参数
        if tool_to_use == "SQL_GENERATE_NODE":
            instruction = tool_parameters.get("instruction")
            if not instruction:
                return f"验证失败：SQL_GENERATE_NODE 在步骤 {step.get('step')} 缺少 instruction"
        
        elif tool_to_use == "PYTHON_GENERATE_NODE":
            instruction = tool_parameters.get("instruction")
            if not instruction:
                return f"验证失败：PYTHON_GENERATE_NODE 在步骤 {step.get('step')} 缺少 instruction"
        
        elif tool_to_use == "REPORT_GENERATOR_NODE":
            summary = tool_parameters.get("summary_and_recommendations")
            if not summary:
                return f"验证失败：REPORT_GENERATOR_NODE 在步骤 {step.get('step')} 缺少 summary_and_recommendations"
    
    return None


def _build_validation_result(state: NL2SQLState, is_valid: bool, error_message: str) -> dict:
    """
    构建验证结果
    
    Args:
        state: 工作流状态
        is_valid: 是否有效
        error_message: 错误信息
        
    Returns:
        dict: 验证结果
    """
    if is_valid:
        return {
            "plan_validation_status": True,
            "plan_next_node": state.get("plan_next_node", "PLANNER_NODE")
        }
    else:
        return {
            "plan_validation_status": False,
            "plan_validation_error": error_message,
            "plan_next_node": "PLANNER_NODE"
        }
