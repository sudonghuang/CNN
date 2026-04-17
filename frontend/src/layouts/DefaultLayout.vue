<template>
  <el-container class="layout-wrapper">
    <el-aside width="220px" class="sidebar">
      <div class="logo">智能考勤系统</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon><span>数据概览</span>
        </el-menu-item>

        <el-sub-menu v-if="hasRole(['admin','teacher','counselor'])" index="students">
          <template #title><el-icon><User /></el-icon><span>学生管理</span></template>
          <el-menu-item index="/students">学生列表</el-menu-item>
          <el-menu-item v-if="hasRole(['admin'])" index="/students/create">新增学生</el-menu-item>
        </el-sub-menu>

        <el-menu-item v-if="hasRole(['admin'])" index="/faces">
          <el-icon><Camera /></el-icon><span>人脸数据管理</span>
        </el-menu-item>

        <el-sub-menu index="attendance">
          <template #title><el-icon><Checked /></el-icon><span>考勤管理</span></template>
          <el-menu-item index="/attendance/tasks">考勤任务</el-menu-item>
        </el-sub-menu>

        <el-menu-item v-if="hasRole(['admin','teacher','counselor'])" index="/reports">
          <el-icon><TrendCharts /></el-icon><span>报表统计</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="breadcrumb">{{ $route.meta.title || '首页' }}</span>
        <div class="user-info">
          <span>{{ auth.userInfo?.real_name }}</span>
          <el-tag size="small" type="info" style="margin: 0 12px">{{ roleLabel }}</el-tag>
          <el-button link @click="auth.logout()">退出</el-button>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const ROLE_MAP = { admin: '管理员', teacher: '教师', counselor: '辅导员', student: '学生' }
const roleLabel = computed(() => ROLE_MAP[auth.userInfo?.role] || '')
const hasRole = (roles) => roles.includes(auth.userInfo?.role)
</script>

<style scoped>
.layout-wrapper { height: 100vh; }
.sidebar { background: #001529; overflow: hidden; }
.logo { color: #fff; font-size: 16px; font-weight: 600; padding: 20px 24px; border-bottom: 1px solid #ffffff1a; }
.header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #f0f0f0; box-shadow: 0 1px 4px rgba(0,21,41,.08); }
.user-info { display: flex; align-items: center; }
.main-content { background: #f5f7fa; padding: 20px; overflow-y: auto; }
</style>
