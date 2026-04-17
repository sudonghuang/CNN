import { defineStore } from 'pinia'
import { ref } from 'vue'
import { io } from 'socket.io-client'

export const useAttendanceStore = defineStore('attendance', () => {
  const currentTask = ref(null)
  const recognitionResults = ref([])
  const isRunning = ref(false)
  const taskStats = ref({ present_count: 0, total_students: 0 })
  let socket = null

  function startTask(task) {
    currentTask.value = task
    isRunning.value = true
    recognitionResults.value = []
    taskStats.value = { present_count: 0, total_students: task.total_students || 0 }
  }

  function stopTask() {
    isRunning.value = false
    currentTask.value = null
    _disconnect()
  }

  function addResult(result) {
    const idx = recognitionResults.value.findIndex(
      r => r.student_id === result.student_id
    )
    if (idx === -1) {
      recognitionResults.value.unshift(result)
    } else {
      recognitionResults.value[idx] = result
    }
  }

  /**
   * 连接 Socket.IO 服务端，加入考勤任务房间
   * @param {number} taskId
   * @param {string} token  JWT token
   */
  function connectWebSocket(taskId, token) {
    _disconnect()

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
    socket = io(baseUrl, {
      query: { token },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
    })

    socket.on('connect', () => {
      socket.emit('join_task', { task_id: taskId })
    })

    socket.on('recognition_result', (data) => {
      if (data.task_id === taskId) {
        data.results?.forEach(addResult)
      }
    })

    socket.on('task_update', (data) => {
      if (data.task_id === taskId) {
        taskStats.value = {
          present_count: data.present_count,
          total_students: data.total_students,
        }
        if (data.status === 'finished') {
          isRunning.value = false
        }
      }
    })

    socket.on('error', (data) => {
      console.warn('[Socket.IO] server error:', data.message)
    })

    socket.on('disconnect', (reason) => {
      console.log('[Socket.IO] disconnected:', reason)
    })

    return socket
  }

  /**
   * 发送视频帧（base64 JPEG）到服务端进行人脸识别
   * @param {string} imageBase64  含 data URI 前缀的 base64 字符串
   * @param {number} taskId
   */
  function sendFrame(imageBase64, taskId) {
    const tid = taskId ?? currentTask.value?.id
    if (socket?.connected && tid) {
      socket.emit('frame', { task_id: tid, image: imageBase64 })
    }
  }

  function _disconnect() {
    if (socket) {
      socket.disconnect()
      socket = null
    }
  }

  return {
    currentTask, recognitionResults, isRunning, taskStats,
    startTask, stopTask, addResult, connectWebSocket, sendFrame,
  }
})
