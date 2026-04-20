<template>
  <div>
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <el-card shadow="never" class="stat-card">
          <div class="stat-num">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="16">
        <el-card shadow="never" header="近7日出勤趋势">
          <VChart :option="lineOption" style="height:300px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" header="缺勤预警">
          <el-empty v-if="!warnings.length" description="暂无预警" :image-size="60" />
          <el-table v-else :data="warnings" size="small" :show-header="false">
            <el-table-column prop="name" label="姓名" />
            <el-table-column prop="absent_count" label="缺勤" width="60">
              <template #default="{ row }">
                <el-tag type="danger" size="small">{{ row.absent_count }}次</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { reportsApi } from '@/api/reports'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const stats = ref([
  { label: '学生总数', value: '--' },
  { label: '今日考勤场次', value: '--' },
  { label: '今日出勤率', value: '--' },
  { label: '待核实记录', value: '--' },
])
const warnings = ref([])
const lineOption = ref({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}%' } },
  series: [{ name: '出勤率', type: 'line', smooth: true, data: [], itemStyle: { color: '#409eff' } }],
})

onMounted(async () => {
  // 一次性获取仪表盘统计
  try {
    const res = await reportsApi.stats()
    const d = res.data || {}
    stats.value[0].value = d.student_count ?? '--'
    stats.value[1].value = d.today_task_count != null ? d.today_task_count + '场' : '--'
    stats.value[2].value = d.today_attendance_rate != null
      ? (d.today_attendance_rate * 100).toFixed(1) + '%' : '--'
    stats.value[3].value = d.unverified_count ?? '--'
  } catch { /* ignore */ }

  // 缺勤预警
  try {
    const res = await reportsApi.warnings()
    warnings.value = res.data?.slice(0, 5) || []
  } catch { /* ignore */ }

  // 近7日出勤趋势（仅 admin/teacher/counselor 可访问）
  try {
    const { attendanceApi } = await import('@/api/attendance')
    const res = await attendanceApi.listTasks({ per_page: 7, status: 'finished', silent: true })
    const items = res.data?.items?.slice().reverse() || []
    lineOption.value = {
      ...lineOption.value,
      xAxis: { type: 'category', data: items.map(t => t.task_date) },
      series: [{
        name: '出勤率', type: 'line', smooth: true,
        data: items.map(t => t.total_students
          ? +((t.present_count / t.total_students) * 100).toFixed(1) : 0),
        itemStyle: { color: '#409eff' },
        areaStyle: { opacity: 0.1 },
      }],
    }
  } catch { /* ignore */ }
})
</script>

<style scoped>
.stat-card { text-align: center; padding: 8px 0; }
.stat-num { font-size: 32px; font-weight: 600; color: #409eff; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>
