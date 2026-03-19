/**
 * NL2SQL 平台 - API 调用
 */
import axios from 'axios';
import type {
  Session,
  Message,
  QueryResponse,
  CreateSessionRequest,
  QueryRequest
} from '@/types';

// 远程访问配置：使用服务器外部 IP
// 本地访问可改为 http://localhost:8000/api 或 http://127.0.0.1:8000/api
const API_BASE_URL = 'http://47.254.121.85:8000/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 秒超时
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false // 不发送 cookies
});

// 添加请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log('[API] 发送请求:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('[API] 请求拦截器错误:', error);
    return Promise.reject(error);
  }
);

// 添加响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('[API] 响应:', response.status, response.data);
    return response;
  },
  (error) => {
    console.error('[API] 响应错误:', error);
    console.error('[API] 错误代码:', error.code);
    console.error('[API] 错误类型:', error.constructor.name);
    
    let errorMessage = '请求失败';
    
    if (error.code === 'ECONNREFUSED') {
      errorMessage = `无法连接到后端服务 (ECONNREFUSED)
      
可能原因:
1. 后端服务未启动
2. 后端监听地址不是 127.0.0.1:8000
3. 防火墙阻止连接

请检查后端服务状态。`;
    } else if (error.code === 'ERR_NETWORK') {
      errorMessage = `网络错误 (ERR_NETWORK)
      
可能原因:
1. CORS 跨域问题
2. 后端服务未响应
3. 网络连接中断

错误详情：${error.message}`;
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = `请求超时 (超过 60 秒)
      
可能原因:
1. 后端处理时间过长
2. 网络延迟
3. LLM 响应慢

请重试或联系管理员。`;
    } else if (error.response) {
      // 后端返回了错误响应
      const status = error.response.status;
      const data = error.response.data;
      errorMessage = `HTTP ${status}: ${data?.detail || data?.error || '未知错误'}`;
    } else {
      errorMessage = `请求失败：${error.message}`;
    }
    
    return Promise.reject(new Error(errorMessage));
  }
);

/**
 * 获取会话列表
 */
export async function getSessions(agentId: number): Promise<Session[]> {
  // 临时实现：从 localStorage 获取
  const key = `sessions_${agentId}`;
  const data = localStorage.getItem(key);
  return data ? JSON.parse(data) : [];
}

/**
 * 创建新会话
 */
export async function createSession(request: CreateSessionRequest): Promise<Session> {
  const session: Session = {
    id: `session_${Date.now()}`,
    agent_id: request.agent_id,
    title: request.title || '新会话',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  
  // 临时实现：保存到 localStorage
  const key = `sessions_${request.agent_id}`;
  const sessions: Session[] = JSON.parse(localStorage.getItem(key) || '[]');
  sessions.unshift(session);
  localStorage.setItem(key, JSON.stringify(sessions));
  
  // 创建会话的消息存储
  localStorage.setItem(`messages_${session.id}`, JSON.stringify([]));
  
  return session;
}

/**
 * 删除会话
 */
export async function deleteSession(agentId: number, sessionId: string): Promise<void> {
  const key = `sessions_${agentId}`;
  const sessions: Session[] = JSON.parse(localStorage.getItem(key) || '[]');
  const filtered = sessions.filter(s => s.id !== sessionId);
  localStorage.setItem(key, JSON.stringify(filtered));
  
  // 同时删除消息
  localStorage.removeItem(`messages_${sessionId}`);
}

/**
 * 清空所有会话
 */
export async function clearSessions(agentId: number): Promise<void> {
  const key = `sessions_${agentId}`;
  localStorage.removeItem(key);
}

/**
 * 获取会话消息
 */
export async function getSessionMessages(sessionId: string): Promise<Message[]> {
  const key = `messages_${sessionId}`;
  const data = localStorage.getItem(key);
  return data ? JSON.parse(data) : [];
}

/**
 * 保存消息
 */
export async function saveMessage(sessionId: string, message: Message): Promise<Message> {
  const key = `messages_${sessionId}`;
  const messages: Message[] = JSON.parse(localStorage.getItem(key) || '[]');
  messages.push(message);
  localStorage.setItem(key, JSON.stringify(messages));
  
  // 更新会话的 updated_at
  updateSessionTime(sessionId);
  
  return message;
}

/**
 * 更新会话时间
 */
function updateSessionTime(sessionId: string): void {
  for (let i = 0; i < 100; i++) {
    const key = `sessions_${i}`;
    const sessions: Session[] = JSON.parse(localStorage.getItem(key) || '[]');
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      session.updated_at = new Date().toISOString();
      localStorage.setItem(key, JSON.stringify(sessions));
      break;
    }
  }
}

/**
 * 发送 NL2SQL 查询
 */
export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  console.log('[API] 发送查询请求:', request);
  
  try {
    const response = await api.post<QueryResponse>('/nl2sql/query', request);
    console.log('[API] 查询响应:', response.status, response.data);
    return response.data;
  } catch (error: any) {
    console.error('[API] 查询失败:', error);
    console.error('[API] 响应状态:', error.response?.status);
    console.error('[API] 响应数据:', error.response?.data);
    console.error('[API] 请求数据:', request);
    throw error;
  }
}
