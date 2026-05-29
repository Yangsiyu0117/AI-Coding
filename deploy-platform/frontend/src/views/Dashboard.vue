<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>仪表盘</h2>
      <span class="env-info" v-if="envStore.currentEnvId">
        当前环境：<el-tag size="default">{{ envStore.currentEnvName }}</el-tag>
      </span>
    </div>

    <el-card v-if="showOnboarding" class="onboarding-card" shadow="hover">
      <template #header>
        <span class="onboarding-title">欢迎使用 {{ appTitle }}</span>
      </template>
      <el-steps :active="onboardingSteps.filter(s => s.done).length" finish-status="success" align-center>
        <el-step v-for="(s, i) in onboardingSteps" :key="i"
          :title="s.title" :description="s.desc"
          :status="s.done ? 'success' : i === onboardingSteps.filter(s => s.done).length ? 'process' : 'wait'"
        />
      </el-steps>
      <div class="onboarding-actions">
        <span class="onboarding-hint">按步骤开始配置，或直接</span>
        <el-button
          v-for="(s, i) in onboardingSteps" :key="i"
          :type="!s.done ? 'primary' : 'default'"
          :disabled="s.done"
          size="small"
          @click="router.push(s.link)"
        >
          {{ s.title }}
        </el-button>
      </div>
    </el-card>

    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-blue">
          <div class="stat-icon">
            <el-icon :size="28"><Setting /></el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ serviceCount }}</span>
            <span class="stat-label">服务总数</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-green">
          <div class="stat-icon">
            <el-icon :size="28"><CircleCheckFilled /></el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ patrolResult?.healthy_nodes ?? '-' }}</span>
            <span class="stat-label">健康节点</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-red">
          <div class="stat-icon">
            <el-icon :size="28"><CircleCloseFilled /></el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ patrolResult?.unhealthy_nodes ?? '-' }}</span>
            <span class="stat-label">异常节点</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-card-orange">
          <div class="stat-icon">
            <el-icon :size="28"><Clock /></el-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ recentTasks.filter(t => t.status === 'pending' || t.status === 'running').length }}</span>
            <span class="stat-label">进行中任务</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="bottom-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近升级记录</span>
              <el-button link type="primary" @click="$router.push('/upgrades')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentTasks" size="small" @row-click="goUpgrade">
            <el-table-column prop="title" label="任务" min-width="200" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loadingTasks && recentTasks.length === 0" description="暂无升级记录" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>快速操作</span>
          </template>
          <div class="quick-actions">
            <div class="action-item action-primary" @click="$router.push('/upgrade/new')">
              <span class="action-icon"><el-icon><Plus /></el-icon></span>
              <span class="action-label">新建升级</span>
              <el-icon class="action-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="action-item" @click="$router.push('/patrol')">
              <span class="action-icon"><el-icon><Search /></el-icon></span>
              <span class="action-label">一键巡检</span>
              <el-icon class="action-arrow"><ArrowRight /></el-icon>
            </div>
            <div class="action-item" @click="$router.push('/services')">
              <span class="action-icon"><el-icon><Tools /></el-icon></span>
              <span class="action-label">服务管理</span>
              <el-icon class="action-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Setting, CircleCheckFilled, CircleCloseFilled, Clock, Plus, Search, Tools, ArrowRight } from '@element-plus/icons-vue'
import { useEnvironmentStore } from '../stores/environment'
import { fetchServices } from '../api/services'
import { fetchTasks, type UpgradeTask } from '../api/upgrades'
import { fetchPackages } from '../api/packages'
import { runPatrol, type PatrolRunResponse } from '../api/patrol'
import { fetchAppConfig } from '../api/config'

const router = useRouter()
const envStore = useEnvironmentStore()
const serviceCount = ref(0)
const packageCount = ref(0)
const appTitle = ref('运维升级发布平台')
const patrolResult = ref<PatrolRunResponse | null>(null)
const recentTasks = ref<UpgradeTask[]>([])
const loadingTasks = ref(false)
const loadingOnboarding = ref(true)

