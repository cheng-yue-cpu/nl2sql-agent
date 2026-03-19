# NL2SQL Agent

企业级 NL2SQL 智能数据分析平台 - 自然语言转 SQL

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## 📖 项目简介

**NL2SQL (Natural Language to SQL)** 是一个基于 AI 的智能数据分析平台，用户可以使用自然语言查询数据库，系统自动理解意图、生成 SQL 并返回结果。

### 核心特性

- 🗣️ **自然语言查询** - 用中文提问，自动转换为 SQL
- 🔄 **多轮对话** - 支持上下文追问（"平均年龄呢？"）
- 🧠 **智能 Schema 检索** - 基于向量检索的表结构召回
- 🔗 **表关系分析** - 自动分析外键和 JOIN 路径
- ✅ **语义一致性校验** - 确保生成的 SQL 与意图一致
- 📊 **结果可视化** - 表格展示查询结果

### 示例

```
用户："统计用户总数"
→ AI: SELECT COUNT(*) FROM users;
→ 结果：5

用户："平均年龄呢？"
→ AI: SELECT AVG(age) FROM users;
→ 结果：25
```

---

## 🏗️ 项目架构

```
nl2sql-agent/
├── nl2sql-platform/          # 后端 (FastAPI + LangGraph)
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config/           # 配置管理
│   │   ├── workflows/        # LangGraph 工作流 ⭐
│   │   │   ├── graph.py      # 工作流图 (10 节点)
│   │   │   ├── state.py      # State 定义
│   │   │   └── nodes/        # 节点实现
│   │   ├── services/         # 业务服务
│   │   │   └── schema_service.py  # Schema 检索服务
│   │   └── api/              # API 路由
│   ├── scripts/
│   │   └── import_mysql_schema.py  # Schema 导入脚本 ⭐
│   ├── faiss_index/          # FAISS 向量库 (持久化)
│   └── requirements.txt
│
├── nl2sql-frontend/          # 前端 (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── components/       # Vue 组件
│   │   ├── stores/           # Pinia 状态管理
│   │   └── api/              # API 调用
│   ├── package.json
│   └── vite.config.ts
│
└── README.md                 # 本文件
```

---

## 🔥 技术栈

### 后端 (nl2sql-platform)

| 技术 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | 0.104+ | Web 框架 |
| **LangChain** | 0.3+ | AI 应用框架 |
| **LangGraph** | 0.2+ | 工作流编排 |
| **SQLAlchemy** | 2.0+ | ORM |
| **PyMySQL** | - | MySQL 驱动 |
| **FAISS** | - | 向量检索 |
| **FastEmbed** | - | Embeddings (中文) |
| **Structlog** | 23.0+ | 结构化日志 |

### 前端 (nl2sql-frontend)

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.4+ | 前端框架 |
| **Vite** | 5.0+ | 构建工具 |
| **Element Plus** | 2.4+ | UI 组件库 |
| **Pinia** | - | 状态管理 |
| **Axios** | - | HTTP 客户端 |
| **TypeScript** | 5.3+ | 类型系统 |

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+ / PostgreSQL 15+
- Node.js 18+
- Redis 7+ (可选)

### 2. 安装 MySQL

```bash
# Alibaba Cloud Linux
sudo dnf install -y mysql-server mysql

# 启动 MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### 3. 创建数据库

```bash
# 登录 MySQL
sudo mysql -u root

# 执行 SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Root@123456';

CREATE DATABASE IF NOT EXISTS nl2sql 
  DEFAULT CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'nl2sql'@'localhost' 
  IDENTIFIED BY 'Nl2sql@123456';

GRANT ALL PRIVILEGES ON nl2sql.* TO 'nl2sql'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 4. 配置后端

```bash
cd nl2sql-platform

# 安装依赖
pip install -r requirements.txt

# 配置数据库连接
# 编辑 app/config/mysql.py
```

```python
# app/config/mysql.py
class MySQLConfig:
    HOST = "localhost"
    PORT = 3306
    DATABASE = "nl2sql"        # ← 你的数据库名
    USERNAME = "nl2sql"        # ← 你的用户名
    PASSWORD = "Nl2sql@123456" # ← 你的密码
```

### 5. 导入 Schema 到向量库 ⭐

**重要：** 启动服务前必须导入 Schema，否则无法检索表结构。

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
✅ Schema 导入完成！
============================================================
  表数量：19
  列数量：168
============================================================
```

**导入说明：**
- 从 MySQL `information_schema` 读取元数据
- 使用 FastEmbed (BAAI/bge-small-zh-v1.5) 向量化
- 持久化到 `./faiss_index/` 目录
- 服务重启后自动加载

**何时需要重新导入：**
- ⚠️ 数据库结构变更后
- ⚠️ 切换数据库后
- ⚠️ 使用不同的 Embeddings 模型时

### 6. 启动后端

```bash
cd nl2sql-platform

# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

访问 API 文档：http://localhost:8000/docs

### 7. 启动前端

