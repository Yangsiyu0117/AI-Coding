<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-brand">
        <div class="login-logo">{{ appBrand }}</div>
        <h2>{{ appTitle }}</h2>
        <p class="login-subtitle">Deployment Management Platform</p>
      </div>
      <el-form @submit.prevent>
        <el-form-item>
          <el-input
            v-model="username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="loading" @click="handleLogin" style="width: 100%">
          登 录
        </el-button>
      </el-form>
    </div>
    <p class="login-footer">{{ appBrand }} Platform {{ appVersion }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { fetchAppConfig } from '../api/config'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const appBrand = ref('')
const appTitle = ref('运维升级发布平台')
const appVersion = ref('v1.0')

onMounted(async () => {
  try {
    const cfg = await fetchAppConfig()
    appBrand.value = cfg.app_brand
    appTitle.value = cfg.app_title
    appVersion.value = 'v' + cfg.version
  } catch { /* use defaults */ }
})

async function handleLogin() {
  loading.value = true
  try {
    const res = await login(username.value, password.value)
    authStore.setAuth(res.data.access_token, res.data.username, res.data.role)
    router.push('/')
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #1d2b3a 0%, #304156 50%, #409eff 150%);
}

.login-card {
  width: 420px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  padding: 36px 40px;
  animation: login-in 0.5s ease-out;
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

.login-brand h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

.login-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #909399;
  letter-spacing: 0.5px;
}

.login-footer {
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
}

@keyframes login-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
