import request from './request'

export const coursesApi = {
  list: (params) => request.get('/courses', { params }),
  get: (id) => request.get(`/courses/${id}`),
  create: (data) => request.post('/courses', data),
  update: (id, data) => request.put(`/courses/${id}`, data),
  remove: (id) => request.delete(`/courses/${id}`),
  enroll: (courseId, studentId) =>
    request.post(`/courses/${courseId}/enroll`, { student_id: studentId }),
  unenroll: (courseId, studentId) =>
    request.delete(`/courses/${courseId}/enroll/${studentId}`),
  students: (courseId) => request.get(`/courses/${courseId}/students`),
}
