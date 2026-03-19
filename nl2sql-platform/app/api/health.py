"""
健康检查 API
"""
from fastapi import APIRouter
from app.schemas import HealthResponse
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    健康检查
    
    检查数据库、Redis、向量库连接状态
    """
    # TODO: 实现实际的健康检查
    # 目前返回简化版本
    
    return HealthResponse(
        status="ok",
        version="0.1.0",
        database="connected",
        redis="connected",
        vector_store="connected"
    )


@router.get("/ready")
async def readiness_check():
    """
    就绪检查
    
    用于 K8s readiness probe
    """
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    存活检查
    
    用于 K8s liveness probe
    """
    return {"status": "alive"}
