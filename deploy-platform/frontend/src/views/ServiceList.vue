<template>
  <div class="service-list-page">
    <div class="page-header">
      <h2>服务管理</h2>
      <div>
        <el-button type="primary" @click="openCreate">创建服务</el-button>
        <el-button @click="openImport">批量导入</el-button>
      </div>
    </div>

    <el-card shadow="never" class="content-card">
    <div class="filter-bar">
      <el-select v-model="filterEnvId" placeholder="按环境筛选" clearable @change="fetchData">
        <el-option label="全部环境" :value="undefined" />
        <el-option v-for="env in envStore.environments" :key="env.id" :label="env.name" :value="env.id" />
      </el-select>
      <el-select v-model="filterType" placeholder="按类型筛选" clearable>
        <el-option label="全部类型" value="" />
        <el-option v-for="t in serviceTypes" :key="t.name" :label="t.label" :value="t.name" />
      </el-select>
    </div>

    <el-table v-if="filteredServices.length > 0" :data="filteredServices" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag :type="row.type === 'go' ? 'success' : 'primary'" size="small">
            {{ typeLabel(row.type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="环境" width="100">
        <template #default="{ row }">
          {{ envName(row.environment_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="deploy_path" label="部署路径" min-width="180" />
      <el-table-column label="节点数" width="80">
        <template #default="{ row }">
          {{ row.nodes?.length ?? 0 }}
        </template>
      </el-table-column>
      <el-table-column prop="upgrade_order" label="升级顺序" width="90" />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除此服务及所有节点？关联的升级包和任务也将被删除。" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" description="暂无服务，请先创建环境后添加服务">
      <el-button type="primary" @click="openCreate">创建服务</el-button>
    </el-empty>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑服务' : '创建服务'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="环境" prop="environment_id">
          <el-select v-model="form.environment_id" placeholder="选择环境">
            <el-option v-for="env in envStore.environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务名称" prop="name">
          <el-input v-model="form.name" placeholder="例如 my-service" />
        </el-form-item>
        <el-form-item label="服务类型" prop="type">
          <el-select v-model="form.type">
            <el-option v-for="t in serviceTypes" :key="t.name" :label="t.label" :value="t.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署路径">
          <el-input v-model="form.deploy_path" placeholder="例如 /opt/my-service" />
        </el-form-item>
        <el-form-item label="运行脚本">
          <el-input v-model="form.run_script" placeholder="默认 run.sh" />
        </el-form-item>
        <el-form-item label="启动命令">
          <el-input v-model="form.start_cmd" placeholder="例如 sh run.sh {old_ver} {new_ver}" />
        </el-form-item>
        <el-form-item label="停止命令">
          <el-input v-model="form.stop_cmd" placeholder="例如 cd /opt/svc && sh run.sh stop" />
        </el-form-item>
        <el-form-item label="检查命令">
          <el-input v-model="form.check_cmd" placeholder='例如 docker ps | grep my-service' />
        </el-form-item>
        <el-form-item label="版本命令">
          <el-input v-model="form.version_cmd" placeholder="例如 /opt/svc/bin -v" />
        </el-form-item>
        <el-form-item label="备份模式">
          <el-input v-model="form.backup_pattern" placeholder="例如 my-service.bak" />
        </el-form-item>
        <el-form-item label="升级顺序">
          <el-input-number v-model="form.upgrade_order" :min="0" />
        </el-form-item>
        <el-form-item label="依赖服务">
          <el-input v-model="form.depends_on" placeholder="填写服务名称，多个用逗号分隔" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="服务功能描述（可选）" />
        </el-form-item>
      </el-form>

      <!-- Node management sub-section -->
      <el-divider content-position="left">节点管理</el-divider>
      <el-table :data="form.nodes" border size="small">
        <el-table-column label="主机IP" min-width="140">
          <template #default="{ $index }">
            <el-input v-model="form.nodes[$index].host_ip" size="small" placeholder="192.168.1.1" />
          </template>
        </el-table-column>
        <el-table-column label="SSH 端口" width="100">
          <template #default="{ $index }">
            <el-input-number v-model="form.nodes[$index].ssh_port" :min="1" :max="65535" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="SSH 用户" width="100">
          <template #default="{ $index }">
            <el-input v-model="form.nodes[$index].ssh_user" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="SSH 密码" width="130">
          <template #default="{ $index }">
            <el-input v-model="form.nodes[$index].ssh_password" type="password" show-password size="small" />
          </template>
        </el-table-column>
        <el-table-column label="连接测试" width="90">
          <template #default="{ $index }">
            <el-button
              link
              type="warning"
              size="small"
              :loading="testingNodeIndex === $index"
              @click="handleTestSSH($index)"
            >
              测试连接
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="form.nodes.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-button style="margin-top: 8px" size="small" @click="addNode">+ 添加节点</el-button>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Batch Import Dialog -->
    <el-dialog
      v-model="importDialogVisible"
      title="批量导入服务"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="importJson"
        type="textarea"
        rows="15"
        placeholder='[
  {
    "environment_id": 1,
    "name": "my-service",
    "type": "go",
    "deploy_path": "/opt/my-service",
    "run_script": "run.sh",
    "start_cmd": "",
    "stop_cmd": "",
    "check_cmd": "",
    "nodes": [
      {"host_ip": "192.168.1.1", "ssh_port": 22, "ssh_user": "root", "ssh_password": ""}
    ]
  }
]'
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useEnvironmentStore } from '../stores/environment'
import {
  fetchServices,
  createService,
  updateService,
  deleteService,
  addServiceNode,
  updateServiceNode,
  deleteServiceNode,
  importServices,
  fetchServiceTypes,
  type Service,
  type ServiceType,
} from '../api/services'
import { testSSH } from '../api/environments'

const envStore = useEnvironmentStore()
const loading = ref(false)
const saving = ref(false)
const services = ref<Service[]>([])
const serviceTypes = ref<ServiceType[]>([])
const filterEnvId = ref<number | undefined>()
const filterType = ref('')
const dialogVisible = ref(false)
const testingNodeIndex = ref<number | null>(null)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const importDialogVisible = ref(false)
const importJson = ref('')
const importing = ref(false)

const rules: FormRules = {
  environment_id: [{ required: true, message: '请选择环境' }],
  name: [{ required: true, message: '请输入服务名称' }],
  type: [{ required: true, message: '请选择服务类型' }],
}

interface NodeForm {
  id?: number
  host_ip: string
  ssh_port: number
  ssh_user: string
  ssh_password: string
}

const form = reactive({
  environment_id: undefined as number | undefined,
  name: '',
  type: 'go',
  deploy_path: '',
  run_script: 'run.sh',
  start_cmd: '',
  stop_cmd: '',
  check_cmd: '',
  version_cmd: '',
  backup_pattern: '',
  upgrade_order: 0,
  depends_on: '',
  description: '',
  nodes: [] as NodeForm[],
})

function envName(envId: number) {
  return envStore.environments.find((e) => e.id === envId)?.name ?? `#${envId}`
}

function typeLabel(type: string): string {
  return serviceTypes.value.find(t => t.name === type)?.label ?? type
}

const filteredServices = computed(() => {
  let list = services.value
  if (filterEnvId.value !== undefined) {
    list = list.filter((s) => s.environment_id === filterEnvId.value)
  }
  if (filterType.value) {
    list = list.filter((s) => s.type === filterType.value)
  }
  return list
})

async function fetchData() {
  loading.value = true
  try {
    services.value = await fetchServices()
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.environment_id = undefined
  form.name = ''
  form.type = 'go'
  form.deploy_path = ''
  form.run_script = 'run.sh'
  form.start_cmd = ''
  form.stop_cmd = ''
  form.check_cmd = ''
  form.version_cmd = ''
  form.backup_pattern = ''
  form.upgrade_order = 0
  form.depends_on = ''
  form.description = ''
  form.nodes = []
}

function addNode() {
  form.nodes.push({ host_ip: '', ssh_port: 22, ssh_user: 'root', ssh_password: '' })
}

async function handleTestSSH(index: number) {
  const node = form.nodes[index]
  if (!node.host_ip) {
    ElMessage.warning('请先填写主机IP')
    return
  }
  testingNodeIndex.value = index
  try {
    const result = await testSSH({
      host: node.host_ip,
      port: node.ssh_port,
      user: node.ssh_user,
      password: node.ssh_password || undefined,
    })
    if (result.success) {
      ElMessage.success(`连接成功 (${result.latency_ms}ms)`)
    } else {
      ElMessage.error(`连接失败: ${result.message}`)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '连接测试失败')
  } finally {
    testingNodeIndex.value = null
  }
}

function openCreate() {
  resetForm()
  isEditing.value = false
  editingId.value = null
  dialogVisible.value = true
}

function openEdit(service: Service) {
  isEditing.value = true
  editingId.value = service.id
  form.environment_id = service.environment_id
  form.name = service.name
  form.type = service.type
  form.deploy_path = service.deploy_path
  form.run_script = service.run_script
  form.start_cmd = service.start_cmd
  form.stop_cmd = service.stop_cmd
  form.check_cmd = service.check_cmd
  form.version_cmd = service.version_cmd
  form.backup_pattern = service.backup_pattern
  form.upgrade_order = service.upgrade_order
  form.depends_on = service.depends_on
  form.description = service.description
  form.nodes = service.nodes.map((n) => ({
    id: n.id,
    host_ip: n.host_ip,
    ssh_port: n.ssh_port,
    ssh_user: n.ssh_user,
    ssh_password: '',
  }))
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      environment_id: form.environment_id!,
      name: form.name,
      type: form.type,
      deploy_path: form.deploy_path,
      run_script: form.run_script,
      start_cmd: form.start_cmd,
      stop_cmd: form.stop_cmd,
      check_cmd: form.check_cmd,
      version_cmd: form.version_cmd,
      backup_pattern: form.backup_pattern,
      upgrade_order: form.upgrade_order,
      depends_on: form.depends_on,
      description: form.description,
      nodes: form.nodes.map((n) => ({ host_ip: n.host_ip, ssh_port: n.ssh_port, ssh_user: n.ssh_user, ssh_password: n.ssh_password })),
    }

    if (isEditing.value && editingId.value !== null) {
      // Update service scalar fields
      const { nodes: _, ...scalars } = payload
      await updateService(editingId.value, scalars)
      // Sync nodes: delete removed nodes, add new ones, update existing
      const existingIds = new Set(form.nodes.filter((n) => n.id).map((n) => n.id!))
      const existingService = services.value.find((s) => s.id === editingId.value)
      if (existingService) {
        // Delete removed nodes
        for (const node of existingService.nodes) {
          if (!existingIds.has(node.id)) {
            await deleteServiceNode(editingId.value, node.id)
          }
        }
        // Add new nodes (no id)
        for (const node of form.nodes) {
          if (!node.id) {
            await addServiceNode(editingId.value, { host_ip: node.host_ip, ssh_port: node.ssh_port, ssh_user: node.ssh_user, ssh_password: node.ssh_password })
          } else {
            await updateServiceNode(editingId.value, node.id, { host_ip: node.host_ip, ssh_port: node.ssh_port, ssh_user: node.ssh_user, ssh_password: node.ssh_password })
          }
        }
      }
    } else {
      await createService(payload)
    }
    ElMessage.success(isEditing.value ? '更新成功' : '创建成功')
    dialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(service: Service) {
  try {
    await deleteService(service.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

function openImport() {
  importJson.value = ''
  importDialogVisible.value = true
}

async function handleImport() {
  const text = importJson.value.trim()
  if (!text) {
    ElMessage.warning('请输入服务列表 JSON')
    return
  }

  let data: any[]
  try {
    data = JSON.parse(text)
  } catch {
    ElMessage.error('JSON 格式错误，请检查')
    return
  }

  if (!Array.isArray(data)) {
    ElMessage.error('JSON 必须是一个数组')
    return
  }

  importing.value = true
  try {
    const result = await importServices(data)
    ElMessage.success(`成功导入 ${result.length} 个服务`)
    importDialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  if (envStore.environments.length === 0) {
    await envStore.loadEnvironments()
  }
  await Promise.all([
    fetchData(),
    fetchServiceTypes().then(types => { serviceTypes.value = types }).catch(),
  ])
})
</script>

<style scoped>
.service-list-page {
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
