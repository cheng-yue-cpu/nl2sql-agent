"""
MySQL 数据库连接配置
"""
from app.config import settings
import structlog

logger = structlog.get_logger()


class MySQLConfig:
    """MySQL 数据库配置"""
    
    # 数据库连接信息
    HOST = "localhost"
    PORT = 3306
    DATABASE = "mydb"
    USERNAME = "root"
    PASSWORD = "Cheng123."
    
    @classmethod
    def get_connection_string(cls) -> str:
        """获取 SQLAlchemy 连接字符串"""
        return f"mysql+aiomysql://{cls.USERNAME}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
    
    @classmethod
    def get_sync_connection_string(cls) -> str:
        """获取同步连接字符串（用于 Schema 导入）"""
        return f"mysql+pymysql://{cls.USERNAME}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """获取连接参数字典"""
        return {
            "host": cls.HOST,
            "port": cls.PORT,
            "user": cls.USERNAME,
            "password": cls.PASSWORD,
            "database": cls.DATABASE,
            "charset": "utf8mb4"
        }


# 更新应用配置中的数据库 URL
if hasattr(settings, 'database_url'):
    settings.database_url = MySQLConfig.get_connection_string()

logger.info("MySQL config loaded", database=MySQLConfig.DATABASE, host=MySQLConfig.HOST)
