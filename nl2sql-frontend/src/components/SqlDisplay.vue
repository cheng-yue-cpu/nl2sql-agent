<template>
  <div class="sql-display">
    <div class="sql-header">
      <div class="sql-title">
        <el-icon><Document /></el-icon>
        <span>生成的 SQL</span>
      </div>
      <el-button size="small" @click="copySql" :icon="Copy">
        复制
      </el-button>
    </div>
    <div class="sql-content">
      <pre><code class="language-sql" v-html="highlightedSql"></code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Document, DocumentCopy as Copy } from '@element-plus/icons-vue';
import hljs from 'highlight.js/lib/core';
import sql from 'highlight.js/lib/languages/sql';
import { ElMessage } from 'element-plus';

// 注册 SQL 语言
hljs.registerLanguage('sql', sql);

const props = defineProps<{
  sql: string;
}>();

const highlightedSql = computed(() => {
  if (!props.sql) return '';
  try {
    return hljs.highlight(props.sql, { language: 'sql' }).value;
  } catch {
    return props.sql;
  }
});

const copySql = async () => {
  try {
    await navigator.clipboard.writeText(props.sql);
    ElMessage.success('SQL 已复制到剪贴板');
  } catch (err) {
    ElMessage.error('复制失败');
  }
};
</script>

<style scoped>
.sql-display {
  margin: 12px 0;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-fill-color-light);
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--el-fill-color);
  border-bottom: 1px solid var(--el-border-color);
}

.sql-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.sql-content {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
}

.sql-content pre {
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.sql-content code {
  color: var(--el-text-color-primary);
}

/* SQL 语法高亮 */
.hljs-keyword {
  color: #2196f3;
  font-weight: bold;
}

.hljs-function {
  color: #9c27b0;
}

.hljs-string {
  color: #4caf50;
}

.hljs-number {
  color: #ff9800;
}

.hljs-comment {
  color: #9e9e9e;
  font-style: italic;
}
</style>
