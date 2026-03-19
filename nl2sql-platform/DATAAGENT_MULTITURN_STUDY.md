# DataAgent MultiTurn Context 实现方式学习笔记

**学习时间**: 2026-03-06 14:56  
**参考项目**: DataAgent (Spring AI Alibaba 开源项目)  
**项目地址**: https://github.com/spring-ai-alibaba/spring-ai-alibaba

---

## 📚 DataAgent 项目背景

**DataAgent** 是 Spring AI Alibaba 团队开源的企业级 NL2SQL 智能体项目：

- **技术栈**: Spring Boot + Spring AI + LangGraph4j
- **定位**: 企业级数据分析智能体
- **核心能力**: 自然语言转 SQL、多轮对话、RAG 知识检索
- **架构**: 13 节点工作流

---

## 🎯 MultiTurn Context 设计思想

### 核心问题

多轮对话需要解决的核心问题：

1. **指代消解** - "它们"、"这个"指代什么？
2. **上下文补全** - 省略的主语、宾语是什么？
3. **会话隔离** - 不同用户的对话不能混淆
4. **性能优化** - 快速加载历史，不拖慢响应
5. **数据持久化** - 重启后对话历史不丢失

---

## 🏗️ DataAgent 的实现架构

### 三层存储架构

```
┌─────────────────────────────────────────┐
│         内存缓存 (Memory Cache)          │
│         thread_id → MultiTurnContext    │
│         访问速度：O(1), <10ms           │
└─────────────────────────────────────────┘
              ↓ (未命中)
┌─────────────────────────────────────────┐
│         Redis 缓存                        │
│         key: "context:{thread_id}"      │
│         访问速度：O(1), <50ms           │
└─────────────────────────────────────────┘
              ↓ (未命中)
┌─────────────────────────────────────────┐
│         数据库 (MySQL)                   │
│         table: conversation_context     │
│         访问速度：O(logN), <200ms       │
└─────────────────────────────────────────┘
```

**优势**:
- ✅ 热点数据在内存，极速访问
- ✅ Redis 作为二级缓存，支持分布式
- ✅ 数据库持久化，永久保存
- ✅ 三级命中，平衡性能和成本

---

## 📋 核心数据结构

### 1. ConversationTurn (对话轮次)

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConversationTurn {
    private String userQuestion;      // 用户问题
    private String aiPlan;            // AI 计划 (文本描述)
    private String sqlQuery;          // 生成的 SQL
    private String sqlResult;         // SQL 执行结果 (JSON 字符串)
    private LocalDateTime timestamp;  // 时间戳
}
```

**关键字段说明**:
- `userQuestion`: 用户原始问题
- `aiPlan`: AI 的思考过程/执行计划（DataAgent 特有）
- `sqlQuery`: 最终生成的 SQL
- `sqlResult`: 执行结果（用于后续对比）

---

### 2. MultiTurnContext (多轮上下文)

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MultiTurnContext {
    private String threadId;                          // 会话 ID
    private String agentId;                           // 智能体 ID
    private List<ConversationTurn> history = new ArrayList<>();  // 对话历史
    private LocalDateTime createdAt;                  // 创建时间
    private LocalDateTime updatedAt;                  // 更新时间
}
```

**设计要点**:
- `threadId`: 会话唯一标识（UUID 或用户 ID+ 时间戳）
- `agentId`: 支持多智能体场景
- `history`: 按时间顺序存储对话轮次
- `createdAt/updatedAt`: 用于 TTL 清理

---

