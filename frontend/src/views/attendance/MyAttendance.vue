<template>
  <el-card shadow="never">
    <template #header>
      <span>我的考勤记录</span>
      <el-tag type="info" style="margin-left:12px">
        出勤率：{{ attendanceRate }}%
      </el-tag>
    </template>

    <el-form :inline="true" :model="query" style="margin-bottom:8px">
      <el-form-item label="状态">
        <el-select v-model="query.status" placeholder="全部" clearable style="width:120px">
          <el-option label="出勤" value="present" />
          <el-option label="缺勤" value="absent" />
          <el-option label="待核实" value="unverified" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 统计卡片 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="6">
        <el-card shadow="never" class="mini-stat">
          <div class="num">{{ total }}</div><div class="lbl">总次数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-stat">
          <div class="num" style="color:#67c23a">{{ countMap.present || 0 }}</div>
          <div class="lbl">出勤</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-stat">
          <div class="num" style="color:#f56c6c">{{ countMap.absent || 0 }}</div>
          <div class="lbl">缺勤</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-stat">
          <div class="num" style="color:#e6a23c">{{ countMap.unverified || 0 }}</div>
          <div class="lbl">待核实</div>
        </el-card>
      </el-col>
    </el-row>

    <el-table :data="records" v-loading="loading" stripe>
      <el-table-column label="课程" min-width="140">
        <template #default="{ row }">{{ row.course_name || '--' }}</template>
      </el-table-column>
      <el-table-column label="考勤日期" width="120">
        <template #default="{ row }">{{ row.task_date || '--' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small"
            :type="{ present:'success', absent:'danger', unverified:'warning' }[row.status]">
            {{ { present:'出勤', absent:'缺勤', unverified:'待核实' }[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="置信度" width="90">
        <template #default="{ row }">
          {{ row.confidence ? (row.confidence * 100).toFixed(1) + '%' : '--' }}
        </template>
      </el-table-column>
      <el-table-column label="识别时间" width="160">
        <template #default="{ row }">
          {{ row.recognized_at?.slice(0, 19).replace('T', ' ') || '--' }}
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" />
    </el-table>

    <el-pagination v-model:current-page="page" :total="total"
      layout="total, prev, pager, next"
      style="margin-top:16px;justify-content:flex-end"
      @current-change="fetchData" />
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { attendanceApi } from '@/api/attendance'
import { reportsApi } from '@/api/reports'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const records = ref([]), loading = ref(false), page = ref(1), total = ref(0)
const query = reactive({ status: '' })
const countMap = ref({ present: 0, absent: 0, unverified: 0 })

const attendanceRate = computed(() => {
  const t = countMap.value.present + countMap.value.absent + countMap.value.unverified
  return t ? ((countMap.value.present / t) * 100).toFixed(1) : '--'
})

async function fetchData() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: 20 }
    if (query.status) params.status = query.status
    const res = await attendanceApi.listRecords(params)
    records.value = res.data.items
    total.value = res.data.pagination.total
  } finally { loading.value = false }
}

async function loadSummary() {
  try {
    // 获取学生本人的历史汇总
    const user = auth.userInfo
    if (user?.role === 'student') {
      // 使用 listRecords 统计三种状态数量（查全量无分页）
      const [p, a, u] = await Promise.all([
        attendanceApi.listRecords({ status: 'present',    per_page: 1 }),
        attendanceApi.listRecords({ status: 'absent',     per_page: 1 }),
        attendanceApi.listRecords({ status: 'unverified', per_page: 1 }),
      ])
      countMap.value = {
        present:    p.data.pagination.total,
        absent:     a.data.pagination.total,
        unverified: u.data.pagination.total,
      }
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  fetchData()
  loadSummary()
})
</script>

<style scoped>
.mini-stat { text-align: center; }
.num { font-size: 28px; font-weight: 600; color: #409eff; line-height: 1.2; }
.lbl { font-size: 12px; color: #909399; margin-top: 2px; }
</style>
