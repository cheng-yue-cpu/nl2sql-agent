"""
Pydantic Schema 定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== NL2SQL 请求/响应 ==========

class NL2SQLRequest(BaseModel):
    """NL2SQL 查询请求"""
    query: str = Field(..., description="用户自然语言查询", min_length=1, max_length=2000)
    agent_id: str = Field(..., description="智能体 ID")
    thread_id: Optional[str] = Field(None, description="会话 ID（可选，为空则创建新会话）")
    human_feedback: bool = Field(False, description="是否启用人工反馈")


class NL2SQLResponse(BaseModel):
    """NL2SQL 查询响应"""
    thread_id: str = Field(..., description="会话 ID")
    query: str = Field(..., description="用户查询")
    canonical_query: Optional[str] = Field(None, description="重写后的查询")
    generated_sql: Optional[str] = Field(None, description="生成的 SQL")
    sql_result: Optional[Dict[str, Any]] = Field(None, description="SQL 执行结果")
    error: Optional[str] = Field(None, description="错误信息")


class NL2SQLStreamResponse(BaseModel):
    """NL2SQL 流式响应"""
    thread_id: str
    node_name: str
    text_type: str = "TEXT"
    text: str
    error: bool = False
    complete: bool = False


# ========== 健康检查 ==========

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"
    redis: str = "connected"
    vector_store: str = "connected"


# ========== 数据源 ==========

class DatasourceCreate(BaseModel):
    """创建数据源请求"""
    name: str = Field(..., description="数据源名称")
    dialect: str = Field(..., description="数据库类型", pattern="^(mysql|postgresql)$")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口", ge=1, le=65535)
    database: str = Field(..., description="数据库名")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class DatasourceResponse(BaseModel):
    """数据源响应"""
    id: int
    agent_id: int
    name: str
    dialect: str
    host: str
    port: int
    database: str
    username: str
    is_active: bool
    
    class Config:
        from_attributes = True


# ========== 会话 ==========

class ConversationCreate(BaseModel):
    """创建会话请求"""
    agent_id: int
    title: Optional[str] = "新会话"


class ConversationResponse(BaseModel):
    """会话响应"""
    id: str
    agent_id: int
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """创建消息请求"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    conversation_id: str
    role: str
    content: str
    message_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== 业务知识 ==========

class BusinessKnowledgeCreate(BaseModel):
    """创建业务知识请求"""
    agent_id: int
    business_term: str = Field(..., description="业务名词", max_length=255)
    description: Optional[str] = Field(None, description="描述")
    synonyms: Optional[str] = Field(None, description="同义词，逗号分隔")
    is_recall: bool = True


class BusinessKnowledgeResponse(BaseModel):
    """业务知识响应"""
    id: int
    agent_id: int
    business_term: str
    description: Optional[str]
    synonyms: Optional[str]
    is_recall: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
