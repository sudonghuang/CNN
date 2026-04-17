import request from './request'
export const studentsApi = {
  list: (params) => request.get('/students', { params }),
  create: (data) => request.post('/students', data),
  get: (id) => request.get(`/students/${id}`),
  update: (id, data) => request.put(`/students/${id}`, data),
  remove: (id) => request.delete(`/students/${id}`),
  importExcel: (file) => {
    const fd = new FormData(); fd.append('file', file)
    return request.post('/students/import', fd)
  },
  classes: () => request.get('/students/classes'),
}
