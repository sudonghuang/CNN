import request from './request'
export const facesApi = {
  upload: (studentId, files) => {
    const fd = new FormData()
    files.forEach(f => fd.append('images', f))
    return request.post(`/faces/${studentId}/upload`, fd)
  },
  capture: (studentId, imageBase64) =>
    request.post(`/faces/${studentId}/capture`, { image: imageBase64 }),
  list: (studentId) => request.get(`/faces/${studentId}`),
  remove: (imageId) => request.delete(`/faces/${imageId}`),
  train: (modelType = 'resnet50') => request.post('/faces/train', { model_type: modelType }),
}
