"""
FastAPI 应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time

from app.config import settings
from app.api import nl2sql, health
from app.db.session import engine, Base


# 配置结构化日志
import logging
import json

# 自定义 JSON 编码器，支持中文输出
class ChineseJSONRenderer:
    """JSON 渲染器，ensure_ascii=False 支持中文"""
    
    def __call__(self, logger, method_name, event_dict):
        return json.dumps(event_dict, ensure_ascii=False, default=str)


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        ChineseJSONRenderer() if not settings.is_development else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, settings.log_level.upper())
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting application...")
    
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")
    
    yield
    
    # 关闭时执行
    logger.info("Shutting down application...")
    await engine.dispose()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="企业级 NL2SQL 智能数据分析平台",
    version="0.1.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://47.254.121.85:5173",  # 远程访问
        "http://47.254.121.85:8080",  # 远程访问
        "*",  # 允许所有来源（开发环境）
        *settings.allowed_origins_list
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    logger.info(
        "request_processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.is_development else "An unexpected error occurred"
        }
    )


# 注册路由
app.include_router(nl2sql.router, prefix="/api/nl2sql", tags=["NL2SQL"])
app.include_router(health.router, prefix="/health", tags=["Health"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/docs")
async def get_docs():
    """重定向到 API 文档"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
