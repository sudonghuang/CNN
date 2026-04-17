<template>
  <el-card shadow="never">
    <el-form :inline="true" :model="query">
      <el-form-item label="状态">
        <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
          <el-option label="待开始" value="pending" />
          <el-option label="进行中" value="running" />
          <el-option label="已结束" value="finished" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
        <el-button type="success" :icon="Plus" @click="showCreate = true">发起考勤</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="tasks" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="task_date" label="日期" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="{ pending:'info', running:'warning', finished:'success' }[row.status]">
            {{ { pending:'待开始', running:'进行中', finished:'已结束' }[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="出勤" width="120">
        <template #default="{ row }">
          {{ row.present_count }} / {{ row.total_students }}
          <span style="color:#909399;font-size:12px">
            ({{ row.total_students ? (row.present_count/row.total_students*100).toFixed(1) : 0 }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="primary"
            @click="$router.push(`/attendance/tasks/${row.id}`)">开始</el-button>
          <el-button v-if="row.status === 'running'" link type="warning"
            @click="$router.push(`/attendance/tasks/${row.id}`)">监控</el-button>
          <el-button link @click="viewDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" :total="total" layout="total, prev, pager, next"
      style="margin-top:16px;justify-content:flex-end" @current-change="fetchData" />

    <!-- 新建考勤弹窗 -->
    <el-dialog v-model="showCreate" title="发起考勤" width="400px" @open="loadCourses">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="课程">
          <el-select v-model="createForm.course_id" placeholder="请选择课程" style="width:100%">
            <el-option v-for="c in courses" :key="c.id" :label="c.course_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="考勤日期">
          <el-date-picker v-model="createForm.task_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { attendanceApi } from '@/api/attendance'
import { coursesApi } from '@/api/courses'

const tasks = ref([]), loading = ref(false), page = ref(1), total = ref(0)
const query = reactive({ status: '' })
const showCreate = ref(false)
const courses = ref([])
const createForm = reactive({ course_id: null, task_date: new Date().toISOString().slice(0,10) })

async function fetchData() {
  loading.value = true
  try {
    const res = await attendanceApi.listTasks({ page: page.value, per_page: 20, ...query })
    tasks.value = res.data.items; total.value = res.data.pagination.total
  } finally { loading.value = false }
}

async function loadCourses() {
  try {
    const res = await coursesApi.list({ per_page: 100 })
    courses.value = res.data?.items || []
  } catch { /* ignore */ }
}

async function handleCreate() {
  if (!createForm.course_id) return ElMessage.warning('请选择课程')
  await attendanceApi.createTask(createForm)
  ElMessage.success('考勤任务已创建')
  showCreate.value = false; fetchData()
}

function viewDetail(row) { /* TODO: 弹出详情抽屉 */ }

onMounted(fetchData)
</script>
