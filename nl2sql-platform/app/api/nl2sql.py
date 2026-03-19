"""
NL2SQL API 路由
"""
from fastapi import APIRouter, HTTPException
from app.schemas import NL2SQLRequest, NL2SQLResponse, NL2SQLStreamResponse
from app.workflows.graph import workflow_app
import structlog
import uuid

logger = structlog.get_logger()

router = APIRouter()


@router.post("/query", response_model=NL2SQLResponse)
async def nl2sql_query(request: NL2SQLRequest):
    """
    NL2SQL 查询接口（同步）
    
    将自然语言转换为 SQL 并执行
    """
    logger.info(
        "NL2SQL query received",
        query=request.query,
        agent_id=request.agent_id,
        thread_id=request.thread_id
    )
    
    try:
        # 生成或使用已有 thread_id
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # 初始化工作流状态
        initial_state = {
            "messages": [],
            "user_query": request.query,
            "thread_id": thread_id,
            "agent_id": request.agent_id,
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
            "human_review_enabled": request.human_feedback,
            "human_feedback_data": None,
            "intent_recognition_output": None,
            "feasibility_assessment_output": None,
            "error": None
        }
        
        # 执行工作流
        result = await workflow_app.ainvoke(initial_state)
        
        # 构建响应
        response = NL2SQLResponse(
            thread_id=thread_id,
            query=request.query,
            canonical_query=result.get("canonical_query"),
            generated_sql=result.get("generated_sql"),
            sql_result=result.get("sql_result"),
            error=result.get("error")
        )
        
        logger.info(
            "NL2SQL query completed",
            thread_id=thread_id,
            sql=result.get("generated_sql", "")[:100] if result.get("generated_sql") else None
        )
        
        return response
        
    except Exception as e:
        logger.error("NL2SQL query failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"查询失败：{str(e)}"
        )


@router.post("/stream")
async def nl2sql_stream(request: NL2SQLRequest):
    """
    NL2SQL 流式接口（SSE）
    
    实时推送工作流执行进度
    """
    from fastapi.responses import StreamingResponse
    import json
    
    logger.info(
        "NL2SQL stream request received",
        query=request.query,
        agent_id=request.agent_id
    )
    
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # 初始化状态
    initial_state = {
        "messages": [],
        "user_query": request.query,
        "thread_id": thread_id,
        "agent_id": request.agent_id,
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
        "human_review_enabled": request.human_feedback,
        "human_feedback_data": None,
        "intent_recognition_output": None,
        "feasibility_assessment_output": None,
        "error": None
    }
    
    # 流式生成器
    async def generate():
        try:
            # 使用 astream 流式执行
            async for event in workflow_app.astream(initial_state):
                node_name = list(event.keys())[0]
                output = event[node_name]
                
                # 将 Pydantic 模型转换为字典后再序列化
                if hasattr(output, 'model_dump'):
                    output_dict = output.model_dump()
                elif hasattr(output, 'dict'):
                    output_dict = output.dict()
                elif isinstance(output, dict):
                    output_dict = output
                else:
                    output_dict = {"output": str(output)}
                
                # 构建流式响应
                response = NL2SQLStreamResponse(
                    thread_id=thread_id,
                    node_name=node_name,
                    text_type="TEXT",
                    text=json.dumps(output_dict, ensure_ascii=False, default=str)[:500],  # 截断避免过大
                    error=False,
                    complete=False
                )
                
                yield f"data: {response.json()}\n\n"
            
            # 完成
            complete_response = NL2SQLStreamResponse(
                thread_id=thread_id,
                node_name="END",
                text_type="TEXT",
                text="",
                complete=True
            )
            yield f"data: {complete_response.json()}\n\n"
            
        except Exception as e:
            logger.error("Stream failed", error=str(e), exc_info=True)
            error_response = NL2SQLStreamResponse(
                thread_id=thread_id,
                node_name="ERROR",
                text_type="TEXT",
                text=str(e),
                error=True
            )
            yield f"data: {error_response.json()}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stream/tokens")
