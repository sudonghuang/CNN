<template>
  <div>
    <!-- 任务统计条 -->
    <el-card shadow="never" style="margin-bottom:12px" body-style="padding:12px 20px">
      <el-row align="middle" :gutter="24">
        <el-col :span="6">
          <el-statistic title="应到人数" :value="attendanceStore.taskStats.total_students" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="已识别出勤" :value="attendanceStore.taskStats.present_count" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="实时出勤率"
            :value="attendanceRate" suffix="%" :precision="1" />
        </el-col>
        <el-col :span="6" style="text-align:right">
          <el-tag v-if="task?.status === 'running'" type="success" effect="dark">
            <el-icon class="is-loading"><Loading /></el-icon> 识别中
          </el-tag>
          <el-tag v-else-if="task?.status === 'finished'" type="info">已结束</el-tag>
          <el-tag v-else type="warning">待开始</el-tag>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="16">
      <!-- 左侧：摄像头 + 控制 -->
      <el-col :span="14">
        <el-card shadow="never" header="实时识别">
          <div class="video-wrap">
            <video ref="videoRef" autoplay playsinline class="video" />
            <canvas ref="canvasRef" style="display:none" width="640" height="480" />
            <div v-if="!task || task.status !== 'running'" class="video-placeholder">
              <el-icon style="font-size:64px;color:#c0c4cc"><VideoCamera /></el-icon>
              <p>点击"开始考勤"启动摄像头</p>
            </div>
          </div>
          <div class="controls">
            <el-button v-if="!task || task.status !== 'running'" type="primary" size="large"
              :loading="starting" @click="handleStart">开始考勤</el-button>
            <el-button v-else type="danger" size="large" :loading="stopping"
              @click="handleStop">结束考勤</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：识别结果 -->
      <el-col :span="10">
        <el-card shadow="never" :header="`识别结果（${recognizedList.length} 人）`">
          <el-scrollbar height="440px">
            <div v-for="r in recognizedList" :key="r.student_id" class="result-item">
              <el-avatar size="small" style="background:#409eff;flex-shrink:0">
                {{ r.student_id?.slice(-2) }}
              </el-avatar>
              <div class="result-info">
                <span class="name">{{ r.student_id }}</span>
              </div>
              <el-tag :type="r.status === 'present' ? 'success' : 'warning'" size="small">
                {{ r.status === 'present' ? '出勤' : '待核实' }}
                {{ (r.confidence * 100).toFixed(1) }}%
              </el-tag>
            </div>
            <el-empty v-if="!recognizedList.length" description="等待识别..." :image-size="60" />
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoCamera, Loading } from '@element-plus/icons-vue'
import { attendanceApi } from '@/api/attendance'
import { useAttendanceStore } from '@/stores/attendance'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const taskId = Number(route.params.id)
const attendanceStore = useAttendanceStore()
const auth = useAuthStore()

const task = ref(null), starting = ref(false), stopping = ref(false)
const videoRef = ref(), canvasRef = ref()
const recognizedList = computed(() => attendanceStore.recognitionResults)
const attendanceRate = computed(() => {
  const { present_count, total_students } = attendanceStore.taskStats
  return total_students ? +((present_count / total_students) * 100).toFixed(1) : 0
})
let frameTimer = null, mediaStream = null

async function handleStart() {
  starting.value = true
  try {
    const res = await attendanceApi.startTask(taskId)
    task.value = res.data
    attendanceStore.startTask(res.data)
    await openCamera()
    attendanceStore.connectWebSocket(taskId, auth.token)
    frameTimer = setInterval(sendFrame, 500)
    ElMessage.success('考勤已开始')
  } catch (e) {
    ElMessage.error('启动失败: ' + (e.response?.data?.message || e.message))
  } finally { starting.value = false }
}

async function handleStop() {
  stopping.value = true
  clearInterval(frameTimer)
  stopCamera()
  try {
    const res = await attendanceApi.stopTask(taskId)
    task.value = res.data
    attendanceStore.stopTask()
    ElMessage.success(`考勤结束，出勤 ${res.data.present_count}/${res.data.total_students} 人`)
  } finally { stopping.value = false }
}

async function openCamera() {
  mediaStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
  videoRef.value.srcObject = mediaStream
}

function stopCamera() {
  mediaStream?.getTracks().forEach(t => t.stop())
  mediaStream = null
}

function sendFrame() {
  if (!videoRef.value || !canvasRef.value) return
  const ctx = canvasRef.value.getContext('2d')
  ctx.drawImage(videoRef.value, 0, 0, 640, 480)
  const b64 = canvasRef.value.toDataURL('image/jpeg', 0.7)
  attendanceStore.sendFrame(b64, taskId)
}

onBeforeUnmount(() => { clearInterval(frameTimer); stopCamera() })
</script>

<style scoped>
.video-wrap { position: relative; background: #000; border-radius: 8px; overflow: hidden; min-height: 360px; }
.video { width: 100%; display: block; }
.video-placeholder { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #909399; }
.controls { display: flex; align-items: center; gap: 16px; margin-top: 16px; }
.result-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.result-info { flex: 1; }
.name { font-size: 13px; }
</style>
