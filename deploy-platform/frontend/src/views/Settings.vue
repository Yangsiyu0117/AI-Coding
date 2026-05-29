<template>
  <div class="settings-page">
    <div class="page-header">
      <h2>系统设置</h2>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="settings-tabs">
      <el-tab-pane label="环境管理" name="env">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>环境列表</span>
              <el-button type="primary" size="small" @click="openCreate">创建环境</el-button>
            </div>
          </template>
          <el-table :data="environments" v-loading="loading" stripe border>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="名称" min-width="120" />
            <el-table-column prop="description" label="描述" min-width="200" />
            <el-table-column prop="ssh_default_port" label="SSH 端口" width="100" />
            <el-table-column prop="created_at" label="创建时间" width="180" />
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button link type="warning" size="small" @click="openSSHTest(row)">SSH 测试</el-button>
                <el-popconfirm title="确定删除此环境？该环境下所有服务、节点、升级包和升级任务都将被删除。" @confirm="handleDelete(row)">
                  <template #reference>
                    <el-button link type="danger" size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="用户管理" name="user">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>用户列表</span>
              <el-button type="primary" size="small" @click="openUserCreate">创建用户</el-button>
            </div>
          </template>
          <el-table :data="users" v-loading="userLoading" stripe border>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" min-width="120" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '操作员' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openUserEdit(row)">编辑</el-button>
                <el-popconfirm title="确定删除此用户？" @confirm="handleUserDelete(row)">
                  <template #reference>
                    <el-button link type="danger" size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="服务类型" name="serviceType">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>服务类型列表</span>
              <el-button type="primary" size="small" @click="openTypeCreate">创建类型</el-button>
            </div>
          </template>
          <el-table :data="serviceTypes" v-loading="typeLoading" stripe border>
            <el-table-column prop="name" label="类型名称" width="120" />
            <el-table-column prop="label" label="显示标签" min-width="140" />
            <el-table-column label="步骤数" width="80">
              <template #default="{ row }">
                {{ row.steps.length }}
              </template>
            </el-table-column>
            <el-table-column label="可回退" width="80">
              <template #default="{ row }">
                {{ row.rollbackable.length }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <template v-if="builtinTypes.includes(row.name)">
                  <el-tag type="info" size="small">内置</el-tag>
                </template>
                <template v-else>
                  <el-button link type="primary" size="small" @click="openTypeEdit(row)">编辑</el-button>
                  <el-popconfirm title="确定删除此服务类型？" @confirm="handleTypeDelete(row)">
                    <template #reference>
                      <el-button link type="danger" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="平台设置" name="platform">
        <el-card class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>平台配置</span>
              <el-button type="primary" size="small" :loading="platformSaving" @click="handlePlatformSave">保存设置</el-button>
            </div>
          </template>
          <el-form :model="platformForm" label-width="160px" style="max-width: 600px">
            <el-form-item label="品牌缩写">
              <el-input v-model="platformForm.app_brand" placeholder="如 MyPlatform" />
              <div class="form-tip">显示在页面 Logo 和标题中</div>
            </el-form-item>
            <el-form-item label="平台标题">
              <el-input v-model="platformForm.app_title" placeholder="如 运维升级发布平台" />
            </el-form-item>
            <el-form-item label="远程更新目录">
              <el-input v-model="platformForm.remote_update_base" placeholder="/opt/update" />
              <div class="form-tip">升级包上传到服务器的目标目录</div>
            </el-form-item>
            <el-form-item label="最大上传大小 (MB)">
              <el-input-number v-model="platformForm.max_upload_size_mb" :min="1" :max="10000" />
            </el-form-item>
            <el-form-item label="允许上传的扩展名">
              <el-input v-model="platformForm.allowed_extensions_str" placeholder=".tar.gz, .zip, .tgz" />
              <div class="form-tip">逗号分隔，如 .tar.gz,.zip,.tgz,.gz,.bin</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- Environment Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑环境' : '创建环境'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="SSH 端口">
          <el-input-number v-model="form.ssh_default_port" :min="1" :max="65535" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- User Dialog -->
    <el-dialog
      v-model="userDialogVisible"
      :title="userEditing ? '编辑用户' : '创建用户'"
      width="450px"
      :close-on-click-modal="false"
    >
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="userEditing" />
        </el-form-item>
        <el-form-item label="密码" :prop="userEditing ? '' : 'password'">
          <el-input v-model="userForm.password" type="password" show-password :placeholder="userEditing ? '留空则不修改' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="userSaving" @click="handleUserSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- SSH Test Dialog -->
    <el-dialog v-model="sshDialogVisible" title="SSH 连接测试" width="450px">
      <el-form :model="sshForm" label-width="80px">
        <el-form-item label="主机">
          <el-input v-model="sshForm.host" placeholder="192.168.1.1" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="sshForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户">
          <el-input v-model="sshForm.user" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="sshForm.password" type="password" show-password />
        </el-form-item>
      </el-form>
      <div v-if="sshResult" class="ssh-result">
        <el-alert
          :title="sshResult.message"
          :type="sshResult.success ? 'success' : 'error'"
          :closable="false"
          show-icon
        >
          <template v-if="sshResult.success" #default>
            延迟: {{ sshResult.latency_ms }}ms
          </template>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="sshDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="sshTesting" @click="runSSHTest">测试连接</el-button>
      </template>
    </el-dialog>

    <!-- Service Type Dialog -->
    <el-dialog
      v-model="typeDialogVisible"
      :title="typeEditing ? '编辑服务类型' : '创建服务类型'"
      width="550px"
      :close-on-click-modal="false"
    >
      <el-form ref="typeFormRef" :model="typeForm" :rules="typeRules" label-width="110px">
        <el-form-item label="类型名称" prop="name">
          <el-input v-model="typeForm.name" :disabled="typeEditing" placeholder="如 java、python" />
        </el-form-item>
        <el-form-item label="显示标签" prop="label">
          <el-input v-model="typeForm.label" placeholder="如 Java 应用" />
        </el-form-item>
        <el-form-item label="升级步骤" prop="steps">
          <el-select
            v-model="typeForm.steps"
            multiple
            allow-create
            filterable
            placeholder="选择或输入步骤 key"
            style="width: 100%"
          >
            <el-option
              v-for="s in allStepKeys"
              :key="s"
              :label="stepLabels[s] ? stepLabels[s] + ' (' + s + ')' : s"
              :value="s"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="可回退步骤">
          <el-checkbox-group v-model="typeForm.rollbackable">
            <el-checkbox v-for="s in typeForm.steps" :key="s" :label="s" :value="s">
              {{ stepLabels[s] || s }}
            </el-checkbox>
          </el-checkbox-group>
          <div v-if="typeForm.steps.length === 0" class="form-tip">请先选择升级步骤</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="typeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="typeSaving" @click="handleTypeSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useEnvironmentStore } from '../stores/environment'
