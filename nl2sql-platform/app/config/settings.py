"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "NL2SQL Platform"
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    
    # 数据库配置
    database_url: str = "postgresql://user:password@localhost:5432/nl2sql"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    
    # 向量库配置
    vector_store_type: str = "chroma"
    vector_store_url: str = "http://localhost:8001"
    vector_store_persist_dir: str = "./chroma_db"
    
    # LLM 配置
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    
    dashscope_api_key: Optional[str] = None
    dashscope_model: str = "qwen-max"
    
    # ZhipuAI (GLM) 配置
    zhipuai_api_key: Optional[str] = None
    zhipuai_model: str = "glm-4"
    
    # CORS 配置
    allowed_origins: str = "http://localhost:3000"
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """解析允许的源列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
