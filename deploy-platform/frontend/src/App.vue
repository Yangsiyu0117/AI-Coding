<template>
  <div v-if="isLoginPage" class="login-layout">
    <router-view />
  </div>
  <el-container v-else class="app-container">
    <el-aside width="220px" class="app-aside">
      <div class="logo">
        <span class="logo-dot" />
        <span>{{ appBrand }} Deploy</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="transparent"
        text-color="#bfcbd9"
        active-text-color="#fff"
      >
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/services">
          <el-icon><SetUp /></el-icon>
          <span>服务管理</span>
        </el-menu-item>
        <el-menu-item index="/packages">
          <el-icon><FolderOpened /></el-icon>
          <span>升级包</span>
        </el-menu-item>
        <el-menu-item index="/upgrade/new">
          <el-icon><Upload /></el-icon>
          <span>新建升级</span>
        </el-menu-item>
        <el-menu-item index="/upgrades">
          <el-icon><Clock /></el-icon>
          <span>升级历史</span>
        </el-menu-item>
        <el-menu-item index="/patrol">
          <el-icon><Search /></el-icon>
          <span>状态巡检</span>
        </el-menu-item>
        <el-menu-item index="/audit">
          <el-icon><Document /></el-icon>
          <span>操作审计</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Tools /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <EnvSelector />
      </div>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <span class="header-title">{{ appTitle }}</span>
        <div class="header-right">
          <el-tag size="small" :type="authStore.role === 'admin' ? 'danger' : 'info'">
            {{ authStore.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
          <span class="username">{{ authStore.username }}</span>
          <el-button text type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Clock, Document, FolderOpened, Monitor, Search, SetUp, Tools, Upload } from '@element-plus/icons-vue'
import { useAuthStore } from './stores/auth'
import { fetchAppConfig } from './api/config'
import EnvSelector from './components/EnvSelector.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const appBrand = ref('')
const appTitle = ref('运维升级发布平台')

onMounted(async () => {
  try {
    const cfg = await fetchAppConfig()
    appBrand.value = cfg.app_brand
    appTitle.value = cfg.app_title
  } catch { /* use defaults */ }
})

const isLoginPage = computed(() => route.path === '/login')
const activeMenu = computed(() => route.path)

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>

<style scoped>
.login-layout {
  width: 100vw;
  height: 100vh;
}

.app-container {
  height: 100vh;
}

.app-aside {
  background: linear-gradient(180deg, #1d2b3a 0%, #263445 40%, #304156 100%);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.08);
}

.app-aside .logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409eff;
  box-shadow: 0 0 6px rgba(64, 158, 255, 0.6);
}

.app-aside :deep(.el-menu) {
  border-right: none;
}

.app-aside :deep(.el-menu-item) {
  transition: background-color 0.2s, color 0.2s;
}

.app-aside :deep(.el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.06) !important;
}

.app-aside :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(64, 158, 255, 0.15), transparent) !important;
  border-left: 3px solid #409eff;
  padding-left: 17px !important;
}

.aside-footer {
  margin-top: auto;
  padding: 12px;
}

.app-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  position: relative;
  z-index: 10;
}

.header-title {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: #606266;
}

.app-main {
  background: #f5f7fa;
  padding: 24px;
}
</style>