import {
  fetchEnvironments,
  createEnvironment,
  updateEnvironment,
  deleteEnvironment,
  testSSH,
  type Environment,
  type SSHTestResult,
} from '../api/environments'
import { fetchUsers, updateUser, deleteUser, type UserInfo } from '../api/users'
import {
  fetchServiceTypes,
  fetchStepLabels,
  createServiceType,
  updateServiceType,
  deleteServiceType,
  type ServiceType,
} from '../api/services'
import { fetchPlatformSettings, savePlatformSettings } from '../api/config'
import client from '../api/client'

const envStore = useEnvironmentStore()
const activeTab = ref('env')

// --- Environment ---
const loading = ref(false)
const saving = ref(false)
const environments = ref<Environment[]>([])
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const rules: FormRules = {
  name: [{ required: true, message: '请输入环境名称' }],
}

const form = reactive({
  name: '',
  description: '',
  ssh_default_port: 22,
})

// --- SSH test ---
const sshDialogVisible = ref(false)
const sshTesting = ref(false)
const sshResult = ref<SSHTestResult | null>(null)
const sshForm = reactive({
  host: '',
  port: 22,
  user: 'root',
  password: '',
})

// --- User ---
const users = ref<UserInfo[]>([])
const userLoading = ref(false)
const userSaving = ref(false)
const userDialogVisible = ref(false)
const userEditing = ref(false)
const userEditingId = ref<number | null>(null)
const userFormRef = ref<FormInstance>()

