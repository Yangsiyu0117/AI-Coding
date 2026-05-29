<template>
  <div class="upgrade-detail-page">
    <div class="top-bar">
      <div class="top-left">
        <el-button link @click="$router.push('/upgrades')">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2>{{ task?.title ?? '加载中...' }}</h2>
        <el-tag :type="statusTagType" size="default">{{ statusLabel }}</el-tag>
        <el-tag v-if="isRollingBack" type="warning" size="default">
          <el-icon class="spinning"><Loading /></el-icon> 回退中
        </el-tag>
        <span class="progress-text">
          {{ successCount }} / {{ steps.length }} 步完成
        </span>
      </div>
      <div class="top-right">
        <el-button
          v-if="task?.status === 'pending'"
          type="primary"
          :loading="starting"
          @click="handleStart"
        >
          开始升级
        </el-button>
        <el-button
          v-if="task?.status === 'running'"
          type="warning"
          :loading="pausing"
          @click="handlePause"
        >
          暂停
        </el-button>
        <el-button
          v-if="task?.status === 'paused'"
          type="success"
          :loading="resuming"
          @click="handleResume"
        >
          继续
        </el-button>
        <el-popconfirm
          v-if="task?.status === 'running' || task?.status === 'paused'"
          title="确定停止升级？已完成的步骤不会回退。"
          confirm-button-text="确认停止"
          @confirm="handleStop"
        >
          <template #reference>
            <el-button type="danger" :loading="stopping">停止</el-button>
          </template>
        </el-popconfirm>
        <el-popconfirm
          v-if="canRollback"
          title="确定回退已执行的步骤？回退将反向恢复备份文件和容器。"
          confirm-button-text="确认回退"
          @confirm="handleRollback"
        >
          <template #reference>
            <el-button type="danger" :loading="rollingBack">回退</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <div class="main-area">
      <div class="left-panel">
        <StepTree :steps="steps" @select-step="selectedStepId = $event" @retry-step="handleRetryStep" />
      </div>
      <div class="right-panel">
        <LogViewer :log-content="currentLog" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import StepTree from '../components/StepTree.vue'
import LogViewer from '../components/LogViewer.vue'
import { fetchTask, startTask, rollbackTask, pauseTask, resumeTask, stopTask, retryStep, type UpgradeTask, type TaskStep } from '../api/upgrades'

const route = useRoute()
const taskId = Number(route.params.id)

const task = ref<UpgradeTask | null>(null)
const steps = ref<TaskStep[]>([])
const starting = ref(false)
const rollingBack = ref(false)
const isRollingBack = ref(false)
const pausing = ref(false)
const resuming = ref(false)
const stopping = ref(false)
const selectedStepId = ref<number | null>(null)
const logsByStep = reactive<Record<number, string>>({})

let ws: WebSocket | null = null

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '待执行', running: '执行中', paused: '已暂停', success: '已完成', failed: '失败',
  }
  return map[task.value?.status ?? ''] ?? task.value?.status ?? '-'
})

const statusTagType = computed(() => {
  const map: Record<string, string> = {
    pending: 'info', running: 'warning', paused: 'warning', success: 'success', failed: 'danger',
  }
  return map[task.value?.status ?? ''] ?? 'info'
})

const successCount = computed(() => steps.value.filter((s) => s.status === 'success').length)

const canRollback = computed(() => {
  if (!task.value) return false
  if (isRollingBack.value) return false
  if (task.value.rollback_status !== 'none') return false
  const s = task.value.status
  // 有已完成步骤才能回退
  return (s === 'failed' || s === 'success') && successCount.value > 0
})

const currentLog = computed(() => {
  if (selectedStepId.value === null) return ''
  return logsByStep[selectedStepId.value] ?? ''
})

