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

### 3. MySQL 数据库配置

#### 3.1 安装 MySQL (Alibaba Cloud Linux)

```bash
# 安装 MySQL 8.0
sudo dnf install -y mysql-server mysql

# 启动 MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 验证状态
sudo systemctl status mysqld
```

#### 3.2 创建数据库和用户

```bash
# 登录 MySQL
sudo mysql -u root

# 执行 SQL 命令
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Root@123456';

CREATE DATABASE IF NOT EXISTS nl2sql DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'nl2sql'@'localhost' IDENTIFIED BY 'Nl2sql@123456';
GRANT ALL PRIVILEGES ON nl2sql.* TO 'nl2sql'@'localhost';
FLUSH PRIVILEGES;
SHOW DATABASES;
EXIT;
```

#### 3.3 配置数据库连接

编辑 `app/config/mysql.py`：

```python
class MySQLConfig:
    HOST = "localhost"
    PORT = 3306
    DATABASE = "nl2sql"        # ← 修改为你的数据库名
    USERNAME = "nl2sql"        # ← 修改为你的用户名
    PASSWORD = "Nl2sql@123456" # ← 修改为你的密码
```

#### 3.4 导入测试数据 (可选)

```bash
# 登录 MySQL 并导入测试表
mysql -u nl2sql -p nl2sql < your_schema.sql
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# Application
APP_NAME=NL2SQL Platform
APP_ENV=development

# Database
DATABASE_URL=mysql+aiomysql://nl2sql:Nl2sql@123456@localhost:3306/nl2sql
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379

# Vector Store
VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PERSIST_DIR=./faiss_index

# LLM
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your-dashscope-key
DASHSCOPE_MODEL=qwen-max

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

### 5. 导入 Schema 到向量库

**重要：** 在启动服务前，需要先导入数据库 Schema 到向量库，否则 NL2SQL 无法检索表结构。

#### 5.1 运行导入脚本

```bash
cd nl2sql-platform
python scripts/import_mysql_schema.py
```

**输出示例：**
```
============================================================
🗄️ MySQL Schema 导入工具
============================================================
📥 开始导入 Schema...
⚠️  将清除旧的索引数据，避免重复...
============================================================
✅ Schema 导入完成！
============================================================
  表数量：19
  列数量：168
============================================================
```

#### 5.2 验证导入结果

```bash
# 检查 FAISS 索引目录
ls -la faiss_index/

# 应该看到：
# - index.faiss
# - index.pkl
```

#### 5.3 Schema 导入说明

**导入流程：**
1. 连接 MySQL 数据库
2. 读取 `information_schema` 元数据
   - 表注释 (`information_schema.TABLES`)
   - 列信息 (`information_schema.COLUMNS`)
   - 主键/外键 (`information_schema.KEY_COLUMN_USAGE`)
3. 使用 FastEmbed (BAAI/bge-small-zh-v1.5) 向量化
4. 存储到 FAISS 向量库 (`./faiss_index/`)

**持久化机制：**
- Schema 向量持久化到 `./faiss_index/` 目录
- 服务重启后自动加载，无需重新导入
- 当数据库结构变更时，需要重新运行导入脚本

**注意事项：**
- ⚠️ 数据库结构变更后，必须重新导入 Schema
- ⚠️ 切换数据库后，必须重新导入 Schema
- ⚠️ 使用不同的 Embeddings 模型时，必须重新导入

### 6. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 后台运行 (使用 systemd 或 supervisor)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

### 7. 访问 API 文档

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

### 常用命令

```bash
# 查看 MySQL 服务状态
sudo systemctl status mysqld

# 登录 MySQL
mysql -u nl2sql -p nl2sql

# 重新导入 Schema
python scripts/import_mysql_schema.py

# 清空 FAISS 索引并重新导入
rm -rf faiss_index/ && python scripts/import_mysql_schema.py

# 查看导入的表数量
mysql -u nl2sql -p nl2sql -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='nl2sql';"
```

### 故障排查

#### 问题 1: Schema 检索失败

**症状：** API 返回 "未检索到相关数据表"

**解决方案：**
```bash
# 1. 检查 MySQL 是否运行
sudo systemctl status mysqld

# 2. 检查数据库配置
cat app/config/mysql.py

# 3. 重新导入 Schema
python scripts/import_mysql_schema.py

# 4. 检查 FAISS 索引
ls -la faiss_index/
```

#### 问题 2: FAISS 索引加载失败

**症状：** 服务启动时报错 "Failed to load FAISS index"

**解决方案：**
```bash
# 删除旧索引并重新导入
rm -rf faiss_index/
python scripts/import_mysql_schema.py
```

#### 问题 3: 中文检索效果差

**解决方案：**
- 确保使用中文 embeddings 模型：`BAAI/bge-small-zh-v1.5`
- 检查表/列注释是否包含中文描述
- 降低检索阈值：修改 `schema_recall_node.py` 中的 `threshold` 参数

## License

Apache 2.0
