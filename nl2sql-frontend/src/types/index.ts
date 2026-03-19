/**
 * NL2SQL 平台 - 类型定义
 */

// 会话
export interface Session {
  id: string;
  agent_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

// 消息
export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  result?: QueryResultData;
  created_at: string;
}

// 查询结果数据
export interface QueryResultData {
  success: boolean;
  columns: string[];
  data: Record<string, any>[];
  row_count: number;
  error?: string;
}

// API 查询响应
export interface QueryResponse {
  thread_id: string;
  query: string;
  canonical_query?: string;
  generated_sql?: string;
  sql_result?: QueryResultData;
  error?: string;
}

// 会话创建请求
export interface CreateSessionRequest {
  agent_id: number;
  title?: string;
}

// 查询请求
export interface QueryRequest {
  query: string;
  agent_id: string;  // 后端要求字符串类型
  thread_id: string;
}
