<template>
  <div class="session-list">
    <div class="session-header">
      <el-button
        type="primary"
        style="width: 100%"
        @click="$emit('create')"
        :icon="Plus"
      >
        新建对话
      </el-button>
    </div>

    <div class="sessions">
      <div
        v-for="session in sessions"
        :key="session.id"
        :class="['session-item', { active: session.id === currentSessionId }]"
        @click="$emit('select', session)"
      >
        <div class="session-header-inner">
          <span class="session-title">
            {{ session.title || '新会话' }}
          </span>
          <el-button
            v-if="session.id === currentSessionId"
            type="danger"
            link
            size="small"
            @click.stop="$emit('delete', session.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <div class="session-time">
          {{ formatTime(session.updated_at || session.created_at) }}
        </div>
      </div>

      <div v-if="sessions.length === 0" class="empty-sessions">
        <el-empty description="暂无会话" :image-size="60" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Delete } from '@element-plus/icons-vue';
import type { Session } from '@/types';

defineProps<{
  sessions: Session[];
  currentSessionId?: string;
}>();

defineEmits<{
  create: [];
  select: [session: Session];
  delete: [sessionId: string];
}>();

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
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.session-header {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.sessions {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.session-item:hover {
  background: var(--el-fill-color-light);
}

.session-item.active {
  background: var(--el-color-primary-light-9);
  border-left: 3px solid var(--el-color-primary);
}

.session-header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.session-title {
  flex: 1;
  font-size: 14px;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.empty-sessions {
  display: flex;
  justify-content: center;
  padding: 20px;
}
</style>
