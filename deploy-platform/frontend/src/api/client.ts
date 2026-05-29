import axios from 'axios'
import { ElMessage } from 'element-plus'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let errorShown = false

function showErrorOnce(msg: string) {
  if (!errorShown) {
    errorShown = true
    ElMessage.error(msg)
    setTimeout(() => { errorShown = false }, 3000)
  }
}

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    if (status === 403) {
      showErrorOnce('权限不足，请联系管理员')
    } else if (status === 404) {
      // Let callers handle 404 themselves
    } else if (status === 429) {
      showErrorOnce(error.response?.data?.detail || '请求过于频繁，请稍后再试')
    } else if (status && status >= 500) {
      showErrorOnce('服务器异常，请稍后重试')
    } else if (!status && error.code === 'ERR_NETWORK') {
      showErrorOnce('网络连接失败，请检查网络')
    } else if (error.code === 'ECONNABORTED') {
      showErrorOnce('请求超时，请稍后重试')
    }

    return Promise.reject(error)
  }
)

export default client
