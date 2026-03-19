"""
12. SQLExecuteNode - SQL 执行节点

职责：
- 执行生成的 SQL
- 返回查询结果
- 保存对话历史（DataAgent 方式）
- 支持 MySQL/PostgreSQL

参考 DataAgent 实现：
- SqlExecuteNode.java - SQL 执行逻辑
- MultiTurnContextManager.java - finishTurn() 调用时机
"""
from app.workflows.state import NL2SQLState
from app.config.mysql import MySQLConfig
from app.services.context_manager import get_context_manager
import aiomysql
import structlog

logger = structlog.get_logger()


async def sql_execute_node(state: NL2SQLState) -> dict:
    """
    SQL 执行节点（参考 DataAgent SqlExecuteNode 实现）
    
    核心流程：
    1. 执行 SQL 查询
    2. 流式反馈执行进度
    3. 追加 SQL 信息到 pending（扩展 DataAgent 实现）
    4. 调用 finish_turn() 完成对话轮（DataAgent 方式）
    
    Args:
        state: 工作流状态
        
    Returns:
        dict: 包含 SQL 执行结果
    """
    sql = state.get("generated_sql", "")
    thread_id = state.get("thread_id", "")
    
    # 安全校验：SQL 不能为空
    if not sql:
        logger.error("No SQL to execute")
        return {
            "sql_result": {
                "success": False,
                "error": "没有可执行的 SQL"
            },
            "plan_current_step": state.get("plan_current_step", 1) + 1
        }
    
    logger.info("Executing SQL", sql=sql[:200])
    
    try:
        # ========== 流式反馈（参考 DataAgent 实现）==========
        # DataAgent: emitter.next(ChatResponseUtil.createResponse("开始执行 SQL..."))
        logger.info("开始执行 SQL...")
        
        # 执行 SQL
        result = await _execute_sql(sql)
        
        # 流式反馈：执行完成
        # DataAgent: emitter.next(ChatResponseUtil.createResponse("执行 SQL 完成"))
        logger.info("SQL 执行完成", row_count=result.get("row_count", 0))
        
        # ========== 保存对话历史（DataAgent 方式）==========
        # 参考 DataAgent MultiTurnContextManager.finishTurn() 调用时机
        context_manager = get_context_manager()
        
        # 追加 SQL 信息（我们的扩展实现，DataAgent 没有此方法）
        context_manager.append_sql_info(
            thread_id,
            sql_query=sql,
            sql_result=result
        )
        
        # 完成对话轮（原子提交，参考 DataAgent finishTurn）
        context_manager.finish_turn(thread_id)
        logger.debug("Turn finished and saved", thread_id=thread_id)
        
        # 更新计划步骤
        plan_current_step = state.get("plan_current_step", 1) + 1
        
        return {
            "sql_result": result,
            "plan_current_step": plan_current_step
        }
        
    except Exception as e:
        logger.error("Failed to execute SQL", error=str(e))
        
        # SQL 执行失败时，调用 discard_pending() 丢弃 pending 数据
        # 参考 DataAgent: discardPending() - 用于 run aborted 时清理
        context_manager = get_context_manager()
        context_manager.discard_pending(thread_id)
        logger.debug("Pending discarded due to SQL execution failure", thread_id=thread_id)
        
        return {
            "sql_result": {
                "success": False,
                "error": str(e),
                "data": [],
                "columns": [],
                "row_count": 0
            },
            "plan_current_step": state.get("plan_current_step", 1) + 1,
            "sql_regenerate_reason": f"SQL 执行失败：{str(e)}"
        }


async def _execute_sql(sql: str, limit: int = 1000) -> dict:
    """
    执行 SQL - 真实 MySQL 数据库连接
    
    参考 DataAgent 实现：
    - DatabaseUtil.getAgentAccessor() - 获取数据库访问器
    - Accessor.executeSqlAndReturnObject() - 执行 SQL 并返回结果
    
    Args:
        sql: SQL 语句
        limit: 最大返回行数
        
    Returns:
        dict: 执行结果
    """
    # ========== 安全校验（参考 DataAgent 安全机制）==========
    sql_upper = sql.strip().upper()
    
    # 只允许 SELECT 查询
    if not sql_upper.startswith("SELECT"):
        logger.warning("Non-SELECT SQL blocked", sql=sql[:100])
        return {
            "success": False,
            "error": "只允许 SELECT 查询，禁止执行写操作",
            "data": [],
            "columns": [],
            "row_count": 0
        }
    
    # 禁止危险关键字
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE", "REPLACE"]
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            logger.warning("Dangerous SQL keyword detected", keyword=keyword, sql=sql[:100])
            return {
                "success": False,
                "error": f"检测到危险操作：{keyword}",
                "data": [],
                "columns": [],
                "row_count": 0
            }
    
    # ========== 执行 SQL 查询 ==========
    logger.info("Executing SQL on MySQL", sql=sql[:200], limit=limit)
    
    try:
        # 连接 MySQL 数据库（参考 DataAgent: databaseUtil.getAgentAccessor）
        connection = await aiomysql.connect(
            host=MySQLConfig.HOST,
            port=MySQLConfig.PORT,
            user=MySQLConfig.USERNAME,
            password=MySQLConfig.PASSWORD,
            db=MySQLConfig.DATABASE,
            charset='utf8mb4',
            cursorclass=aiomysql.cursors.DictCursor
        )
        
        try:
            async with connection.cursor() as cursor:
                # 执行 SQL（参考 DataAgent: accessor.executeSqlAndReturnObject）
                await cursor.execute(sql)
                
                # 获取列名
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # 获取数据（限制返回行数）
                rows = await cursor.fetchmany(limit)
                
                # 转换为字典列表
                data = [dict(row) for row in rows]
                
                row_count = len(data)
                
                logger.info("SQL executed successfully", row_count=row_count)
                
                return {
                    "success": True,
                    "columns": columns,
                    "data": data,
                    "row_count": row_count
                }
                
        finally:
            connection.close()
            
    except aiomysql.OperationalError as e:
        # 数据库操作错误（参考 DataAgent 错误处理）
        logger.error("MySQL operational error", error=str(e), sql=sql[:200])
        return {
            "success": False,
            "error": f"数据库错误：{str(e)}",
            "data": [],
            "columns": [],
            "row_count": 0
        }
    except Exception as e:
        # 其他错误
        logger.error("SQL execution failed", error=str(e), sql=sql[:200])
        return {
            "success": False,
            "error": f"执行失败：{str(e)}",
            "data": [],
            "columns": [],
            "row_count": 0
        }
