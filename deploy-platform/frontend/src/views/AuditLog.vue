<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>操作审计</h2>
    </div>

    <el-card>
      <div class="filter-bar">
        <el-select v-model="filterAction" placeholder="操作类型" clearable style="width: 180px" @change="loadData">
          <el-option label="全部" value="" />
          <el-option label="创建服务" value="create_service" />
          <el-option label="更新服务" value="update_service" />
          <el-option label="删除服务" value="delete_service" />
          <el-option label="创建环境" value="create_environment" />
          <el-option label="更新环境" value="update_environment" />
          <el-option label="删除环境" value="delete_environment" />
          <el-option label="上传包" value="upload_package" />
          <el-option label="删除包" value="delete_package" />
          <el-option label="创建升级" value="create_upgrade_task" />
          <el-option label="开始升级" value="start_upgrade" />
          <el-option label="回滚任务" value="rollback_task" />
          <el-option label="删除升级" value="delete_upgrade_task" />
          <el-option label="用户注册" value="user_register" />
        </el-select>
        <el-button @click="refreshData">刷新</el-button>
      </div>

      <el-table :data="logs" v-loading="loading" border stripe style="margin-top: 12px">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="action" label="操作" width="150">
          <template #default="{ row }">
            <el-tag size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="目标类型" width="110" />
        <el-table-column prop="target_id" label="目标 ID" width="80" />
        <el-table-column prop="detail" label="详情" min-width="200">
          <template #default="{ row }">
            <span class="detail-text">{{ row.detail || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="用户 ID" width="80" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="currentPage"
        style="margin-top: 16px; justify-content: center"
        @current-change="loadData"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchAuditLogs, type AuditLogEntry } from '../api/audit'

const logs = ref<AuditLogEntry[]>([])
const loading = ref(false)
const filterAction = ref('')
const currentPage = ref(1)
const pageSize = 200
const total = ref(0)

function formatTime(t: string | null) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: pageSize }
    if (filterAction.value) params.action = filterAction.value
    const data = await fetchAuditLogs(params)
    logs.value = data
    total.value = data.length
  } finally {
    loading.value = false
  }
}

function refreshData() {
  currentPage.value = 1
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.audit-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  background: #fafafa;
  padding: 12px 16px;
  border-radius: 6px;
}

.detail-text {
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}
</style>