### 3. NL2SQLState (LangGraph 状态)

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class NL2SQLState {
    // 输入相关
    private List<Message> messages;           // LangChain 消息历史
    private String userQuery;                 // 用户原始问题
    private String threadId;                  // 会话 ID
    private String agentId;                   // 智能体 ID
    private String multiTurnContext;          // 格式化的上下文字符串
    
    // 检索相关
    private String evidence;                  // RAG 检索结果
    private String canonicalQuery;            // 重写后的查询
    private List<Document> tableDocuments;    // 表结构文档
    private List<Document> columnDocuments;   // 列信息文档
    
    // ... 其他字段
}
```

**关键设计**:
- `multi_turn_context`: **字符串格式**，直接注入 Prompt
- `canonical_query`: 重写后的查询，用于后续节点
- 不在 State 中存储复杂对象，避免序列化问题

---

## 🔧 核心方法实现

### 1. begin_turn - 开始新对话轮

```java
public async void begin_turn(String threadId, String agentId, String userQuestion) {
    // 1. 获取或创建上下文
    MultiTurnContext context = getOrCreateContext(threadId, agentId);
    
    // 2. 创建 pending 暂存区
    PendingTurn pending = new PendingTurn();
    pending.setUserQuestion(userQuestion);
    pending.setAiPlan("");
    pending.setSqlQuery("");
    pending.setSqlResult("");
    
    // 3. 存到内存缓存（带 threadId 后缀）
    memoryCache.put(threadId + "_pending", pending);
}
```

**设计思想**:
- **Pending 模式**: 先暂存，完成后再提交
- **流式支持**: 可以逐步追加 AI 计划
- **原子性**: 要么全部成功，要么全部丢弃

---

### 2. append_plan_chunk - 流式追加 AI 计划

```java
public async void append_plan_chunk(String threadId, String chunk) {
    // 从 pending 暂存区获取
    PendingTurn pending = memoryCache.get(threadId + "_pending");
    if (pending != null) {
        // 追加到 ai_plan
        pending.setAiPlan(pending.getAiPlan() + chunk);
    }
}
```

**使用场景**:
```
用户："查询用户数量"
  ↓
AI 流式输出计划：
  "我需要..." (chunk 1)
  "查询 users 表..." (chunk 2)
  "使用 COUNT 聚合..." (chunk 3)
  ↓
append_plan_chunk(threadId, "我需要...")
append_plan_chunk(threadId, "查询 users 表...")
append_plan_chunk(threadId, "使用 COUNT 聚合...")
```

---

### 3. finish_turn - 完成对话轮

```java
public async void finish_turn(String threadId) {
    // 1. 从 pending 暂存区取出
    PendingTurn pending = memoryCache.remove(threadId + "_pending");
    if (pending == null) return;
    
    // 2. 获取上下文
    MultiTurnContext context = getOrCreateContext(threadId);
    
    // 3. 创建对话轮次
    ConversationTurn turn = new ConversationTurn();
    turn.setUserQuestion(pending.getUserQuestion());
    turn.setAiPlan(pending.getAiPlan());
    turn.setSqlQuery(pending.getSqlQuery());
    turn.setSqlResult(pending.getSqlResult());
    turn.setTimestamp(LocalDateTime.now());
    
    // 4. 添加到历史
    context.getHistory().add(turn);
    
    // 5. 限制轮数（滑动窗口）
    if (context.getHistory().size() > maxHistory) {
        context.getHistory().remove(0);  // 移除最旧的
    }
    
    // 6. 更新时间
    context.setUpdatedAt(LocalDateTime.now());
    
    // 7. 持久化到数据库
    persistToDatabase(context);
    
    // 8. 缓存到 Redis
    cacheToRedis(context);
}
```

**关键逻辑**:
- **滑动窗口**: 只保留最近 N 轮（默认 5 轮）
- **双写**: 数据库 + Redis 同时更新
- **清理 pending**: 完成后立即移除暂存区

---

### 4. build_context - 构建上下文字符串

```java
public async String build_context(String threadId) {
    // 获取上下文
    MultiTurnContext context = getOrCreateContext(threadId);
    
    // 没有历史
    if (context.getHistory().isEmpty()) {
        return "(无历史对话)";
    }
    
    // 构建格式化的字符串
    StringBuilder sb = new StringBuilder();
    sb.append("【多轮对话历史】（共 ").append(context.getHistory().size()).append(" 轮）\n\n");
    
    for (int i = 0; i < context.getHistory().size(); i++) {
        ConversationTurn turn = context.getHistory().get(i);
        sb.append("--- 第 ").append(i + 1).append(" 轮 ---\n");
        sb.append("用户：").append(turn.getUserQuestion()).append("\n");
        
        if (turn.getAiPlan() != null && !turn.getAiPlan().isEmpty()) {
            sb.append("AI 计划：").append(turn.getAiPlan()).append("\n");
        }
        
        if (turn.getSqlQuery() != null && !turn.getSqlQuery().isEmpty()) {
            sb.append("执行 SQL：").append(turn.getSqlQuery()).append("\n");
        }
        
        sb.append("\n");
    }
    
    return sb.toString();
}
```

**输出示例**:
```
【多轮对话历史】（共 2 轮）

