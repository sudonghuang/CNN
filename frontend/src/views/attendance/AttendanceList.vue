<template>
  <el-card shadow="never">
    <el-form :inline="true" :model="query">
      <el-form-item label="课程">
        <el-select v-model="query.course_id" placeholder="全部课程" clearable style="width:160px">
          <el-option v-for="c in courses" :key="c.id" :label="c.course_name" :value="c.id" />
        </el-select>
      </el-form-item>
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
      <el-table-column label="课程" min-width="140">
        <template #default="{ row }">
          {{ courseMap[row.course_id] || `课程#${row.course_id}` }}
        </template>
      </el-table-column>
      <el-table-column prop="task_date" label="日期" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="{ pending:'info', running:'warning', finished:'success' }[row.status]">
            {{ { pending:'待开始', running:'进行中', finished:'已结束' }[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="出勤" width="140">
        <template #default="{ row }">
          <span style="font-weight:500">{{ row.present_count }}</span>
          <span style="color:#909399"> / {{ row.total_students }}</span>
          <span style="color:#909399;font-size:12px;margin-left:4px">
            ({{ row.total_students ? (row.present_count / row.total_students * 100).toFixed(1) : 0 }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canOperate && row.status === 'pending'" link type="primary"
            @click="$router.push(`/attendance/tasks/${row.id}`)">开始</el-button>
          <el-button v-if="canOperate && row.status === 'running'" link type="warning"
            @click="$router.push(`/attendance/tasks/${row.id}`)">监控</el-button>
          <el-button link @click="viewDetail(row)">详情</el-button>
          <el-popconfirm v-if="canOperate && row.status === 'pending'" title="确认删除该任务？"
            @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" :total="total"
      layout="total, prev, pager, next"
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
          <el-date-picker v-model="createForm.task_date" type="date"
            value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="showDetail" :title="`考勤详情 #${detailTask?.id}`" size="520px">
      <template v-if="detailTask">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="课程">
            {{ courseMap[detailTask.course_id] || `#${detailTask.course_id}` }}
          </el-descriptions-item>
          <el-descriptions-item label="日期">{{ detailTask.task_date }}</el-descriptions-item>
          <el-descriptions-item label="出勤">
            {{ detailTask.present_count }} / {{ detailTask.total_students }}
            ({{ detailTask.total_students
              ? (detailTask.present_count / detailTask.total_students * 100).toFixed(1) : 0 }}%)
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="{ pending:'info', running:'warning', finished:'success' }[detailTask.status]" size="small">
              {{ { pending:'待开始', running:'进行中', finished:'已结束' }[detailTask.status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ detailTask.start_time?.slice(0, 19).replace('T', ' ') || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ detailTask.end_time?.slice(0, 19).replace('T', ' ') || '--' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="detailRecords" size="small" stripe v-loading="detailLoading"
          max-height="400">
          <el-table-column prop="student_id" label="学生ID" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small"
                :type="{ present:'success', absent:'danger', unverified:'warning' }[row.status]">
                {{ { present:'出勤', absent:'缺勤', unverified:'待核实' }[row.status] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="80">
            <template #default="{ row }">
              {{ row.confidence ? (row.confidence * 100).toFixed(1) + '%' : '--' }}
            </template>
          </el-table-column>
          <el-table-column label="识别时间">
            <template #default="{ row }">
              {{ row.recognized_at?.slice(11, 19) || '--' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-select v-if="row.status !== 'absent'" v-model="row.status" size="small"
                style="width:80px" @change="handleUpdateRecord(row)">
                <el-option label="出勤" value="present" />
                <el-option label="待核实" value="unverified" />
                <el-option label="缺勤" value="absent" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { attendanceApi } from '@/api/attendance'
import { coursesApi } from '@/api/courses'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const canOperate = computed(() => ['admin', 'teacher'].includes(auth.userInfo?.role))

const tasks = ref([]), loading = ref(false), page = ref(1), total = ref(0)
const query = reactive({ status: '', course_id: null })
const showCreate = ref(false)
const courses = ref([])
const courseMap = computed(() => Object.fromEntries(courses.value.map(c => [c.id, c.course_name])))
const createForm = reactive({ course_id: null, task_date: new Date().toISOString().slice(0, 10) })

// 详情抽屉
const showDetail = ref(false), detailTask = ref(null)
const detailRecords = ref([]), detailLoading = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: 20 }
    if (query.status) params.status = query.status
    if (query.course_id) params.course_id = query.course_id
    const res = await attendanceApi.listTasks(params)
    tasks.value = res.data.items
    total.value = res.data.pagination.total
  } finally { loading.value = false }
}

async function loadCourses() {
  if (courses.value.length) return
  try {
    const res = await coursesApi.list({ per_page: 100 })
    courses.value = res.data?.items || []
  } catch { /* ignore */ }
}

async function handleCreate() {
  if (!createForm.course_id) return ElMessage.warning('请选择课程')
  await attendanceApi.createTask(createForm)
  ElMessage.success('考勤任务已创建')
  showCreate.value = false
  fetchData()
}

async function handleDelete(id) {
  try {
    await attendanceApi.deleteTask(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch { /* error already toasted by request interceptor */ }
}

async function viewDetail(row) {
  detailTask.value = row
  showDetail.value = true
  detailLoading.value = true
  try {
    const res = await attendanceApi.getTask(row.id)
    detailTask.value = res.data
    detailRecords.value = res.data.records || []
  } finally { detailLoading.value = false }
}

async function handleUpdateRecord(record) {
  try {
    await attendanceApi.updateRecord(record.id, { status: record.status })
    ElMessage.success('已更新')
  } catch {
    ElMessage.error('更新失败')
  }
}

onMounted(async () => {
  await loadCourses()
  fetchData()
})
</script>
