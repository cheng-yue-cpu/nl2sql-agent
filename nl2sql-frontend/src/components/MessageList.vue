<template>
  <div class="message-list" ref="containerRef">
    <!-- 空状态 -->
    <div v-if="messages.length === 0" class="empty-state">
      <el-empty description="开始新的对话吧" :image-size="80">
        <template #image>
          <el-icon :size="80" color="var(--el-color-primary)">
            <ChatDotRound />
          </el-icon>
        </template>
      </el-empty>
    </div>

    <!-- 消息列表 -->
    <div v-else class="messages">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message', message.role]"
      >
        <div class="message-avatar">
          <el-avatar :size="36" :icon="message.role === 'user' ? User : Service" />
        </div>
        
        <div class="message-content">
          <div class="message-text">
            {{ message.content }}
          </div>
          
          <!-- SQL 展示 -->
          <SqlDisplay
            v-if="message.sql"
            :sql="message.sql"
          />
          
          <!-- 结果表格 -->
          <ResultTable
            v-if="message.result && message.result.success && message.result.data"
            :data="message.result.data"
            :columns="message.result.columns"
          />
          
          <!-- 错误信息 -->
          <div v-if="message.result && !message.result.success" class="error-message">
            <el-icon><Warning /></el-icon>
            <span>{{ message.result.error }}</span>
          </div>
        </div>
        
        <div class="message-time">
          {{ formatTime(message.created_at) }}
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-message">
        <el-icon class="is-loading" :size="20">
          <Loading />
        </el-icon>
        <span>AI 正在思考中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import {
  User,
  Service,
  ChatDotRound,
  Loading,
  Warning
} from '@element-plus/icons-vue';
import type { Message } from '@/types';
import SqlDisplay from './SqlDisplay.vue';
import ResultTable from './ResultTable.vue';

const props = defineProps<{
  messages: Message[];
  isLoading: boolean;
}>();

const containerRef = ref<HTMLElement | null>(null);

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick();
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight;
  }
};

// 监听消息变化
watch(
  () => props.messages.length,
  () => scrollToBottom()
);

// 监听加载状态
watch(
  () => props.isLoading,
  (newVal) => {
    if (!newVal) {
      scrollToBottom();
    }
  }
);

// 格式化时间
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  // 今天
  if (diff < 24 * 60 * 60 * 1000) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }
  
  // 昨天
  if (diff < 48 * 60 * 60 * 1000) {
    return '昨天';
  }
  
  // 更早
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
};
</script>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.messages {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message.assistant {
  align-self: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message.user .message-content {
  align-items: flex-end;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  max-width: 100%;
  word-break: break-word;
}

.message.assistant .message-text {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  border-bottom-left-radius: 4px;
}

.message.user .message-text {
  background: var(--el-color-primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.message.user .message-time {
  text-align: right;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--el-color-danger-light-9);
  border: 1px solid var(--el-color-danger-light-5);
  border-radius: 8px;
  color: var(--el-color-danger);
  font-size: 13px;
}
</style>
