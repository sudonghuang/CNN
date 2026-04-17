<template>
  <el-card shadow="never">
    <template #header>
      <span>人脸数据管理</span>
    </template>

    <el-form :inline="true" :model="query" style="margin-bottom:8px">
      <el-form-item label="班级">
        <el-select v-model="query.class_name" placeholder="全部班级" clearable style="width:160px">
          <el-option v-for="c in classes" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>
      <el-form-item label="注册状态">
        <el-select v-model="query.face_registered" placeholder="全部" clearable style="width:120px">
          <el-option label="已注册" :value="true" />
          <el-option label="未注册" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="students" v-loading="loading" stripe>
      <el-table-column prop="student_id" label="学号" width="120" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="class_name" label="班级" width="120" />
      <el-table-column label="人脸状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.face_registered ? 'success' : 'danger'" size="small">
            {{ row.face_registered ? '已注册' : '未注册' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="已采集图片" width="100">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.face_count || 0 }} 张</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button type="primary" link @click="$router.push(`/faces/${row.id}`)">
            {{ row.face_registered ? '管理人脸' : '采集人脸' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top:16px;justify-content:flex-end"
      @current-change="fetchData"
    />
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { studentsApi } from '@/api/students'

const students = ref([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const classes = ref([])
const query = reactive({ class_name: '', face_registered: '' })

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: 20 }
    if (query.class_name) params.class_name = query.class_name
    if (query.face_registered !== '') params.face_registered = query.face_registered
    const res = await studentsApi.list(params)
    students.value = res.data.items
    total.value = res.data.pagination.total
  } finally {
    loading.value = false }
}

async function loadClasses() {
  try {
    const res = await studentsApi.classes()
    classes.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => {
  fetchData()
  loadClasses()
})
</script>
