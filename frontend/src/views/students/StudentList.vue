<template>
  <el-card shadow="never">
    <!-- 搜索栏 -->
    <el-form :inline="true" :model="query" @submit.prevent="fetchData">
      <el-form-item label="姓名">
        <el-input v-model="query.name" placeholder="搜索姓名" clearable style="width:160px" />
      </el-form-item>
      <el-form-item label="班级">
        <el-select v-model="query.class_name" placeholder="全部班级" clearable style="width:160px">
          <el-option v-for="c in classes" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>
      <el-form-item label="人脸状态">
        <el-select v-model="query.face_registered" placeholder="全部" clearable style="width:120px">
          <el-option label="已注册" :value="true" /><el-option label="未注册" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </el-form-item>
      <el-form-item style="float:right">
        <el-button type="primary" :icon="Plus" @click="$router.push('/students/create')">新增</el-button>
        <el-upload :show-file-list="false" accept=".xlsx,.xls" :before-upload="handleImport">
          <el-button :icon="Upload">批量导入</el-button>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-table :data="students" v-loading="loading" stripe>
      <el-table-column prop="student_id" label="学号" width="130" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="class_name" label="班级" />
      <el-table-column prop="department" label="院系" />
      <el-table-column label="人脸状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.face_registered ? 'success' : 'warning'" size="small">
            {{ row.face_registered ? `已注册(${row.face_count}张)` : '未注册' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/students/${row.id}/edit`)">编辑</el-button>
          <el-button link type="primary" @click="$router.push(`/faces/${row.id}`)">人脸</el-button>
          <el-popconfirm title="确认删除该学生？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page" v-model:page-size="perPage"
      :total="total" layout="total, sizes, prev, pager, next"
      :page-sizes="[10,20,50]" style="margin-top:16px;justify-content:flex-end"
      @change="fetchData" />
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { studentsApi } from '@/api/students'

const students = ref([]), classes = ref([]), loading = ref(false)
const page = ref(1), perPage = ref(20), total = ref(0)
const query = reactive({ name: '', class_name: '', face_registered: undefined })

async function fetchData() {
  loading.value = true
  try {
    const res = await studentsApi.list({ page: page.value, per_page: perPage.value, ...query })
    students.value = res.data.items
    total.value = res.data.pagination.total
  } finally { loading.value = false }
}

async function handleDelete(id) {
  await studentsApi.remove(id)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleImport(file) {
  const res = await studentsApi.importExcel(file)
  ElMessage.success(`导入成功 ${res.data.success} 条，失败 ${res.data.failed} 条`)
  fetchData()
  return false
}

function resetQuery() { Object.assign(query, { name: '', class_name: '', face_registered: undefined }); fetchData() }

onMounted(async () => {
  const res = await studentsApi.classes()
  classes.value = res.data || []
  fetchData()
})
</script>