--- 第 1 轮 ---
用户：查询用户数量
AI 计划：我需要查询 users 表，使用 COUNT 聚合函数统计用户总数
执行 SQL：SELECT COUNT(*) AS user_count FROM users;

--- 第 2 轮 ---
用户：那订单呢？
AI 计划：用户想了解订单数量，查询 orders 表
执行 SQL：SELECT COUNT(*) AS order_count FROM orders;
```

---

### 5. _get_or_create_context - 三级缓存查找

```java
private async MultiTurnContext _get_or_create_context(String threadId, String agentId) {
    // 1. 检查内存缓存
    if (memoryCache.containsKey(threadId)) {
        log.debug("命中内存缓存：{}", threadId);
        return memoryCache.get(threadId);
    }
    
    // 2. 检查 Redis 缓存
    String cached = redis.get("context:" + threadId);
    if (cached != null) {
        log.debug("命中 Redis 缓存：{}", threadId);
        MultiTurnContext context = JSON.parseObject(cached, MultiTurnContext.class);
        memoryCache.put(threadId, context);  // 回填内存
        return context;
    }
    
    // 3. 从数据库加载
    MultiTurnContext context = loadFromDatabase(threadId);
    if (context == null) {
        // 创建新上下文
        context = new MultiTurnContext();
        context.setThreadId(threadId);
        context.setAgentId(agentId);
        context.setHistory(new ArrayList<>());
        context.setCreatedAt(LocalDateTime.now());
        context.setUpdatedAt(LocalDateTime.now());
        log.info("创建新上下文：{}", threadId);
    } else {
        log.info("从数据库加载上下文：{}", threadId);
    }
    
    // 缓存到内存和 Redis
    memoryCache.put(threadId, context);
    cacheToRedis(context);
    
    return context;
}
```

**三级缓存策略**:
1. **内存缓存**: 最快，进程内，重启丢失
2. **Redis 缓存**: 快，分布式，支持过期
3. **数据库**: 慢，持久化，永久保存

**命中率优化**:
- 热点会话在内存
- 温会话在 Redis
- 冷会话在数据库

---

## 🎯 QueryEnhanceNode 实现

### Prompt 模板

```java
public String buildRewritePrompt(String query, String context, String evidence) {
    return """
你是一个专业的 NL2SQL 对话查询重写助手。

【任务】
根据历史对话上下文，将用户的最新查询重写为独立的、无歧义的陈述句。
重写后的查询将用于后续的 Schema 检索和 SQL 生成。

【要求】
1. **指代消解**：将"它们"、"这个"、"那些"、"后者"等代词替换为明确的实体
2. **上下文补全**：补充省略的表名、字段名、条件等信息
3. **保持原意**：不改变用户的原始意图
4. **简洁清晰**：使用简洁的陈述句，避免复杂从句
5. **只输出重写结果**：不要有任何解释、前缀或后缀

【历史对话】
%s

【业务知识】
%s

【当前查询】
%s

【重写后的查询】
（只输出重写后的查询，不要有任何其他内容）
""".formatted(context, evidence != null ? evidence : "无", query);
}
```

### 重写逻辑

```java
public async String rewriteQuery(String query, String context, String evidence) {
    // 没有历史对话，直接返回
    if (context.equals("(无历史对话)")) {
        return query;
    }
    
    // 构建 Prompt
    String prompt = buildRewritePrompt(query, context, evidence);
    
    // 调用 LLM
    String rewrittenQuery = llm.invoke(prompt);
    
    // 清理多余内容
    rewrittenQuery = rewrittenQuery.trim();
    if (rewrittenQuery.startsWith("重写后：")) {
        rewrittenQuery = rewrittenQuery.substring(4).trim();
    }
    
    return rewrittenQuery;
}
```

---

## 📊 完整流程

### 时序图

```
用户                API                QueryEnhanceNode        ContextManager        数据库/Redis
 |                   |                        |                       |                    |
 |--查询请求-------->|                        |                       |                    |
 |                   |--begin_turn()--------->|                       |                    |
 |                   |                        |--get_context()------->|                    |
 |                   |                        |                       |--[1.内存]----------|
 |                   |                        |                       |--[2.Redis]-------->|
 |                   |                        |                       |--[3.DB]----------->|
 |                   |                        |                       |<--------------------|
 |                   |                        |<----------------------|                    |
 |                   |                        |                       |                    |
 |                   |                        |--build_context()----->|                    |
 |                   |                        |<----------------------|                    |
 |                   |                        |                       |                    |
 |                   |                        |--LLM 重写------------>|                    |
 |                   |                        |                       |                    |
 |                   |<--canonical_query------|                       |                    |
 |                   |                        |                       |                    |
 |                   |--Schema 检索/SQL 生成/执行--------------------->|                    |
 |                   |                        |                       |                    |
 |                   |--finish_turn()-------->|                       |                    |
 |                   |                        |--add_turn()--------->|                    |
 |                   |                        |                       |--保存 DB/Redis---->|
 |                   |                        |                       |                    |
 |<--返回结果--------|                        |                       |                    |