function connectWebSocket() {
  const token = localStorage.getItem('token') ?? ''
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const url = `${protocol}//${location.host}/api/upgrades/ws/${taskId}?token=${encodeURIComponent(token)}`

  ws = new WebSocket(url)
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)

      if (msg.type === 'log') {
        logsByStep[msg.step_id] = (logsByStep[msg.step_id] ?? '') + msg.text
      } else if (msg.type === 'step_update') {
        const step = steps.value.find((s) => s.id === msg.step_id)
        if (step) {
          if (msg.status !== undefined) step.status = msg.status
          if (msg.rollback_status !== undefined) step.rollback_status = msg.rollback_status
        }
      } else if (msg.type === 'wave_start') {
        for (const sid of msg.step_ids) {
          const step = steps.value.find((s) => s.id === sid)
          if (step) step.status = 'running'
        }
      } else if (msg.type === 'task_status') {
        if (task.value) task.value.status = msg.status
        if (msg.status === 'paused') {
          ElMessage.info('升级已暂停')
        } else if (msg.status === 'running') {
          ElMessage.info('升级已恢复')
        } else if (msg.status === 'failed' && msg.message) {
          ElMessage.warning(msg.message)
        }
      } else if (msg.type === 'task_complete') {
        if (task.value) task.value.status = msg.status
        const text = msg.status === 'success' ? '升级任务完成' : `升级任务结束: ${msg.status}`
        ElMessage[msg.status === 'success' ? 'success' : 'warning'](text)
      } else if (msg.type === 'rollback_start') {
        isRollingBack.value = true
        ElMessage.info('开始回退...')
      } else if (msg.type === 'rollback_complete') {
        isRollingBack.value = false
        if (task.value) task.value.rollback_status = msg.status
        ElMessage.info('回退完成')
      }
    } catch {
      // Ignore non-JSON messages
    }
  }

  ws.onerror = () => {}
}

async function handleStart() {
  starting.value = true
  try {
    await startTask(taskId)
    if (task.value) task.value.status = 'running'
    if (ws) { ws.close(); ws = null }
    connectWebSocket()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '启动失败')
  } finally {
    starting.value = false
  }
}

async function handleRollback() {
  rollingBack.value = true
  try {
    await rollbackTask(taskId)
    isRollingBack.value = true
    connectWebSocket()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '回退失败')
  } finally {
    rollingBack.value = false
  }
}

async function handlePause() {
  pausing.value = true
  try {
    await pauseTask(taskId)
    if (task.value) task.value.status = 'paused'
    ElMessage.success('暂停请求已发送，将在当前步骤完成后暂停')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '暂停失败')
  } finally {
    pausing.value = false
  }
}

async function handleResume() {
  resuming.value = true
  try {
    await resumeTask(taskId)
    if (task.value) task.value.status = 'running'
    ElMessage.success('继续执行')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '继续失败')
  } finally {
    resuming.value = false
  }
}

async function handleStop() {
  stopping.value = true
  try {
    await stopTask(taskId)
    ElMessage.success('停止请求已发送')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '停止失败')
  } finally {
    stopping.value = false
  }
}

async function handleRetryStep(stepId: number) {
  try {
    // Clear old log for this step so it starts fresh
    delete logsByStep[stepId]
    await retryStep(taskId, stepId)
    ElMessage.success('步骤已开始重试')
    // Close old WebSocket and wait for it to fully disconnect before reconnecting
    if (ws) {
      const oldWs = ws
      ws = null
      oldWs.close()
      // Wait a tick for the close to propagate before opening a new connection
      await new Promise(r => setTimeout(r, 200))
    }
    connectWebSocket()
    selectedStepId.value = stepId
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '重试失败')
  }
}

onMounted(async () => {
  try {
    const data = await fetchTask(taskId)
    task.value = data
    steps.value = data.steps
    for (const step of data.steps) {
      if (step.log_output) {
        logsByStep[step.id] = step.log_output
      }
    }
    // Smart step selection: running > pending > last with log > last step
    if (data.steps.length > 0) {
      const running = data.steps.find(s => s.status === 'running')
      const pending = data.steps.find(s => s.status === 'pending')
      if (running) {
        selectedStepId.value = running.id
      } else if (pending) {
        selectedStepId.value = pending.id
      } else {
        const lastWithLog = [...data.steps].reverse().find(s => s.log_output)
        selectedStepId.value = lastWithLog ? lastWithLog.id : data.steps[data.steps.length - 1].id
      }
    }
    if (data.status === 'running' || data.status === 'paused') {
      connectWebSocket()
    }
  } catch {
    ElMessage.error('加载任务失败')
  }
})

onBeforeUnmount(() => {
  ws?.close()
})
</script>

<style scoped>
.upgrade-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.top-left h2 {
  margin: 0;
  font-size: 18px;
}

.top-right {
  display: flex;
  gap: 8px;
}

.progress-text {
  color: #909399;
  font-size: 13px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.main-area {
  display: flex;
  gap: 20px;
  height: calc(100vh - 160px);
}

.left-panel {
  width: 340px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 8px;
  overflow-y: auto;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.right-panel {
  flex: 1;
  min-width: 0;
}
</style>
