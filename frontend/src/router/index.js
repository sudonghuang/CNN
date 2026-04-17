import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '数据概览' },
      },
      // 学生管理
      {
        path: 'students',
        name: 'StudentList',
        component: () => import('@/views/students/StudentList.vue'),
        meta: { title: '学生列表', roles: ['admin', 'teacher', 'counselor'] },
      },
      {
        path: 'students/create',
        name: 'StudentCreate',
        component: () => import('@/views/students/StudentForm.vue'),
        meta: { title: '新增学生', roles: ['admin', 'counselor'] },
      },
      {
        path: 'students/:id/edit',
        name: 'StudentEdit',
        component: () => import('@/views/students/StudentForm.vue'),
        meta: { title: '编辑学生', roles: ['admin', 'counselor'] },
      },
      // 人脸数据
      {
        path: 'faces',
        name: 'FaceList',
        component: () => import('@/views/faces/FaceList.vue'),
        meta: { title: '人脸数据管理', roles: ['admin'] },
      },
      {
        path: 'faces/:studentId',
        name: 'FaceCapture',
        component: () => import('@/views/faces/FaceCapture.vue'),
        meta: { title: '人脸采集', roles: ['admin'] },
      },
      // 考勤
      {
        path: 'attendance/tasks',
        name: 'AttendanceList',
        component: () => import('@/views/attendance/AttendanceList.vue'),
        meta: { title: '考勤任务' },
      },
      {
        path: 'attendance/tasks/:id',
        name: 'AttendanceTask',
        component: () => import('@/views/attendance/AttendanceTask.vue'),
        meta: { title: '实时考勤', roles: ['admin', 'teacher'] },
      },
      // 报表
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportPage.vue'),
        meta: { title: '报表统计' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/** 检查 JWT 是否已过期（不需要请求后端，直接解析 payload） */
function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

router.beforeEach((to) => {
  const auth = useAuthStore()
  const token = auth.token

  // token 存在但已过期 → 清除并跳登录
  if (token && isTokenExpired(token)) {
    auth.logout()
    if (!to.meta.public) {
      return { name: 'Login', query: { redirect: to.fullPath } }
    }
  }

  // 未登录 → 跳登录
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // 已登录但访问 /login → 跳首页
  if (to.name === 'Login' && auth.isLoggedIn) {
    return { path: '/dashboard' }
  }

  // 角色权限不足 → 跳首页
  if (to.meta.roles && !to.meta.roles.includes(auth.userInfo?.role)) {
    return { path: '/dashboard' }
  }
})

export default router