const showOnboarding = computed(() => {
  return !loadingOnboarding.value && envStore.environments.length === 0
})

const onboardingSteps = computed(() => {
  const hasEnv = envStore.environments.length > 0
  const hasSvc = serviceCount.value > 0
  const hasPkg = packageCount.value > 0
  return [
    { title: '创建环境', desc: '先创建部署环境（如测试、UAT、生产）', done: hasEnv, link: '/settings' },
    { title: '添加服务', desc: '在环境中注册需要管理的服务及节点信息', done: hasSvc, link: '/services' },
    { title: '上传升级包', desc: '上传服务的升级包文件（tar.gz / zip）', done: hasPkg, link: '/packages' },
    { title: '创建升级任务', desc: '选择服务和包，创建升级任务并执行', done: false, link: '/upgrade/new' },
  ]
})

function statusTag(s: string) {
  const map: Record<string, string> = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[s] ?? 'info'
}

function statusText(s: string) {
  const map: Record<string, string> = { pending: '待执行', running: '执行中', success: '已完成', failed: '失败' }
  return map[s] ?? s
}

function formatTime(t: string | null) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

function goUpgrade(row: UpgradeTask) {
  router.push(`/upgrade/${row.id}`)
}

onMounted(async () => {
  fetchAppConfig().then(cfg => { appTitle.value = cfg.app_title }).catch(() => {})

  if (envStore.environments.length === 0) {
    await envStore.loadEnvironments()
  }

  try {
    const services = await fetchServices()
    serviceCount.value = services.length
  } catch {
    // Silently fail — stats show as 0
  }

  try {
    const packages = await fetchPackages()
    packageCount.value = packages.length
  } catch {
    // Silently fail
  }

  loadingOnboarding.value = false

  if (envStore.currentEnvId) {
    patrolResult.value = await runPatrol(envStore.currentEnvId).catch(() => null)
  }

  loadingTasks.value = true
  try {
    const tasks = await fetchTasks()
    recentTasks.value = tasks.slice(0, 5)
  } finally {
    loadingTasks.value = false
  }
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.env-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  transition: transform 0.2s, box-shadow 0.2s;
  border-top: 3px solid transparent;
  border-radius: 6px;
}

.stat-card-blue { border-top-color: #409eff; }
.stat-card-green { border-top-color: #67c23a; }
.stat-card-red { border-top-color: #f56c6c; }
.stat-card-orange { border-top-color: #e6a23c; }

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px !important;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card-blue .stat-icon { background: #ecf5ff; color: #409eff; }
.stat-card-green .stat-icon { background: #f0f9eb; color: #67c23a; }
.stat-card-red .stat-icon { background: #fef0f0; color: #f56c6c; }
.stat-card-orange .stat-icon { background: #fdf6ec; color: #e6a23c; }

.stat-body {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.bottom-row {
  margin-top: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.2s;
}

.action-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
}

.action-item.action-primary {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.action-item.action-primary:hover {
  background: #337ecc;
  border-color: #337ecc;
}

.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  font-size: 18px;
  flex-shrink: 0;
}

.action-item.action-primary .action-icon {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.action-label {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
}

.action-arrow {
  color: #c0c4cc;
  font-size: 14px;
  flex-shrink: 0;
}

.action-item.action-primary .action-arrow {
  color: rgba(255, 255, 255, 0.7);
}

.dashboard-page :deep(.el-table__row) {
  cursor: pointer;
}

.onboarding-card {
  margin-bottom: 24px;
  border: 1px solid #d9ecff;
  background: linear-gradient(135deg, #f0f7ff 0%, #fff 100%);
}

.onboarding-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.onboarding-card :deep(.el-card__header) {
  border-bottom: 1px solid #d9ecff;
}

.onboarding-actions {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
}

.onboarding-hint {
  color: #909399;
  font-size: 13px;
  margin-right: 4px;
}
</style>
