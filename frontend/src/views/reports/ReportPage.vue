<template>
  <el-card shadow="never">
    <el-form :inline="true" :model="query">
      <el-form-item label="课程">
        <el-select v-model="query.course_id" placeholder="请选择课程" style="width:200px"
          filterable @change="fetchStats">
          <el-option v-for="c in courses" :key="c.id" :label="c.course_name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
          range-separator="至" start-placeholder="开始" end-placeholder="结束" style="width:240px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchStats" :disabled="!query.course_id">查询</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
      </el-form-item>
    </el-form>

    <el-empty v-if="!series.length && !loading" description="请选择课程后查询" style="margin-top:40px" />

    <template v-else>
      <!-- 统计卡片 -->
      <el-row :gutter="16" style="margin:16px 0 8px">
        <el-col :span="6">
          <el-statistic title="考勤次数" :value="series.length" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均出勤率"
            :value="avgRate" suffix="%" :precision="1" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最高出勤率"
            :value="maxRate" suffix="%" :precision="1" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="最低出勤率"
            :value="minRate" suffix="%" :precision="1" />
        </el-col>
      </el-row>

      <!-- 出勤率折线图 -->
      <VChart :option="lineOption" style="height:300px;margin-top:8px" autoresize />

      <!-- 明细表格 -->
      <el-table :data="series" stripe style="margin-top:16px" v-loading="loading">
        <el-table-column prop="date" label="考勤日期" width="130" />
        <el-table-column prop="present" label="出勤人数" width="100" align="center" />
        <el-table-column prop="total" label="应到人数" width="100" align="center" />
        <el-table-column label="出勤率" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.rate >= 0.9 ? 'success' : row.rate >= 0.7 ? 'warning' : 'danger'">
              {{ (row.rate * 100).toFixed(1) }}%
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { reportsApi } from '@/api/reports'
import { coursesApi } from '@/api/courses'
import { ElMessage } from 'element-plus'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const query = reactive({ course_id: null })
const dateRange = ref([])
const series = ref([])
const courses = ref([])
const loading = ref(false)

const rates = computed(() => series.value.map(s => s.rate * 100))
const avgRate = computed(() => rates.value.length ? rates.value.reduce((a, b) => a + b, 0) / rates.value.length : 0)
const maxRate = computed(() => rates.value.length ? Math.max(...rates.value) : 0)
const minRate = computed(() => rates.value.length ? Math.min(...rates.value) : 0)

const lineOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
    formatter: (p) => `${p[0].name}<br/>出勤率: ${(p[0].value).toFixed(1)}%`
  },
  xAxis: { type: 'category', data: series.value.map(s => s.date) },
  yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: v => `${v}%` } },
  series: [{
    name: '出勤率', type: 'line', smooth: true,
    data: series.value.map(s => +(s.rate * 100).toFixed(2)),
    itemStyle: { color: '#409eff' },
    areaStyle: { opacity: 0.1 },
  }],
}))

async function fetchStats() {
  if (!query.course_id) return
  loading.value = true
  try {
    const params = { date_from: dateRange.value?.[0], date_to: dateRange.value?.[1] }
    const res = await reportsApi.courseStats(query.course_id, params)
    series.value = res.data?.series || []
  } finally { loading.value = false }
}

async function handleExport() {
  try {
    const res = await reportsApi.export({
      course_id: query.course_id,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1],
    })
    const url = URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url; a.download = '考勤报表.xlsx'; a.click()
    URL.revokeObjectURL(url)
  } catch { ElMessage.error('导出失败') }
}

onMounted(async () => {
  try {
    const res = await coursesApi.list({ per_page: 100 })
    courses.value = res.data?.items || []
    if (courses.value.length) {
      query.course_id = courses.value[0].id
      fetchStats()
    }
  } catch { /* ignore */ }
})
</script>
