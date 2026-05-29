<template>
  <div class="step-tree">
    <el-tree
      :data="treeData"
      node-key="id"
      :props="{ children: 'children', label: 'label' }"
      :default-expand-all="true"
      highlight-current
      @node-click="onNodeClick"
    >
      <template #default="{ node, data }">
        <span class="tree-node" :class="{ 'is-step': data.isStep }">
          <span class="step-status">
            <!-- Rollback status takes priority -->
            <template v-if="data.rollbackStatus === 'rolling_back'">
              <el-icon class="spinning" color="#e6a23c"><Loading /></el-icon>
            </template>
            <template v-else-if="data.rollbackStatus === 'rollback_success'">
              <el-icon color="#67c23a"><RefreshRight /></el-icon>
            </template>
            <template v-else-if="data.rollbackStatus === 'rollback_failed'">
              <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
            </template>
            <!-- Normal status -->
            <template v-else-if="data.status === 'running'">
              <el-icon class="spinning"><Loading /></el-icon>
            </template>
            <template v-else-if="data.status === 'success'">
              <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
            </template>
            <template v-else-if="data.status === 'failed'">
              <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
            </template>
            <template v-else>
              <el-icon color="#909399"><Clock /></el-icon>
            </template>
          </span>
          <span class="step-label">{{ node.label }}</span>
          <el-button
            v-if="data.status === 'failed'"
            link
            type="danger"
            size="small"
            class="retry-btn"
            @click.stop="onRetryClick(data)"
          >
            重试
          </el-button>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Clock, Loading, CircleCheckFilled, CircleCloseFilled, RefreshRight } from '@element-plus/icons-vue'
import type { TaskStep } from '../api/upgrades'
import { fetchStepLabels } from '../api/services'

const stepLabels = ref<Record<string, string>>({})

interface TreeNode {
  id: string
  label: string
  isStep?: boolean
  status?: string
  rollbackStatus?: string
  stepId?: number
  children?: TreeNode[]
}

const props = defineProps<{
  steps: TaskStep[]
}>()

const emit = defineEmits<{
  'select-step': [stepId: number]
  'retry-step': [stepId: number]
}>()

const treeData = computed<TreeNode[]>(() => {
  const groups = new Map<number, { name: string; nodeIp: string; steps: TaskStep[] }>()
  for (const step of props.steps) {
    let g = groups.get(step.service_id)
    if (!g) {
      g = { name: step.service_name, nodeIp: step.node_ip, steps: [] }
      groups.set(step.service_id, g)
    }
    g.steps.push(step)
  }

  return [...groups.entries()].map(([svcId, g]) => {
    const done = g.steps.filter((s) => s.status === 'success').length
    const total = g.steps.length
    return {
      id: `svc-${svcId}`,
      label: `[${g.nodeIp}] ${g.name} (${done}/${total})`,
      children: g.steps.map((s) => ({
        id: `step-${s.id}`,
        label: `${stepLabels.value[s.step_type] || s.step_type}`,
        isStep: true,
        status: s.status,
        rollbackStatus: s.rollback_status !== 'none' ? s.rollback_status : undefined,
        stepId: s.id,
      })),
    }
  })
})

onMounted(async () => {
  try {
    stepLabels.value = await fetchStepLabels()
  } catch { /* use empty labels, fallback to step_type key */ }
})

function onNodeClick(data: TreeNode) {
  if (data.stepId) {
    emit('select-step', data.stepId)
  }
}

function onRetryClick(data: TreeNode) {
  if (data.stepId) {
    emit('retry-step', data.stepId)
  }
}
</script>

<style scoped>
.step-tree {
  font-size: 14px;
}

.step-tree :deep(.el-tree-node__content) {
  transition: background-color 0.15s;
  border-radius: 4px;
}

.step-tree :deep(.el-tree-node__content:hover) {
  background-color: #f0f2f5;
}

.tree-node {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tree-node.is-step {
  cursor: pointer;
}

.step-status {
  display: inline-flex;
  align-items: center;
  width: 18px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.retry-btn {
  margin-left: auto;
  font-size: 12px;
}
</style>
