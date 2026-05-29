<template>
  <div class="package-list-page">
    <div class="page-header">
      <h2>升级包管理</h2>
      <el-button type="primary" @click="openUpload">上传升级包</el-button>
    </div>

    <el-card shadow="never" class="content-card">
    <div class="filter-bar">
      <el-select v-model="filterServiceId" placeholder="按服务筛选" clearable @change="fetchData">
        <el-option label="全部服务" :value="undefined" />
        <el-option v-for="svc in services" :key="svc.id" :label="svc.name" :value="svc.id" />
      </el-select>
    </div>

    <el-table v-if="filteredPackages.length > 0" :data="filteredPackages" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="service_name" label="服务名称" min-width="140" />
      <el-table-column prop="version" label="版本" min-width="100" />
      <el-table-column label="文件大小" width="110">
        <template #default="{ row }">
          {{ formatFileSize(row.file_size) }}
        </template>
      </el-table-column>
      <el-table-column prop="file_md5" label="MD5" min-width="220" show-overflow-tooltip />
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">
          {{ row.created_at ? new Date(row.created_at).toLocaleString() : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-popconfirm title="确定删除此升级包及其文件？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" description="暂无升级包，请先上传升级包" />
    </el-card>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="dialogVisible"
      title="上传升级包"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="uploadForm" :rules="rules" label-width="90px">
        <el-form-item label="服务" prop="service_id">
          <el-select v-model="uploadForm.service_id" placeholder="选择服务" filterable>
            <el-option v-for="svc in services" :key="svc.id" :label="`${svc.name} (${typeShortLabel(svc.type)})`" :value="svc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号" prop="version">
          <el-input v-model="uploadForm.version" placeholder="例如 1.0.0" />
        </el-form-item>
        <el-form-item label="升级包文件" prop="file">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :before-upload="beforeUpload"
            :accept="uploadConfig.allowed_extensions.join(',')"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 {{ uploadConfig.allowed_extensions.join(' / ') }}，或无后缀二进制文件，最大 {{ uploadConfig.max_upload_size_mb }}MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">确认上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { FormInstance, FormRules, UploadFile, UploadRawFile } from 'element-plus'
import { fetchPackages, uploadPackage, deletePackage, type UpgradePackage } from '../api/packages'
import { fetchServices, fetchServiceTypes, type Service, type ServiceType } from '../api/services'
import { fetchUploadConfig, type UploadConfig } from '../api/config'

const loading = ref(false)
const uploading = ref(false)
const packages = ref<UpgradePackage[]>([])
const services = ref<Service[]>([])
const serviceTypes = ref<ServiceType[]>([])
const filterServiceId = ref<number | undefined>()
const uploadConfig = ref<UploadConfig>({ max_upload_size_mb: 500, allowed_extensions: ['.tar.gz', '.zip', '.tgz', '.gz', '.bin'] })

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const uploadRef = ref()

const uploadForm = reactive({
  service_id: undefined as number | undefined,
  version: '',
  file: null as UploadFile | null,
})

const rules: FormRules = {
  service_id: [{ required: true, message: '请选择服务' }],
  version: [{ required: true, message: '请输入版本号' }],
}

const filteredPackages = computed(() => {
  if (filterServiceId.value === undefined) return packages.value
  return packages.value.filter((p) => p.service_id === filterServiceId.value)
})

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

function handleFileChange(file: UploadFile) {
  uploadForm.file = file
}

function handleFileRemove() {
  uploadForm.file = null
}

function beforeUpload(file: UploadRawFile) {
  const lower = file.name.toLowerCase()
  // Allow files without extension (e.g. Go binaries)
  if (!lower.includes('.')) return true
  const allowed = uploadConfig.value.allowed_extensions
  const ok = allowed.some((ext) => lower.endsWith(ext))
  if (!ok) {
    const extText = allowed.join(', ') + ', 或无后缀的二进制文件'
    ElMessage.error(`不支持的文件类型，允许: ${extText}`)
    return false
  }
  return true
}

async function fetchData() {
  loading.value = true
  try {
    packages.value = await fetchPackages()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '加载失败')
  } finally {
    loading.value = false
  }
}

function typeShortLabel(type: string): string {
  return serviceTypes.value.find(t => t.name === type)?.label ?? type
}

async function fetchServicesList() {
  try {
    services.value = await fetchServices()
  } catch {
    // ignore
  }
}

function openUpload() {
  uploadForm.service_id = undefined
  uploadForm.version = ''
  uploadForm.file = null
  if (uploadRef.value) uploadRef.value.clearFiles()
  dialogVisible.value = true
}

async function handleUpload() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!uploadForm.file?.raw) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('service_id', String(uploadForm.service_id))
    fd.append('version', uploadForm.version)
    fd.append('file', uploadForm.file.raw)

    await uploadPackage(fd)
    ElMessage.success('上传成功')
    dialogVisible.value = false
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '上传失败')
  } finally {
    uploading.value = false
  }
}

async function handleDelete(pkg: UpgradePackage) {
  try {
    await deletePackage(pkg.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail ?? '删除失败')
  }
}

onMounted(async () => {
  await Promise.all([
    fetchData(),
    fetchServicesList(),
    fetchUploadConfig().then(c => { uploadConfig.value = c }).catch(),
    fetchServiceTypes().then(types => { serviceTypes.value = types }).catch(),
  ])
})
</script>

<style scoped>
.package-list-page {
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
