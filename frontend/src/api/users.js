import request from './request'
export const usersApi = {
  list: (params) => request.get('/users', { params }),
  get: (id) => request.get(`/users/${id}`),
  create: (data) => request.post('/users', data),
  update: (id, data) => request.put(`/users/${id}`, data),
  remove: (id) => request.delete(`/users/${id}`),
  toggleActive: (id, isActive) => request.put(`/users/${id}/active`, { is_active: isActive }),
  me: () => request.get('/users/me'),
}
