<template>
  <div class="message-input-container">
    <el-input
      v-model="input"
      :disabled="disabled || isLoading"
      placeholder="输入查询，例如：统计用户总数"
      @keydown.enter.exact="handleSend"
      @keydown.shift.enter="handleNewLine"
      :rows="2"
      type="textarea"
      resize="none"
      class="message-input"
    >
      <template #append>
        <el-button
          type="primary"
          :disabled="disabled || isLoading || !input.trim()"
          :loading="isLoading"
          @click="handleSend"
          class="send-button"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </template>
    </el-input>
    
    <div class="input-hints">
      <span>按 Enter 发送</span>
      <span>Shift + Enter 换行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Promotion } from '@element-plus/icons-vue';

interface Props {
  disabled?: boolean;
  isLoading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  isLoading: false
});

const emit = defineEmits<{
  send: [query: string];
}>();

const input = ref('');

const handleSend = () => {
  const query = input.value.trim();
  if (query && !props.disabled && !props.isLoading) {
    emit('send', query);
    input.value = '';
  }
};

const handleNewLine = (event: KeyboardEvent) => {
  event.preventDefault();
  input.value += '\n';
};
</script>

<style scoped>
.message-input-container {
  width: 100%;
}

.message-input :deep(.el-textarea__inner) {
  padding-right: 80px;
  font-size: 14px;
  line-height: 1.6;
}

.send-button {
  width: 80px;
}

.input-hints {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