async def nl2sql_stream_tokens(request: NL2SQLRequest):
    """
    NL2SQL Token 级流式接口（SSE）
    
    实时推送 LLM 生成的每个 token，提供最佳用户体验
    
    流式事件类型：
    - node_start: 节点开始执行
    - token: LLM token
    - node_complete: 节点执行完成
    - complete: 全部完成
    - error: 错误
    """
    from fastapi.responses import StreamingResponse
    from app.services.llm_service import stream_llm_tokens, stream_llm_tokens_with_temperature
    from app.workflows.nodes import intent_recognition_node, query_enhance_node, planner_node, sql_generate_node
    import json
    
    logger.info(
        "NL2SQL token stream request received",
        query=request.query,
        agent_id=request.agent_id
    )
    
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # 流式生成器
    async def generate():
        try:
            # 1. 意图识别 - 流式
            yield _make_event("node_start", {"node": "INTENT_RECOGNITION", "message": "正在识别意图..."})
            
            intent_prompt = _build_intent_prompt(request.query)
            intent_tokens = []
            async for token in stream_llm_tokens(intent_prompt):
                intent_tokens.append(token)
                yield _make_event("token", {
                    "node": "INTENT_RECOGNITION",
                    "token": token,
                    "cumulative": "".join(intent_tokens)
                })
            
            intent_result = "".join(intent_tokens).strip()
            yield _make_event("node_complete", {
                "node": "INTENT_RECOGNITION",
                "result": intent_result[:200]
            })
            
            # 2. 查询增强 - 流式
            yield _make_event("node_start", {"node": "QUERY_ENHANCE", "message": "正在重写查询..."})
            
            enhance_prompt = _build_enhance_prompt(request.query)
            enhance_tokens = []
            async for token in stream_llm_tokens_with_temperature(enhance_prompt, temperature=0.1):
                enhance_tokens.append(token)
                yield _make_event("token", {
                    "node": "QUERY_ENHANCE",
                    "token": token,
                    "cumulative": "".join(enhance_tokens)
                })
            
            enhance_result = "".join(enhance_tokens).strip()
            yield _make_event("node_complete", {
                "node": "QUERY_ENHANCE",
                "result": enhance_result[:200]
            })
            
            # 3. 任务规划 - 流式
            yield _make_event("node_start", {"node": "PLANNER", "message": "正在生成执行计划..."})
            
            plan_prompt = _build_plan_prompt(request.query)
            plan_tokens = []
            async for token in stream_llm_tokens_with_temperature(plan_prompt, temperature=0.1):
                plan_tokens.append(token)
                yield _make_event("token", {
                    "node": "PLANNER",
                    "token": token,
                    "cumulative": "".join(plan_tokens)
                })
            
            plan_result = "".join(plan_tokens).strip()
            yield _make_event("node_complete", {
                "node": "PLANNER",
                "result": plan_result[:200]
            })
            
            # 4. SQL 生成 - 流式
            yield _make_event("node_start", {"node": "SQL_GENERATE", "message": "正在生成 SQL..."})
            
            sql_prompt = _build_sql_prompt(request.query)
            sql_tokens = []
            async for token in stream_llm_tokens(sql_prompt):
                sql_tokens.append(token)
                yield _make_event("token", {
                    "node": "SQL_GENERATE",
                    "token": token,
                    "cumulative": "".join(sql_tokens)
                })
            
            sql_result = "".join(sql_tokens).strip()
            yield _make_event("node_complete", {
                "node": "SQL_GENERATE",
                "result": sql_result
            })
            
            # 完成
            yield _make_event("complete", {
                "thread_id": thread_id,
                "nodes_completed": 4
            })
            
        except Exception as e:
            logger.error("Token stream failed", error=str(e), exc_info=True)
            yield _make_event("error", {"error": str(e)})
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )


def _make_event(event_type: str, data: dict) -> str:
    """构建 SSE 事件"""
    import json
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_intent_prompt(query: str) -> str:
    """构建意图识别 Prompt"""
    return f"""判断用户查询是否需要数据库分析：
【查询】{query}
【输出格式】JSON: {{"need_analysis": true/false, "intent_type": "DATA_ANALYSIS/CHAT", "confidence": 0-1, "reason": "理由"}}
【输出】"""


def _build_enhance_prompt(query: str) -> str:
    """构建查询增强 Prompt"""
    return f"""重写查询为标准格式：
【查询】{query}
【输出】规范化查询："""


def _build_plan_prompt(query: str) -> str:
    """构建任务规划 Prompt"""
    return f"""生成执行计划：
【查询】{query}
【输出格式】JSON: {{"thought_process": "...", "execution_plan": []}}
【输出】"""


def _build_sql_prompt(query: str) -> str:
    """构建 SQL 生成 Prompt"""
    return f"""生成 SQL 查询：
【查询】{query}
【数据库】MySQL
【输出】SQL:"""
