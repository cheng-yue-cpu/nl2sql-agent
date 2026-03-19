# NL2SQL 前端

NL2SQL 平台的 Vue 3 前端界面

## 🚀 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问：http://localhost:5173

### 生产构建

```bash
npm run build
```

输出目录：`dist/`

### 预览生产构建

```bash
npm run preview
```

## 📦 技术栈

- **框架**: Vue 3.4+ (组合式 API)
- **构建工具**: Vite 5.0+
- **UI 组件库**: Element Plus 2.4+
- **状态管理**: Pinia
- **HTTP 客户端**: Axios
- **代码高亮**: Highlight.js
- **语言**: TypeScript 5.3+

## 🎯 功能特性

### 已实现

- ✅ 上下文对话框 - 支持多轮对话
- ✅ 新建对话 - 创建新会话
- ✅ 会话列表 - 显示/切换历史会话
- ✅ SQL 语法高亮显示
- ✅ 查询结果表格展示
- ✅ 加载状态动画
- ✅ 错误提示
- ✅ 响应式布局

### 数据持久化

当前使用 **localStorage** 进行本地存储：
- 会话列表
- 消息历史

### 后端 API

连接 NL2SQL 平台后端：
- 地址：http://localhost:8000
- API: `/api/nl2sql/query`

## 📁 项目结构

```
nl2sql-frontend/
├── src/
│   ├── main.ts              # 入口文件
│   ├── App.vue              # 根组件
│   ├── components/
│   │   ├── ChatDialog.vue   # 主对话框
│   │   ├── SessionList.vue  # 会话列表
│   │   ├── MessageList.vue  # 消息列表
│   │   ├── MessageInput.vue # 输入框
│   │   ├── SqlDisplay.vue   # SQL 展示
│   │   └── ResultTable.vue  # 结果表格
│   ├── stores/
│   │   └── chat.ts          # 聊天状态管理
│   ├── api/
│   │   └── nl2sql.ts        # API 调用
│   ├── types/
│   │   └── index.ts         # 类型定义
│   └── styles/
│       └── main.css         # 全局样式
├── index.html
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## 🎨 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  📊 NL2SQL Platform                      [+ 新建对话]   │
├────────────┬────────────────────────────────────────────┤
│            │                                            │
│ 会话列表   │  上下文对话框                              │
│ (280px)    │                                            │
│            │  ┌──────────────────────────────────────┐ │
│ - 会话 1    │  │ 🤖 AI: 你好！有什么可以帮你？        │ │
│ - 会话 2    │  └──────────────────────────────────────┘ │
│ [当前]     │                                            │
│            │  ┌──────────────────────────────────────┐ │
│ - 会话 3    │  │ 👤 用户：统计用户总数                │ │
│            │  └──────────────────────────────────────┘ │
│            │                                            │
│            │  ┌──────────────────────────────────────┐ │
│            │  │ 🤖 AI: SELECT COUNT(*) FROM users;   │ │
│            │  │ 📊 结果：5 条                         │ │
│            │  └──────────────────────────────────────┘ │
│            │                                            │
│            │  ┌──────────────────────────────────────┐ │
│            │  │ 👤 用户：平均年龄呢？                │ │
│            │  └──────────────────────────────────────┘ │
│            │                                            │
│            │  ┌──────────────────────────────────────┐ │
│            │  │ 🤖 AI: SELECT AVG(age) FROM users;   │ │
│            │  │ 📊 结果：25 岁                        │ │
│            │  └──────────────────────────────────────┘ │
│            │                                            │
│            │  ┌────────────────────────────────────┐   │
│            │  │ 输入查询...                 [发送] │   │
│            │  └────────────────────────────────────┘   │
├────────────┴────────────────────────────────────────────┤
│  🟢 运行中 | Agent ID: 1                                 │
└─────────────────────────────────────────────────────────┘
```

## 🔧 配置

### 后端 API 地址

编辑 `src/api/nl2sql.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000/api';
```

### Agent ID

默认 Agent ID 为 1，可在 `src/stores/chat.ts` 中修改：

```typescript
const agentId = ref<number>(1);
```

## 📝 使用说明

### 1. 启动后端

确保 NL2SQL 后端服务运行在 `http://localhost:8000`

```bash
cd /home/admin/.openclaw/workspace/nl2sql-platform
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动前端

```bash
cd /home/admin/.openclaw/workspace/nl2sql-frontend
npm run dev
```

### 3. 开始对话

1. 点击"新建对话"创建新会话
2. 在输入框中输入查询，例如：
   - "统计用户总数"
   - "查询订单数量"
   - "平均年龄呢？" (多轮对话)
3. 按 Enter 或点击"发送"按钮
4. 查看生成的 SQL 和查询结果

## 🧪 测试

### 多轮对话测试

```
第一轮：统计用户总数
  → AI: SELECT COUNT(*) FROM users; 结果：5

第二轮：平均年龄呢？
  → AI: SELECT AVG(age) FROM users; 结果：25

第三轮：最大的呢？
  → AI: SELECT MAX(age) FROM users; 结果：30
```

## 📄 License

Apache 2.0
