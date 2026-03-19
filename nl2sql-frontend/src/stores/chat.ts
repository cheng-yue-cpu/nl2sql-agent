/**
 * NL2SQL 平台 - 聊天状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Session, Message } from '@/types';
import * as api from '@/api/nl2sql';

export const useChatStore = defineStore('chat', () => {
  // State
  const sessions = ref<Session[]>([]);
  const currentSession = ref<Session | null>(null);
  const messages = ref<Message[]>([]);
  const isLoading = ref(false);
  const agentId = ref<number>(1);
  const error = ref<string | null>(null);

  // Getters
  const hasActiveSession = computed(() => !!currentSession.value);

  // Actions
  /**
   * 加载会话列表
   */
  async function loadSessions() {
    try {
      sessions.value = await api.getSessions(agentId.value);
    } catch (err) {
      console.error('加载会话失败:', err);
      error.value = '加载会话失败';
    }
  }

  /**
   * 创建新会话
   */
  async function createNewSession(title?: string) {
    try {
      const session = await api.createSession({
        agent_id: agentId.value,
        title
      });
      
      sessions.value.unshift(session);
      currentSession.value = session;
      messages.value = [];
      error.value = null;
      
      return session;
    } catch (err) {
      console.error('创建会话失败:', err);
      error.value = '创建会话失败';
      throw err;
    }
  }

  /**
   * 选择会话
   */
  async function selectSession(session: Session) {
    try {
      currentSession.value = session;
      messages.value = await api.getSessionMessages(session.id);
      error.value = null;
    } catch (err) {
      console.error('加载消息失败:', err);
      error.value = '加载消息失败';
    }
  }

  /**
   * 删除会话
   */
  async function deleteSessionById(sessionId: string) {
    try {
      await api.deleteSession(agentId.value, sessionId);
      sessions.value = sessions.value.filter(s => s.id !== sessionId);
      
      if (currentSession.value?.id === sessionId) {
        currentSession.value = null;
        messages.value = [];
      }
    } catch (err) {
      console.error('删除会话失败:', err);
      error.value = '删除会话失败';
    }
  }

  /**
   * 清空所有会话
   */
  async function clearAllSessions() {
    try {
      await api.clearSessions(agentId.value);
      sessions.value = [];
      currentSession.value = null;
      messages.value = [];
    } catch (err) {
      console.error('清空会话失败:', err);
      error.value = '清空会话失败';
    }
  }

  /**
   * 发送消息
   */
  async function sendMessage(query: string) {
    if (!currentSession.value) {
      error.value = '请先选择或创建一个会话';
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      console.log('[ChatStore] 开始发送消息:', query);

      // 添加用户消息
      const userMessage: Message = {
        id: `msg_${Date.now()}`,
        session_id: currentSession.value.id,
        role: 'user',
        content: query,
        created_at: new Date().toISOString()
      };
      
      messages.value.push(userMessage);
      await api.saveMessage(currentSession.value.id, userMessage);
      console.log('[ChatStore] 用户消息已添加');

      // 发送查询到后端
      console.log('[ChatStore] 调用后端 API...');
      const response = await api.sendQuery({
        query,
        agent_id: String(agentId.value),  // 转换为字符串
        thread_id: currentSession.value.id
      });
      console.log('[ChatStore] 后端响应:', response);

      // 检查响应是否有错误
      if (response.error) {
        throw new Error(response.error);
      }

      // 构建 AI 响应消息
      const aiMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        session_id: currentSession.value.id,
        role: 'assistant',
        content: response.canonical_query || response.query,
        sql: response.generated_sql,
        result: response.sql_result,
        created_at: new Date().toISOString()
      };
      
      messages.value.push(aiMessage);
      await api.saveMessage(currentSession.value.id, aiMessage);
      console.log('[ChatStore] AI 消息已添加');

      // 更新会话标题（如果是第一条消息）
      if (messages.value.length === 2) {
        currentSession.value.title = query.slice(0, 20) + (query.length > 20 ? '...' : '');
        await loadSessions();
      }
    } catch (err) {
      console.error('[ChatStore] 发送消息失败:', err);
      const errorMsg = err instanceof Error ? err.message : '发送消息失败，请检查网络连接';
      error.value = errorMsg;
      
      // 添加错误消息
      const errorMessage: Message = {
        id: `msg_${Date.now()}`,
        session_id: currentSession.value!.id,
        role: 'assistant',
        content: `❌ 错误：${errorMsg}`,
        created_at: new Date().toISOString()
      };
      messages.value.push(errorMessage);
    } finally {
      isLoading.value = false;
      console.log('[ChatStore] 发送完成，isLoading=false');
    }
  }

  return {
    // State
    sessions,
    currentSession,
    messages,
    isLoading,
    agentId,
    error,
    // Getters
    hasActiveSession,
    // Actions
    loadSessions,
    createNewSession,
    selectSession,
    deleteSessionById,
    clearAllSessions,
    sendMessage
  };
});