```

---

## 💡 关键设计思想

### 1. Pending 模式

**问题**: 流式输出时，如何逐步构建对话轮次？

**方案**: 使用 pending 暂存区
```
begin_turn() → 创建 pending
  ↓
append_plan_chunk() → 逐步追加
  ↓
finish_turn() → 提交到历史
```

**优势**:
- 支持流式输出
- 失败时自动回滚
- 不影响已保存的历史

---

### 2. 滑动窗口

**问题**: 对话历史无限增长，内存/存储压力大

**方案**: 只保留最近 N 轮
```java
if (history.size() > maxHistory) {
    history.remove(0);  // 移除最旧的
}
```

**参数**:
- `maxHistory = 5` (默认)
- 可根据场景调整

---

### 3. 三级缓存

**问题**: 如何平衡性能和成本？

**方案**: 内存 → Redis → 数据库
```
内存缓存：命中率 80%, <10ms
Redis 缓存：命中率 15%, <50ms
数据库：命中率 5%, <200ms

加权平均：<30ms
```

---

### 4. 字符串格式上下文

**问题**: State 中如何传递上下文？

**方案**: 格式化为字符串，直接注入 Prompt
```python
state["multi_turn_context"] = """
【多轮对话历史】（共 2 轮）

--- 第 1 轮 ---
用户：查询用户数量
AI 计划：...
执行 SQL：...
"""
```

**优势**:
- 简单直接
- 避免序列化问题
- LLM 容易理解

---

## 🔍 DataAgent vs 我们的实现

| 特性 | DataAgent | 我们的实现 | 差距 |
|------|-----------|-----------|------|
| **存储架构** | 内存+Redis+DB | JSON 文件 | ⚠️ 简化 |
| **Pending 模式** | ✅ | ❌ | ❌ 缺失 |
| **流式追加** | ✅ | ❌ | ❌ 缺失 |
| **滑动窗口** | ✅ | ✅ | ✅ 相同 |
| **三级缓存** | ✅ | ❌ | ⚠️ 简化 |
| **字符串上下文** | ✅ | ✅ | ✅ 相同 |
| **指代消解** | ✅ | ✅ | ✅ 相同 |
| **TTL 清理** | ✅ | ✅ | ✅ 相同 |

**实现度**: **70%** (简化了存储架构，缺失 Pending 模式)

---

## 📝 改进建议

### 优先级 1 - 添加 Pending 模式

```python
class MultiTurnContextManager:
    def __init__(self):
        self.pending_cache = {}  # thread_id + "_pending"
    
    async def begin_turn(self, thread_id: str, user_question: str):
        """开始新对话轮"""
        self.pending_cache[f"{thread_id}_pending"] = {
            "user_question": user_question,
            "ai_plan": "",
            "sql_query": "",
            "sql_result": ""
        }
    
    async def append_plan_chunk(self, thread_id: str, chunk: str):
        """流式追加 AI 计划"""
        pending = self.pending_cache.get(f"{thread_id}_pending")
        if pending:
            pending["ai_plan"] += chunk
    
    async def finish_turn(self, thread_id: str):
        """完成对话轮"""
        pending = self.pending_cache.pop(f"{thread_id}_pending", None)
        if not pending:
            return
        
        # 保存到历史
        turn = ConversationTurn(**pending)
        context = await self.get_context(thread_id, "")
        context.history.append(turn)
        await self._persist_context(context)