const userRules: FormRules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码' }],
  role: [{ required: true, message: '请选择角色' }],
}

const userForm = reactive({
  username: '',
  password: '',
  role: 'operator',
})

// --- Service Type ---
const serviceTypes = ref<ServiceType[]>([])
const typeLoading = ref(false)
const typeSaving = ref(false)
const typeDialogVisible = ref(false)
const typeEditing = ref(false)
const typeFormRef = ref<FormInstance>()
const builtinTypes = ['go', 'docker']
const allStepKeys = ref<string[]>([])
const stepLabels = ref<Record<string, string>>({})

const typeRules: FormRules = {
  name: [{ required: true, message: '请输入类型名称' }],
  label: [{ required: true, message: '请输入显示标签' }],
  steps: [{ required: true, message: '请至少选择一个步骤', type: 'array', min: 1 }],
}

const typeForm = reactive({
  name: '',
  label: '',
  steps: [] as string[],
  rollbackable: [] as string[],
})

// --- Platform Settings ---
const platformSaving = ref(false)
const platformForm = reactive({
  app_brand: '',
  app_title: '',
  remote_update_base: '',
  max_upload_size_mb: 500,
  allowed_extensions_str: '',
})

// --- Environment methods ---
function resetForm() {
  form.name = ''
  form.description = ''
  form.ssh_default_port = 22
}

function openCreate() {
  resetForm()
  isEditing.value = false
  editingId.value = null
  dialogVisible.value = true
}

