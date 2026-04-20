import request from './request'
export const attendanceApi = {
  createTask: (data) => request.post('/attendance/tasks', data),
  listTasks: (params) => {
    const { silent, ...rest } = params || {}
    return request.get('/attendance/tasks', { params: rest, silent })
  },
  getTask: (id) => request.get(`/attendance/tasks/${id}`),
  startTask: (id) => request.post(`/attendance/tasks/${id}/start`),
  stopTask: (id) => request.post(`/attendance/tasks/${id}/stop`),
  recognizeFrame: (id, image) =>
    request.post(`/attendance/tasks/${id}/recognize`, { image }),
  listRecords: (params) => request.get('/attendance/records', { params }),
  updateRecord: (id, data) => request.put(`/attendance/records/${id}`, data),
  deleteTask: (id) => request.delete(`/attendance/tasks/${id}`),
}