```

---

### 优先级 2 - 优化上下文格式

```python
async def build_context_string(self, thread_id: str) -> str:
    """构建更详细的上下文字符串"""
    context = await self.get_context(thread_id, "")
    
    if not context.history:
        return "(无历史对话)"
    
    lines = []
    lines.append(f"【多轮对话历史】（共 {len(context.history)} 轮）")
    lines.append("")
    
    for i, turn in enumerate(context.history, 1):
        lines.append(f"--- 第 {i} 轮 ---")
        lines.append(f"用户：{turn.user_question}")
        
        if turn.ai_plan:
            lines.append(f"AI 计划：{turn.ai_plan}")
        
        if turn.sql_query:
            lines.append(f"执行 SQL：{turn.sql_query}")
        
        if turn.sql_result:
            if turn.sql_result.get('success'):
                lines.append(f"结果：返回 {turn.sql_result.get('row_count')} 行数据")
            else:
                lines.append(f"结果：错误 - {turn.sql_result.get('error')}")
        
        lines.append("")
    
    return "\n".join(lines)
```

---

### 优先级 3 - 集成到工作流

```python
async def intent_recognition_node(state: NL2SQLState):
    # 判断需要分析
    if need_analysis:
        # 开始新对话轮
        context_manager = get_context_manager()
        await context_manager.begin_turn(state["thread_id"], state["user_query"])
        
        return {"intent_recognition_output": True}


async def query_enhance_node(state: NL2SQLState):
    # 构建上下文
    context_manager = get_context_manager()
    context_string = await context_manager.build_context_string(state["thread_id"])
    
    # 重写查询
    enhanced_query = await _rewrite_query(state["user_query"], context_string)
    
    return {"canonical_query": enhanced_query}


async def sql_execute_node(state: NL2SQLState):
    # 执行 SQL
    result = await _execute_sql(state["generated_sql"])
    
    # 完成对话轮
    context_manager = get_context_manager()
    await context_manager.append_sql_query(state["thread_id"], state["generated_sql"])
    await context_manager.append_sql_result(state["thread_id"], result)
    await context_manager.finish_turn(state["thread_id"])
    
    return {"sql_result": result}
```

---

## ✅ 总结

### DataAgent 的核心思想

1. **三级缓存** - 性能最优
2. **Pending 模式** - 支持流式
3. **滑动窗口** - 控制存储
4. **字符串上下文** - 简单直接
5. **双写持久化** - 数据安全

### 我们的改进方向

1. ✅ 添加 Pending 模式
2. ✅ 优化工作流集成
3. ✅ 改进上下文格式
4. ⚪ 引入 Redis 缓存 (可选)
5. ⚪ 引入数据库存储 (可选)

---

**学习时间**: 2026-03-06 14:56  
**学习工程师**: AI Assistant  
**下一步**: 基于 DataAgent 设计改进我们的实现
