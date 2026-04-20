import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const code = err.response?.status
    const message = err.response?.data?.message || '网络错误，请重试'

    if (code === 401) {
      if (!err.config?.silent) {
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
        window.location.href = '/login'
      }
    } else if (code === 403) {
      // silent 请求（如仪表盘后台探针）不弹权限提示
      if (!err.config?.silent) {
        ElMessage.warning('权限不足')
      }
    } else if (code === 404) {
      // 静默忽略
    } else if (code >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else if (code) {
      ElMessage.error(message)
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(err)
  }
)

export default request
