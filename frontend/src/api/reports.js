import request from './request'
export const reportsApi = {
  courseStats: (courseId, params) =>
    request.get(`/reports/course/${courseId}`, { params }),
  studentHistory: (studentId) =>
    request.get(`/reports/student/${studentId}`),
  export: (params) =>
    request.get('/reports/export', { params, responseType: 'blob' }),
  warnings: () => request.get('/reports/warnings'),
}
