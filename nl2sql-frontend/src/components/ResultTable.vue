<template>
  <div class="result-table">
    <div class="table-header">
      <div class="table-title">
        <el-icon><DataLine /></el-icon>
        <span>查询结果</span>
        <el-tag size="small" type="info">{{ data.length }} 条</el-tag>
      </div>
    </div>
    <div class="table-content">
      <el-table :data="data" stripe style="width: 100%" max-height="400" size="small">
        <el-table-column
          v-for="column in columns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="120"
        />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { DataLine } from '@element-plus/icons-vue';

defineProps<{
  data: Record<string, any>[];
  columns: string[];
}>();
</script>

<style scoped>
.result-table {
  margin: 12px 0;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color);
}

.table-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.table-content {
  padding: 0;
}

:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table th) {
  background-color: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-weight: 500;
}

:deep(.el-table td) {
  padding: 8px 0;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: var(--el-fill-color-lighter);
}
</style>
