import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：注入 JWT Token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const code = err.response?.status
    const message = err.response?.data?.message || '网络错误，请重试'
    if (code === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      window.location.href = '/login'
    } else if (code !== 404) {
      ElMessage.error(message)
    }
    return Promise.reject(err)
  }
)

export default request
