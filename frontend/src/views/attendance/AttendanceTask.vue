<template>
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
          <el-button v-else type="danger" size="large" :loading="stopping" @click="handleStop">结束考勤</el-button>
          <span v-if="task?.status === 'running'" class="running-badge">
            <el-badge is-dot type="success" /> 识别中...
          </span>
        </div>
      </el-card>
    </el-col>

    <!-- 右侧：识别结果列表 -->
    <el-col :span="10">
      <el-card shadow="never" :header="`识别结果（${recognizedList.length} 人）`">
        <el-scrollbar height="480px">
          <div v-for="r in recognizedList" :key="r.student_id" class="result-item">
            <el-avatar size="small" style="background:#409eff">{{ r.student_name?.[0] }}</el-avatar>
            <div class="result-info">
              <span class="name">{{ r.student_name }}</span>
              <span class="sid">{{ r.student_id }}</span>
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
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoCamera } from '@element-plus/icons-vue'
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
let frameTimer = null, mediaStream = null

async function handleStart() {
  starting.value = true
  try {
    const res = await attendanceApi.startTask(taskId)
    task.value = res.data
    attendanceStore.startTask(res.data)
    await openCamera()
    // 建立 WebSocket
    attendanceStore.connectWebSocket(taskId, auth.token)
    // 每500ms采一帧
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
.running-badge { display: flex; align-items: center; gap: 6px; color: #67c23a; font-size: 14px; }
.result-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.result-info { flex: 1; display: flex; flex-direction: column; }
.name { font-weight: 500; font-size: 14px; }
.sid { font-size: 12px; color: #909399; }
</style>
