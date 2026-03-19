"""
SQL 错误分类服务

参考 DataAgent 项目的错误分类设计，区分执行错误和语义错误
"""
import re
import structlog

logger = structlog.get_logger()


class SqlErrorType:
    """SQL 错误类型枚举"""
    EXECUTION_ERROR = "execution_error"  # 执行错误：语法错误、列名错误等
    SEMANTIC_ERROR = "semantic_error"    # 语义错误：结果不符合预期
    UNKNOWN = "unknown"                   # 未知错误


def classify_sql_error(error_message: str) -> str:
    """
    分类 SQL 错误类型
    
    参考 DataAgent 的错误分类逻辑
    
    Args:
        error_message: 错误信息
        
    Returns:
        str: 错误类型 (execution_error / semantic_error / unknown)
    """
    if not error_message:
        return SqlErrorType.UNKNOWN
    
    error_lower = error_message.lower()
    
    # ========== 执行错误特征 ==========
    # 语法错误
    execution_error_patterns = [
        # MySQL 语法错误
        r"you have an error in your sql syntax",
        r"syntax error",
        r"sql syntax",
        
        # 列名/表名错误
        r"unknown column",
        r"column not found",
        r"column doesn't exist",
        r"table doesn't exist",
        r"table not found",
        r"table .* doesn't exist",
        
        # 函数错误
        r"function .* does not exist",
        r"undefined function",
        
        # 类型错误
        r"data type mismatch",
        r"type mismatch",
        r"cannot cast",
        
        # 权限错误
        r"access denied",
        r"permission denied",
        r"privilege",
        
        # 约束错误
        r"foreign key constraint",
        r"primary key constraint",
        r"unique constraint",
        r"check constraint",
        r"not null constraint",
        
        # 其他执行错误
        r"division by zero",
        r"out of range",
        r"deadlock",
        r"lock wait timeout",
        r"connection lost",
    ]
    
    # ========== 语义错误特征 ==========
    semantic_error_patterns = [
        # 结果不符
        r"结果不符合预期",
        r"result mismatch",
        r"unexpected result",
        r"wrong result",
        r"incorrect result",
        
        # 数据缺失
        r"数据缺失",
        r"missing data",
        r"no data found",
        r"empty result",
        
        # 逻辑错误
        r"逻辑错误",
        r"logic error",
        r"incorrect logic",
        
        # 聚合错误
        r"聚合错误",
        r"aggregation error",
        r"wrong aggregation",
        
        # 连接错误
        r"连接错误",
        r"join error",
        r"incorrect join",
        
        # 排序分页
        r"排序错误",
        r"sorting error",
        r"wrong order",
        r"分页错误",
        r"pagination error",
        
        # 过滤条件
        r"过滤条件错误",
        r"filter error",
        r"wrong filter",
        r"where 条件错误",
        
        # 业务逻辑
        r"业务逻辑",
        r"business logic",
        r"语义不匹配",
        r"semantic mismatch",
    ]
    
    # 检查执行错误
    for pattern in execution_error_patterns:
        if re.search(pattern, error_lower):
            logger.debug(f"Classified as execution error: {pattern}")
            return SqlErrorType.EXECUTION_ERROR
    
    # 检查语义错误
    for pattern in semantic_error_patterns:
        if re.search(pattern, error_lower):
            logger.debug(f"Classified as semantic error: {pattern}")
            return SqlErrorType.SEMANTIC_ERROR
    
    # 默认：未知错误（按执行错误处理，更保守）
    logger.debug(f"Unknown error type, defaulting to execution error")
    return SqlErrorType.EXECUTION_ERROR


def is_execution_error(error_message: str) -> bool:
    """
    判断是否为执行错误
    
    Args:
        error_message: 错误信息
        
    Returns:
        bool: 是否为执行错误
    """
    return classify_sql_error(error_message) == SqlErrorType.EXECUTION_ERROR


def is_semantic_error(error_message: str) -> bool:
    """
    判断是否为语义错误
    
    Args:
        error_message: 错误信息
        
    Returns:
        bool: 是否为语义错误
    """
    return classify_sql_error(error_message) == SqlErrorType.SEMANTIC_ERROR


def get_error_type_description(error_type: str) -> str:
    """
    获取错误类型描述
    
    Args:
        error_type: 错误类型
        
    Returns:
        str: 错误描述
    """
    descriptions = {
        SqlErrorType.EXECUTION_ERROR: "执行错误：语法错误、列名错误、表名错误等",
        SqlErrorType.SEMANTIC_ERROR: "语义错误：结果不符合预期、逻辑错误等",
        SqlErrorType.UNKNOWN: "未知错误",
    }
    return descriptions.get(error_type, "未知错误")
