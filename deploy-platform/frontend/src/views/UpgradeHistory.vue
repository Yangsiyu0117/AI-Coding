<template>
  <div class="upgrade-history-page">
    <div class="page-header">
      <h2>升级历史</h2>
      <el-button type="primary" @click="$router.push('/upgrade/new')">新建升级</el-button>
    </div>

    <el-card shadow="never" class="content-card">
    <div class="filter-bar">
      <el-select v-model="filterEnvId" placeholder="按环境筛选" clearable @change="fetchData">
        <el-option label="全部环境" :value="undefined" />
        <el-option v-for="env in envStore.environments" :key="env.id" :label="env.name" :value="env.id" />
      </el-select>
    </div>

    <el-table v-if="tasks.length > 0" :data="tasks" v-loading="loading" stripe @row-click="goDetail">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="步骤" width="80">
        <template #default="{ row }">{{ row.steps?.length ?? 0 }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="goDetail(row)">详情</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row)">
            <template #reference>
              <span @click.stop>
                <el-button link type="danger" size="small">删除</el-button>
              </span>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" description="暂无升级历史记录">
      <el-button type="primary" @click="$router.push('/upgrade/new')">新建升级</el-button>
    </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useEnvironmentStore } from '../stores/environment'
import { fetchTasks, deleteTask, type UpgradeTask } from '../api/upgrades'

const router = useRouter()
const envStore = useEnvironmentStore()
const loading = ref(false)
const tasks = ref<UpgradeTask[]>([])
const filterEnvId = ref<number | undefined>()

function statusTag(status: string) {
  const map: Record<string, string> = {
    pending: 'info', running: 'warning', paused: 'warning', success: 'success', failed: 'danger',
  }
  return map[status] ?? 'info'
}

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: '待执行', running: '执行中', paused: '已暂停', success: '已完成', failed: '失败',
  }
  return map[status] ?? status
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

function goDetail(row: UpgradeTask) {
  router.push(`/upgrade/${row.id}`)
}

async function fetchData() {
  loading.value = true
  try {
    tasks.value = await fetchTasks(filterEnvId.value)
  } finally {
    loading.value = false
  }
}

async function handleDelete(row: UpgradeTask) {
  try {
    await deleteTask(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

onMounted(async () => {
  if (envStore.environments.length === 0) {
    await envStore.loadEnvironments()
  }
  await fetchData()
})
</script>

<style scoped>
.upgrade-history-page {
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

.content-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  background: #fafafa;
  padding: 12px 16px;
  border-radius: 6px;
}
</style>
