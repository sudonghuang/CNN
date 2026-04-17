import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  function _persist(t, u) {
    token.value = t
    userInfo.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('userInfo', JSON.stringify(u))
  }

  async function login(credentials) {
    const { data } = await authApi.login(credentials)
    _persist(data.token, data.user)
    // 跳转由调用方负责，避免双重路由竞争
  }

  // 兼容旧调用（login 别名）
  const loginOnly = login

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    // 跳转由路由守卫或调用方负责
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }

  return { token, userInfo, isLoggedIn, login, loginOnly, logout }
})