```bash
cd nl2sql-frontend

# 安装依赖
npm install

# 开发模式
npm run dev
```

访问前端：http://localhost:5173

---

## 🧠 LangGraph 工作流

NL2SQL 使用 LangGraph 编排 10 节点工作流：

```
┌─────────────────────────┐
│ 1. IntentRecognition    │ ← 意图识别
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 2. QueryEnhance         │ ← 查询重写 (多轮对话)
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 3. SchemaRecall         │ ← Schema 检索 (RAG) ⭐
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 4. TableRelation        │ ← 表关系分析 ⭐
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 5. FeasibilityAssess    │ ← 可行性评估
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 6. Planner              │ ← 任务规划
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 7. PlanExecutor         │ ← 计划执行调度
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 8. SQLGenerate          │ ← SQL 生成
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 9. SemanticConsistency  │ ← 语义一致性校验
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│ 10.SQLExecute           │ ← SQL 执行
└─────────────────────────┘
```

### 核心节点说明

| 节点 | 功能 | 关键文件 |
|------|------|----------|
| **SchemaRecall** | 向量检索相关表结构 | `app/workflows/nodes/schema_recall_node.py` |
| **TableRelation** | 分析外键和 JOIN 路径 | `app/workflows/nodes/table_relation_node.py` |
| **SQLGenerate** | 根据 Schema 生成 SQL | `app/workflows/nodes/sql_generate_node.py` |
| **SemanticConsistency** | 校验 SQL 与意图一致性 | `app/workflows/nodes/semantic_consistency_node.py` |

---

## 📐 Schema 构建详解

### 元数据来源

从 MySQL `information_schema` 读取：

| 信息类型 | 来源表 |
|----------|--------|
| 表注释 | `information_schema.TABLES` |
| 列信息 | `information_schema.COLUMNS` |
| 主键 | `information_schema.KEY_COLUMN_USAGE` |
| 外键 | `information_schema.KEY_COLUMN_USAGE` |

### 向量化处理

```python
from fastembed import TextEmbedding

# 中文专用 embeddings 模型
embeddings = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
```

### Document 格式

**表 Document：**
```json
{
  "page_content": "表名：users\n描述：用户信息表\n主键：id\n外键：users.dept_id=departments.id",
  "metadata": {
    "vector_type": "table",
    "name": "users",
    "description": "用户信息表",
    "foreign_key": "users.dept_id=departments.id"
  }
}
```

**列 Document：**
```json
{
  "page_content": "列名：id\n表名：users\n类型：INT\n描述：用户 ID",
  "metadata": {
    "vector_type": "column",
    "table_name": "users",
    "name": "id",
    "type": "INT"
  }
}
```

### 持久化存储

```
faiss_index/
├── index.faiss    # FAISS 索引
└── index.pkl      # 元数据
```

---

## 🔌 API 接口

### NL2SQL 查询

```bash
POST /api/nl2sql/query
Content-Type: application/json

{
    "query": "统计用户总数",
    "agent_id": "1",
    "thread_id": "uuid-xxx"
}
```

**响应：**
```json
{
    "sql": "SELECT COUNT(*) FROM users;",
    "result": [{"COUNT(*)": 5}],
    "messages": [...]
}
```

### 健康检查

```bash
GET /health
```

---

## 📁 子项目文档

- **后端详情:** [nl2sql-platform/README.md](nl2sql-platform/README.md)
- **前端详情:** [nl2sql-frontend/README.md](nl2sql-frontend/README.md)

---

## 🛠️ 常用命令

```bash
# 查看 MySQL 状态
sudo systemctl status mysqld

# 登录 MySQL
mysql -u nl2sql -p nl2sql

# 重新导入 Schema
cd nl2sql-platform && python scripts/import_mysql_schema.py

# 清空 FAISS 索引并重新导入
rm -rf faiss_index/ && python scripts/import_mysql_schema.py

# 查看导入的表数量
mysql -u nl2sql -p nl2sql -e "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='nl2sql';"
```

---

## 🐛 故障排查

### 问题 1: Schema 检索失败

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

### 问题 2: FAISS 索引加载失败

**症状：** 服务启动时报错 "Failed to load FAISS index"

**解决方案：**
```bash
rm -rf faiss_index/
python scripts/import_mysql_schema.py
```

### 问题 3: 中文检索效果差

**解决方案：**
- 确保使用中文 embeddings 模型：`BAAI/bge-small-zh-v1.5`
- 检查表/列注释是否包含中文描述
- 降低检索阈值：修改 `schema_recall_node.py` 中的 `threshold` 参数

---

## 📚 技术报告

项目包含详细的技术报告：

- `MULTI_TURN_IMPLEMENTATION_REPORT.md` - 多轮对话实现
- `SCHEMA_IMPORT_REPORT.md` - Schema 导入详解
- `FAISS_IMPLEMENTATION_REPORT.md` - FAISS 向量库实现
- `E2E_TEST_REPORT.md` - 端到端测试报告

---

## 📄 License

Apache 2.0

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

**最后更新**: 2026-03-19
