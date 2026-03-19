# NL2SQL Platform

企业级 NL2SQL 智能数据分析平台

## 快速开始

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+ / PostgreSQL 15+
- Redis 7+
- ChromaDB 0.5+

### 2. 安装依赖

```bash
cd nl2sql-platform
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

### 4. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

## 项目结构

```
nl2sql-platform/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic Schema
│   ├── workflows/           # LangGraph 工作流
│   │   ├── __init__.py
│   │   ├── state.py         # State 定义
│   │   ├── nodes/           # 节点实现
│   │   └── graph.py         # 图构建
│   ├── services/            # 业务服务
│   └── api/                 # API 路由
├── tests/
├── scripts/
├── requirements.txt
├── .env.example
└── docker-compose.yml
```

## API 接口

### 1. NL2SQL 查询

```bash
POST /api/nl2sql/query
Content-Type: application/json

{
    "query": "查询订单数量最多的用户",
    "agent_id": "1",
    "thread_id": "uuid-xxx"
}
```

### 2. 健康检查

```bash
GET /health
```

## 开发指南

### 添加新节点

1. 在 `app/workflows/nodes/` 创建节点文件
2. 在 `app/workflows/graph.py` 注册节点
3. 更新 State 定义

### 数据库迁移

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## License

Apache 2.0
