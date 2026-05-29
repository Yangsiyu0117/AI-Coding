<template>
  <div class="upgrade-new-page">
    <div class="page-header">
      <h2>创建升级任务</h2>
    </div>

    <el-steps :active="activeStep" align-center style="margin-bottom: 32px">
      <el-step title="选择服务" />
      <el-step title="关联升级包" />
      <el-step title="确认执行" />
    </el-steps>

    <!-- Step 1: Select services -->
    <el-card v-if="activeStep === 0" shadow="never" class="step-card">
      <el-alert
        v-if="envStore.currentEnvId"
        :title="`当前环境: ${envStore.currentEnvName}`"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-table
        ref="tableRef"
        :data="sortedServices"
        v-loading="loadingServices"
        stripe
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="服务名称" min-width="160" />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.type === 'go' ? 'success' : 'primary'" size="small">
              {{ typeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="节点数" width="80">
          <template #default="{ row }">{{ row.nodes?.length ?? 0 }}</template>
        </el-table-column>
        <el-table-column prop="upgrade_order" label="升级顺序" width="90" />
        <el-table-column prop="depends_on" label="依赖" width="140">
          <template #default="{ row }">{{ row.depends_on || '-' }}</template>
        </el-table-column>
        <el-table-column prop="deploy_path" label="部署路径" min-width="160" />
      </el-table>

      <div style="margin-top: 20px; text-align: right">
        <el-button type="primary" :disabled="selectedServices.length === 0" @click="activeStep = 1">
          下一步
        </el-button>
      </div>
    </el-card>

    <!-- Step 2: Associate packages -->
    <el-card v-if="activeStep === 1" shadow="never" class="step-card">
      <div v-for="svc in selectedServices" :key="svc.id" class="package-row">
        <div class="package-service-name">
          <el-tag :type="svc.type === 'go' ? 'success' : 'primary'" size="small">
            {{ typeShortLabel(svc.type) }}
          </el-tag>
          <span>{{ svc.name }}</span>
        </div>
        <el-select v-model="packageMap[svc.id]" placeholder="选择升级包（可选）" clearable style="width: 100%">
          <el-option
            v-for="pkg in packagesByService[svc.id] ?? []"
            :key="pkg.id"
            :label="`${pkg.version} (${formatSize(pkg.file_size)})`"
            :value="pkg.id"
          />
        </el-select>
      </div>

      <div style="margin-top: 20px; text-align: right">
        <el-button @click="activeStep = 0">上一步</el-button>
        <el-button type="primary" @click="activeStep = 2">下一步</el-button>
      </div>
    </el-card>

    <!-- Step 3: Confirm -->
    <el-card v-if="activeStep === 2" shadow="never" class="step-card">
      <el-alert
        title="请确认以下升级信息，确认后将创建升级任务"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-form label-width="100px">
        <el-form-item label="任务标题" required>
          <el-input v-model="taskTitle" placeholder="例如: 生产环境 2025-05-25 发版" />
        </el-form-item>
        <el-form-item label="失败策略">
          <el-select v-model="failureStrategy" style="width: 200px">
            <el-option label="遇错停止" value="stop" />
            <el-option label="遇错继续" value="continue" />
            <el-option label="失败回退" value="rollback" />
          </el-select>
        </el-form-item>
        <el-form-item label="步骤超时">
          <el-input-number
            v-model="timeoutSeconds"
            :min="0"
            :max="3600"
            :step="60"
            style="width: 200px"
          />
          <span style="margin-left: 8px; color: #909399; font-size: 13px">
            秒（0 = 不限制，默认 600 秒）
          </span>
        </el-form-item>
      </el-form>

      <el-table :data="summaryData" border style="margin-top: 16px">
        <el-table-column prop="name" label="服务" width="160" />
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === 'go' ? 'success' : 'primary'" size="small">
              {{ typeShortLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="packageVersion" label="升级包版本" width="140" />
        <el-table-column prop="nodes" label="目标节点" min-width="180" />
        <el-table-column prop="dependsOn" label="依赖" width="120" />
        <el-table-column label="步骤数" width="80">
          <template #default="{ row }">
            {{ stepCount(row.type) }} × {{ row.nodeCount }}
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 20px; text-align: right">
        <el-button @click="activeStep = 1">上一步</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建任务</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useEnvironmentStore } from '../stores/environment'
import { fetchServices, fetchServiceTypes, type Service, type ServiceType } from '../api/services'
import { fetchPackages, type UpgradePackage } from '../api/packages'
import { createTask } from '../api/upgrades'

const router = useRouter()
const envStore = useEnvironmentStore()

const activeStep = ref(0)
const loadingServices = ref(false)
const creating = ref(false)
const allServices = ref<Service[]>([])
const serviceTypes = ref<ServiceType[]>([])
const selectedServices = ref<Service[]>([])
const packagesByService = reactive<Record<number, UpgradePackage[]>>({})
const packageMap = reactive<Record<number, number | undefined>>({})
const taskTitle = ref('')
const failureStrategy = ref('stop')
const timeoutSeconds = ref(600)

const sortedServices = computed(() =>
  [...allServices.value].sort((a, b) => a.upgrade_order - b.upgrade_order)
)

const summaryData = computed(() =>
  selectedServices.value.map((svc) => {
    const pkgId = packageMap[svc.id]
    const pkg = pkgId ? packagesByService[svc.id]?.find((p) => p.id === pkgId) : undefined
    return {
      name: svc.name,
      type: svc.type,
      packageVersion: pkg ? pkg.version : '未选择',
      nodes: svc.nodes?.map((n) => n.host_ip).join(', ') ?? '-',
      dependsOn: svc.depends_on || '-',
      nodeCount: svc.nodes?.length ?? 0,
    }
  })
)

function onSelectionChange(rows: Service[]) {
  selectedServices.value = rows
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function typeLabel(type: string): string {
  return serviceTypes.value.find(t => t.name === type)?.label ?? type
}

function typeShortLabel(type: string): string {
  const label = typeLabel(type)
  return label.length > 4 ? label.replace(/[ 一-鿿]+/g, '') : label
}

function stepCount(type: string): number {
  return serviceTypes.value.find(t => t.name === type)?.steps.length ?? 0
}

async function handleCreate() {
  if (!taskTitle.value.trim()) {
    ElMessage.warning('请输入任务标题')
    return
  }
  if (!envStore.currentEnvId) {
    ElMessage.warning('未选择环境')
    return
  }
  creating.value = true
  try {
    const task = await createTask({
      environment_id: envStore.currentEnvId,
      title: taskTitle.value,
      service_ids: selectedServices.value.map((s) => s.id),
      package_ids: Object.values(packageMap).filter((v): v is number => v !== undefined && v !== null),
      failure_strategy: failureStrategy.value,
      timeout_seconds: timeoutSeconds.value > 0 ? timeoutSeconds.value : null,
    })
    ElMessage.success('任务创建成功')
    router.push(`/upgrade/${task.id}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  fetchServiceTypes().then(types => { serviceTypes.value = types }).catch(() => {})
  loadingServices.value = true
  try {
    if (envStore.currentEnvId) {
      allServices.value = await fetchServices(envStore.currentEnvId)
    } else {
      allServices.value = await fetchServices()
    }

    const pkgResults = await Promise.allSettled(
      allServices.value.map((s) => fetchPackages(s.id))
    )
    pkgResults.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        packagesByService[allServices.value[i].id] = r.value
      }
    })
  } finally {
    loadingServices.value = false
  }
})
</script>

<style scoped>
.upgrade-new-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.step-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.package-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.package-row:hover {
  background: #f5f7fa;
}

.package-service-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 200px;
  font-weight: 500;
}
</style>
