<template>
  <div class="patrol-page">
    <div class="page-header">
      <h2>状态巡检</h2>
      <el-button type="primary" :loading="running" @click="handleRunPatrol">
        <el-icon><Search /></el-icon> 一键巡检
      </el-button>
    </div>

    <el-alert
      v-if="envStore.currentEnvId"
      :title="`巡检环境: ${envStore.currentEnvName}`"
      type="info"
      show-icon
      :closable="false"
      style="margin-bottom: 16px"
    />

    <div v-if="lastResult" class="result-section">
      <el-row :gutter="16" class="summary-row">
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="stat-card">
              <span class="stat-number">{{ lastResult.total_nodes }}</span>
              <span class="stat-label">节点总数</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="stat-card healthy">
              <span class="stat-number">{{ lastResult.healthy_nodes }}</span>
              <span class="stat-label">健康</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <div class="stat-card" :class="{ unhealthy: lastResult.unhealthy_nodes > 0 }">
              <span class="stat-number">{{ lastResult.unhealthy_nodes }}</span>
              <span class="stat-label">异常</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div class="checked-time">
        巡检时间：{{ formatTime(lastResult.checked_at) }}
      </div>

      <div v-for="group in groupedResults" :key="group.serviceName" class="service-group">
        <h4>{{ group.serviceName }}</h4>
        <el-table :data="group.nodes" border size="small">
          <el-table-column prop="host_ip" label="IP" width="160" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'healthy' ? 'success' : 'danger'" size="small">
                {{ row.status === 'healthy' ? '正常' : '异常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情" min-width="300">
            <template #default="{ row }">
              <code class="detail-text">{{ row.detail }}</code>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-empty v-else description="点击「一键巡检」开始检查所有服务节点状态" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useEnvironmentStore } from '../stores/environment'
import { runPatrol, type PatrolRunResponse } from '../api/patrol'

const envStore = useEnvironmentStore()
const running = ref(false)
const lastResult = ref<PatrolRunResponse | null>(null)

const groupedResults = computed(() => {
  if (!lastResult.value) return []
  const groups = new Map<string, { host_ip: string; status: string; detail: string }[]>()
  for (const r of lastResult.value.results) {
    let g = groups.get(r.service_name)
    if (!g) {
      g = []
      groups.set(r.service_name, g)
    }
    g.push({ host_ip: r.host_ip, status: r.status, detail: r.detail })
  }
  return [...groups.entries()].map(([serviceName, nodes]) => ({ serviceName, nodes }))
})

function formatTime(t: string) {
  return new Date(t).toLocaleString('zh-CN')
}

async function handleRunPatrol() {
  if (!envStore.currentEnvId) {
    ElMessage.warning('请先选择环境')
    return
  }
  running.value = true
  try {
    lastResult.value = await runPatrol(envStore.currentEnvId)
    ElMessage.success(
      `巡检完成：${lastResult.value.healthy_nodes} 正常，${lastResult.value.unhealthy_nodes} 异常`
    )
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '巡检执行失败')
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.patrol-page {
  max-width: 1100px;
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

.summary-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;
  padding: 8px 0;
}

.stat-card .stat-number {
  display: block;
  font-size: 32px;
  font-weight: 700;
  color: #303133;
}

.stat-card.healthy .stat-number {
  color: #67c23a;
}

.stat-card.unhealthy .stat-number {
  color: #f56c6c;
}

.stat-card .stat-label {
  display: block;
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.checked-time {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
}

.service-group {
  margin-bottom: 20px;
}

.service-group h4 {
  margin: 0 0 8px 0;
  font-size: 15px;
}

.detail-text {
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
