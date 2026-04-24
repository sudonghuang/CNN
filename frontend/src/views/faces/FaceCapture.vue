<template>
  <el-card shadow="never">
    <template #header>
      <span>人脸数据采集 —— {{ student?.name }}（{{ student?.student_id }}）</span>
      <el-tag :type="student?.face_registered ? 'success' : 'warning'" style="margin-left:12px">
        已采集 {{ student?.face_count }} 张
      </el-tag>
    </template>

    <el-tabs v-model="tab">
      <!-- 上传图片 -->
      <el-tab-pane label="上传图片" name="upload">
        <el-upload
          drag multiple accept="image/*" :auto-upload="false"
          :on-change="(f) => uploadFiles.push(f.raw)"
          :file-list="[]"
          style="width:360px"
        >
          <el-icon style="font-size:48px;color:#c0c4cc"><Upload /></el-icon>
          <p>将图片拖到此处，或<em>点击上传</em></p>
          <template #tip><div style="color:#909399;font-size:12px">支持 jpg/png，建议每人至少5张不同角度</div></template>
        </el-upload>
        <el-button type="primary" :disabled="!uploadFiles.length" :loading="uploading"
          style="margin-top:16px" @click="handleUpload">
          上传 {{ uploadFiles.length }} 张图片
        </el-button>
      </el-tab-pane>

      <!-- 实时采集 -->
      <el-tab-pane label="摄像头采集" name="camera">
        <div class="camera-area">
          <video ref="videoRef" autoplay playsinline class="video-preview" />
          <canvas ref="canvasRef" style="display:none" width="640" height="480" />
        </div>
        <div style="margin-top:12px">
          <el-button v-if="!streaming" type="primary" :icon="VideoCamera" @click="startCamera">开启摄像头</el-button>
          <el-button v-else type="success" :icon="Camera" @click="captureFrame">拍照 (已拍 {{ captureCount }} 张)</el-button>
          <el-button v-if="streaming" @click="stopCamera">关闭摄像头</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 已有图片列表 -->
    <el-divider>已注册图片</el-divider>
    <div class="face-grid">
      <div v-for="img in faceImages" :key="img.id" class="face-item">
        <el-image :src="`/api/faces/file/${img.id}`" fit="cover" style="width:80px;height:80px;border-radius:4px" />
        <el-button link type="danger" size="small" @click="handleDeleteImage(img.id)">删除</el-button>
      </div>
      <el-empty v-if="!faceImages.length" description="暂无图片" :image-size="60" />
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Upload, VideoCamera, Camera } from '@element-plus/icons-vue'
import { facesApi } from '@/api/faces'
import { studentsApi } from '@/api/students'

const route = useRoute()
const studentId = route.params.studentId
const student = ref(null), faceImages = ref([]), tab = ref('upload')
const uploadFiles = ref([]), uploading = ref(false)
const streaming = ref(false), captureCount = ref(0)
const videoRef = ref(), canvasRef = ref()
let mediaStream = null

onMounted(async () => {
  const [sRes, fRes] = await Promise.all([
    studentsApi.get(studentId), facesApi.list(studentId)
  ])
  student.value = sRes.data
  faceImages.value = fRes.data || []
})

async function handleUpload() {
  uploading.value = true
  try {
    await facesApi.upload(studentId, uploadFiles.value)
    ElMessage.success('上传成功')
    uploadFiles.value = []
    refreshImages()
  } finally { uploading.value = false }
}

async function startCamera() {
  mediaStream = await navigator.mediaDevices.getUserMedia({ video: true })
  videoRef.value.srcObject = mediaStream
  streaming.value = true
}

async function captureFrame() {
  const ctx = canvasRef.value.getContext('2d')
  ctx.drawImage(videoRef.value, 0, 0, 640, 480)
  const b64 = canvasRef.value.toDataURL('image/jpeg', 0.85)
  await facesApi.capture(studentId, b64)
  captureCount.value++
  ElMessage.success(`已拍第 ${captureCount.value} 张`)
  refreshImages()
}

function stopCamera() {
  mediaStream?.getTracks().forEach(t => t.stop())
  if (videoRef.value) videoRef.value.srcObject = null
  streaming.value = false; captureCount.value = 0
}

async function handleDeleteImage(id) {
  await facesApi.remove(id)
  ElMessage.success('已删除')
  refreshImages()
}

async function refreshImages() {
  const [sRes, fRes] = await Promise.all([studentsApi.get(studentId), facesApi.list(studentId)])
  student.value = sRes.data; faceImages.value = fRes.data || []
}

onBeforeUnmount(stopCamera)
</script>

<style scoped>
.camera-area { width: 480px; background: #000; border-radius: 8px; overflow: hidden; }
.video-preview { width: 100%; display: block; }
.face-grid { display: flex; flex-wrap: wrap; gap: 12px; padding: 8px 0; }
.face-item { display: flex; flex-direction: column; align-items: center; gap: 4px; }
</style>