function openEdit(env: Environment) {
  isEditing.value = true
  editingId.value = env.id
  form.name = env.name
  form.description = env.description
  form.ssh_default_port = env.ssh_default_port
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEditing.value && editingId.value !== null) {
      await updateEnvironment(editingId.value, { name: form.name, description: form.description, ssh_default_port: form.ssh_default_port })
      ElMessage.success('更新成功')
    } else {
      await createEnvironment({ name: form.name, description: form.description, ssh_default_port: form.ssh_default_port })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(env: Environment) {
  try {
    await deleteEnvironment(env.id)
    ElMessage.success('已删除')
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

function openSSHTest(env: Environment) {
  sshForm.host = ''
  sshForm.port = env.ssh_default_port
  sshForm.user = 'root'
  sshForm.password = ''
  sshResult.value = null
  sshDialogVisible.value = true
}

async function runSSHTest() {
  if (!sshForm.host) {
    ElMessage.warning('请输入主机地址')
    return
  }
  sshTesting.value = true
  sshResult.value = null
  try {
    sshResult.value = await testSSH({
      host: sshForm.host,
      port: sshForm.port,
      user: sshForm.user,
      password: sshForm.password || undefined,
    })
  } catch (e: any) {
    sshResult.value = { success: false, message: e.response?.data?.detail ?? '测试请求失败', latency_ms: 0 }
  } finally {
    sshTesting.value = false
  }
}

// --- User methods ---
function resetUserForm() {
  userForm.username = ''
  userForm.password = ''
  userForm.role = 'operator'
}

function openUserCreate() {
  resetUserForm()
  userEditing.value = false
  userEditingId.value = null
  userDialogVisible.value = true
}

function openUserEdit(u: UserInfo) {
  userEditing.value = true
  userEditingId.value = u.id
  userForm.username = u.username
  userForm.password = ''
  userForm.role = u.role
  userDialogVisible.value = true
}

async function handleUserSave() {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return

  userSaving.value = true
  try {
    if (userEditing.value && userEditingId.value !== null) {
      const data: Record<string, string> = { role: userForm.role }
      if (userForm.password) data.password = userForm.password
      await updateUser(userEditingId.value, data)
      ElMessage.success('更新成功')
    } else {
      await client.post('/auth/register', {
        username: userForm.username,
        password: userForm.password,
        role: userForm.role,
      })
      ElMessage.success('创建成功')
    }
    userDialogVisible.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    userSaving.value = false
  }
}

async function handleUserDelete(u: UserInfo) {
  try {
    await deleteUser(u.id)
    ElMessage.success('已删除')
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

async function loadUsers() {
  userLoading.value = true
  try {
    users.value = await fetchUsers()
  } finally {
    userLoading.value = false
  }
}

// --- Service Type methods ---
async function loadServiceTypes() {
  typeLoading.value = true
  try {
    serviceTypes.value = await fetchServiceTypes()
  } finally {
    typeLoading.value = false
  }
}

async function loadStepLabels() {
  try {
    stepLabels.value = await fetchStepLabels()
    allStepKeys.value = Object.keys(stepLabels.value)
  } catch {
    allStepKeys.value = []
  }
}

function resetTypeForm() {
  typeForm.name = ''
  typeForm.label = ''
  typeForm.steps = []
  typeForm.rollbackable = []
}

function openTypeCreate() {
  resetTypeForm()
  typeEditing.value = false
  typeDialogVisible.value = true
}

function openTypeEdit(row: ServiceType) {
  typeEditing.value = true
  typeForm.name = row.name
  typeForm.label = row.label
  typeForm.steps = [...row.steps]
  typeForm.rollbackable = [...row.rollbackable]
  typeDialogVisible.value = true
}

async function handleTypeSave() {
  const valid = await typeFormRef.value?.validate().catch(() => false)
  if (!valid) return

  typeSaving.value = true
  try {
    if (typeEditing.value) {
      await updateServiceType(typeForm.name, {
        label: typeForm.label,
        steps: typeForm.steps,
        rollbackable: typeForm.rollbackable,
      })
      ElMessage.success('更新成功')
    } else {
      await createServiceType({
        name: typeForm.name,
        label: typeForm.label,
        steps: typeForm.steps,
        rollbackable: typeForm.rollbackable,
      })
      ElMessage.success('创建成功')
    }
    typeDialogVisible.value = false
    await loadServiceTypes()
    await loadStepLabels()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    typeSaving.value = false
  }
}

async function handleTypeDelete(row: ServiceType) {
  try {
    await deleteServiceType(row.name)
    ElMessage.success('已删除')
    await loadServiceTypes()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

// --- Platform Settings methods ---
async function loadPlatformSettings() {
  try {
    const data = await fetchPlatformSettings()
    platformForm.app_brand = data.app_brand ?? ''
    platformForm.app_title = data.app_title ?? ''
    platformForm.remote_update_base = data.remote_update_base ?? ''
    platformForm.max_upload_size_mb = data.max_upload_size_mb ?? 500
    platformForm.allowed_extensions_str = (data.allowed_upload_extensions ?? []).join(',')
  } catch {
    // leave defaults
  }
}

async function handlePlatformSave() {
  platformSaving.value = true
  try {
    const extensions = platformForm.allowed_extensions_str
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
    await savePlatformSettings({
      app_brand: platformForm.app_brand,
      app_title: platformForm.app_title,
      remote_update_base: platformForm.remote_update_base,
      max_upload_size_mb: platformForm.max_upload_size_mb,
      allowed_upload_extensions: extensions,
    })
    ElMessage.success('设置已保存，部分设置刷新页面后生效')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '保存失败')
  } finally {
    platformSaving.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    environments.value = await fetchEnvironments()
    envStore.environments = environments.value
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
  loadUsers()
  loadServiceTypes()
  loadStepLabels()
  loadPlatformSettings()
})
</script>

<style scoped>
.settings-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.settings-tabs :deep(.el-tabs__header) {
  background: #fafafa;
}

.settings-tabs :deep(.el-tabs__nav) {
  border: none;
}

.section-card {
  border: none;
  box-shadow: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ssh-result {
  margin-top: 12px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
