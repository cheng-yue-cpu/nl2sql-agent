"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base


class Agent(Base):
    """智能体模型"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="智能体名称")
    description = Column(Text, comment="描述")
    status = Column(String(50), default="draft", comment="状态：draft-待发布，published-已发布")
    
    # 关系
    datasources = relationship("Datasource", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Datasource(Base):
    """数据源模型"""
    __tablename__ = "datasources"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False, comment="数据源名称")
    dialect = Column(String(50), nullable=False, comment="数据库类型：mysql, postgresql")
    host = Column(String(255), nullable=False, comment="主机地址")
    port = Column(Integer, nullable=False, comment="端口")
    database = Column(String(255), nullable=False, comment="数据库名")
    username = Column(String(255), nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 关系
    agent = relationship("Agent", back_populates="datasources")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Conversation(Base):
    """对话会话模型"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, comment="会话 ID (UUID)")
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    title = Column(String(255), default="新会话", comment="会话标题")
    
    # 关系
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Message(Base):
    """对话消息模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False, comment="角色：user, assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(String(50), default="text", comment="类型：text, sql, result")
    metadata = Column(JSON, default=dict, comment="元数据")
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BusinessKnowledge(Base):
    """业务知识模型"""
    __tablename__ = "business_knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    business_term = Column(String(255), nullable=False, comment="业务名词")
    description = Column(Text, comment="描述")
    synonyms = Column(Text, comment="同义词，逗号分隔")
    is_recall = Column(Boolean, default=True, comment="是否参与召回")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
