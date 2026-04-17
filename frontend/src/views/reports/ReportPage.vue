<template>
  <el-card shadow="never">
    <el-form :inline="true" :model="query">
      <el-form-item label="课程ID">
        <el-input-number v-model="query.course_id" :min="1" style="width:120px" />
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
          range-separator="至" start-placeholder="开始" end-placeholder="结束" style="width:240px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchStats">查询</el-button>
        <el-button :icon="Download" @click="handleExport">导出 Excel</el-button>
      </el-form-item>
    </el-form>

    <!-- 出勤率折线图 -->
    <VChart :option="lineOption" style="height:320px;margin-top:16px" autoresize />

    <!-- 出勤汇总表格 -->
    <el-table :data="series" stripe style="margin-top:16px">
      <el-table-column prop="date" label="日期" width="130" />
      <el-table-column prop="present" label="出勤人数" width="100" />
      <el-table-column prop="total" label="应到人数" width="100" />
      <el-table-column label="出勤率" width="100">
        <template #default="{ row }">
          <el-tag :type="row.rate >= 0.9 ? 'success' : row.rate >= 0.7 ? 'warning' : 'danger'">
            {{ (row.rate * 100).toFixed(1) }}%
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { reportsApi } from '@/api/reports'
import { ElMessage } from 'element-plus'

use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const query = reactive({ course_id: 1 })
const dateRange = ref([])
const series = ref([])

const lineOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>出勤率: ${(p[0].value * 100).toFixed(1)}%` },
  xAxis: { type: 'category', data: series.value.map(s => s.date) },
  yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: v => `${(v*100).toFixed(0)}%` } },
  series: [{ name: '出勤率', type: 'line', smooth: true, data: series.value.map(s => s.rate),
    itemStyle: { color: '#409eff' }, areaStyle: { opacity: 0.1 } }],
}))

async function fetchStats() {
  const params = { date_from: dateRange.value?.[0], date_to: dateRange.value?.[1] }
  const res = await reportsApi.courseStats(query.course_id, params)
  series.value = res.data?.series || []
}

async function handleExport() {
  try {
    const res = await reportsApi.export({
      course_id: query.course_id,
      date_from: dateRange.value?.[0],
      date_to: dateRange.value?.[1],
    })
    const url = URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a'); a.href = url; a.download = '考勤报表.xlsx'; a.click()
    URL.revokeObjectURL(url)
  } catch { ElMessage.error('导出失败') }
}
</script>
