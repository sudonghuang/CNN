import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      // 学生管理
      { path: 'students', name: 'StudentList', component: () => import('@/views/students/StudentList.vue'), meta: { roles: ['admin', 'teacher', 'counselor'] } },
      { path: 'students/create', name: 'StudentCreate', component: () => import('@/views/students/StudentForm.vue'), meta: { roles: ['admin'] } },
      { path: 'students/:id/edit', name: 'StudentEdit', component: () => import('@/views/students/StudentForm.vue'), meta: { roles: ['admin'] } },
      // 人脸数据
      { path: 'faces/:studentId', name: 'FaceCapture', component: () => import('@/views/faces/FaceCapture.vue'), meta: { roles: ['admin'] } },
      // 考勤
      { path: 'attendance/tasks', name: 'AttendanceList', component: () => import('@/views/attendance/AttendanceList.vue') },
      { path: 'attendance/tasks/:id', name: 'AttendanceTask', component: () => import('@/views/attendance/AttendanceTask.vue'), meta: { roles: ['admin', 'teacher'] } },
      // 报表
      { path: 'reports', name: 'Reports', component: () => import('@/views/reports/ReportPage.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.meta.roles && !to.meta.roles.includes(auth.userInfo?.role)) {
    return { path: '/dashboard' }
  }
})

export default router
