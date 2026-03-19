<template>
  <div class="chat-dialog">
    <!-- 顶部标题栏 -->
    <div class="chat-header">
      <div class="header-left">
        <el-icon :size="24" color="var(--el-color-primary)">
          <DataAnalysis />
        </el-icon>
        <h1 class="header-title">NL2SQL Platform</h1>
      </div>
      <div class="header-right">
        <el-button
          type="primary"
          :icon="Plus"
          @click="handleNewSession"
        >
          新建对话
        </el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="chat-body">
      <!-- 左侧会话列表 -->
      <div class="sidebar">
        <SessionList
          :sessions="sessions"
          :current-session-id="currentSession?.id"
          @create="handleNewSession"
          @select="handleSelectSession"
          @delete="handleDeleteSession"
        />
      </div>

      <!-- 右侧对话区域 -->
      <div class="main-content">
        <div v-if="!currentSession" class="empty-chat">
          <el-empty description="请选择一个会话或点击新建对话开始聊天">
            <template #image>
              <el-icon :size="80" color="var(--el-color-primary)">
                <ChatDotRound />
              </el-icon>
            </template>
          </el-empty>
        </div>

        <template v-else>
          <!-- 消息列表 -->
          <MessageList
            :messages="messages"
            :is-loading="isLoading"
          />

          <!-- 错误提示 -->
          <el-alert
            v-if="error"
            type="error"
            :closable="false"
            show-icon
            class="error-alert"
          >
            {{ error }}
          </el-alert>

          <!-- 输入框 -->
          <div class="input-area">
            <MessageInput
              :disabled="!currentSession"
              :is-loading="isLoading"
              @send="handleSendMessage"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="chat-footer">
      <div class="status">
        <el-icon color="var(--el-color-success)"><CircleCheck /></el-icon>
        <span>运行中</span>
      </div>
      <div class="info">
        <span>Agent ID: {{ agentId }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue';
import {
  DataAnalysis,
  Plus,
  ChatDotRound,
  CircleCheck
} from '@element-plus/icons-vue';
import { useChatStore } from '@/stores/chat';
import SessionList from './SessionList.vue';
import MessageList from './MessageList.vue';
import MessageInput from './MessageInput.vue';
import type { Session } from '@/types';

const chatStore = useChatStore();

// 从 store 解构 - 使用 storeToRefs 保持响应性
const sessions = computed(() => chatStore.sessions);
const currentSession = computed(() => chatStore.currentSession);
const messages = computed(() => chatStore.messages);
const isLoading = computed(() => chatStore.isLoading);
const agentId = computed(() => chatStore.agentId);
const error = computed(() => chatStore.error);

// 直接使用 store 的方法
const { loadSessions, createNewSession, selectSession, deleteSessionById, sendMessage } = chatStore;

// 处理新建会话
const handleNewSession = async () => {
  try {
    await createNewSession();
    console.log('[ChatDialog] 新建会话成功');
  } catch (error) {
    console.error('[ChatDialog] 新建会话失败:', error);
  }
};

// 处理选择会话
const handleSelectSession = async (session: Session) => {
  try {
    await selectSession(session);
    console.log('[ChatDialog] 选择会话成功:', session.id);
  } catch (error) {
    console.error('[ChatDialog] 选择会话失败:', error);
  }
};

// 处理删除会话
const handleDeleteSession = async (sessionId: string) => {
  try {
    await deleteSessionById(sessionId);
    console.log('[ChatDialog] 删除会话成功:', sessionId);
  } catch (error) {
    console.error('[ChatDialog] 删除会话失败:', error);
  }
};

// 处理发送消息
const handleSendMessage = async (query: string) => {
  try {
    await sendMessage(query);
    console.log('[ChatDialog] 发送消息成功:', query);
  } catch (error) {
    console.error('[ChatDialog] 发送消息失败:', error);
  }
};

// 初始化
onMounted(async () => {
  await loadSessions();
  
  // 如果有会话，自动选择第一个
  if (sessions.value.length > 0) {
    const firstSession = sessions.value[0];
    if (firstSession) {
      await selectSession(firstSession);
    }
  }
});
</script>

<style scoped>
.chat-dialog {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--el-bg-color);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.chat-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty-chat {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.error-alert {
  margin: 0 24px 16px;
}

.chat-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 24px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
