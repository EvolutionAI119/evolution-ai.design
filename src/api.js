// API 服务：合并所有模块到一个文件
import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 项目管理 API
export const projectAPI = {
  create: (data) => api.post('/projects/', data),
  list: (status = null) => api.get('/projects/', { params: status ? { status } : {} }),
  get: (id) => api.get(`/projects/${id}`),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`)
}

// 模型管理 API
export const modelAPI = {
  upload: (projectId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/models/upload/?project_id=${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list: (projectId = null) => api.get('/models/', { params: projectId ? { project_id: projectId } : {} }),
  get: (id) => api.get(`/models/${id}`),
  delete: (id) => api.delete(`/models/${id}`)
}

// 拓扑优化 API
export const topologyAPI = {
  optimize: (data) => api.post('/topology/optimize/', data)
}

// 质量检查 API
export const qualityAPI = {
  check: (data) => api.post('/quality/check/', data),
  list: (projectId = null, modelId = null) => {
    const params = {}
    if (projectId) params.project_id = projectId
    if (modelId) params.model_id = modelId
    return api.get('/quality/reports/', { params })
  },
  get: (id) => api.get(`/quality/reports/${id}`)
}

// 数据交接 API
export const handoverAPI = {
  prepare: (data) => api.post('/data/handover/', data)
}

// 参数管理 API
export const parameterAPI = {
  list: (projectId = null) => api.get('/parameters/', { params: projectId ? { project_id: projectId } : {} }),
  get: (name, projectId = null) => api.get(`/parameters/${name}`, { params: projectId ? { project_id: projectId } : {} }),
  update: (name, value, projectId = null) => {
    const params = { value }
    if (projectId) params.project_id = projectId
    return api.put(`/parameters/${name}`, null, { params })
  },
  validate: (projectId = null) => api.post('/parameters/validate/', null, { params: projectId ? { project_id: projectId } : {} })
}

// 工作流 API
export const workflowAPI = {
  create: (data) => api.post('/workflows/', data),
  list: (projectId = null, status = null) => {
    const params = {}
    if (projectId) params.project_id = projectId
    if (status) params.status = status
    return api.get('/workflows/', { params })
  },
  get: (id) => api.get(`/workflows/${id}`),
  execute: (id) => api.post(`/workflows/${id}/execute`),
  steps: (id) => api.get(`/workflows/${id}/steps`),
  delete: (id) => api.delete(`/workflows/${id}`)
}

// 报告 API
export const reportAPI = {
  get: (path) => api.get(`/reports/${path}`)
}

// 健康检查 API
export const healthAPI = {
  check: () => api.get('/health')
}

// 车身生成 API
export const carAPI = {
  generate: (data) => api.post('/car/generate', data),
  generateComponent: (component, data) => api.post('/car/generate/component', { component, ...data }),
  getComponents: () => api.get('/car/components'),
  getParameters: () => api.get('/car/parameters'),
  regenerate: (data) => api.post('/car/regenerate', data),
  export: (data) => api.post('/car/export', data)
}

// 模型构建 API
export const buildAPI = {
  build: (data) => api.post('/build/', data),
  rebuild: (data) => api.post('/build/rebuild', data),
  batchBuild: (data) => api.post('/build/batch', data),
  getCacheStatus: () => api.get('/build/cache'),
  clearCache: (modelId) => api.delete(`/build/cache/${modelId}`),
  getStatus: (modelId) => api.get(`/build/status/${modelId}`)
}

// 模型导出 API
export const exportAPI = {
  exportModel: (data) => api.post('/export/', data),
  download: (modelId, format) => api.get(`/export/download/${modelId}/${format}`, { responseType: 'blob' }),
  getFormats: () => api.get('/export/formats'),
  getHistory: (modelId) => api.get(`/export/history/${modelId}`)
}

// 模型变体 API
export const variantAPI = {
  create: (data) => api.post('/variants/', data),
  list: (modelId) => api.get(`/variants/${modelId}`),
  get: (modelId, variantId) => api.get(`/variants/${modelId}/${variantId}`),
  delete: (modelId, variantId) => api.delete(`/variants/${modelId}/${variantId}`),
  compare: (data) => api.post('/variants/compare', data),
  getHistory: (modelId) => api.get(`/variants/${modelId}/history`),
  rollback: (modelId, variantId) => api.post(`/variants/${modelId}/${variantId}/rollback`)
}

// 模型修改 API
export const modifyAPI = {
  // NURBS 曲面
  createSurface: (data) => api.post('/modify/surfaces/create', data),
  getSurface: (surfaceId) => api.get(`/modify/surfaces/${surfaceId}`),
  modifySurface: (surfaceId, modification) => api.post(`/modify/surfaces/${surfaceId}/modify`, modification),
  updateControlPoint: (update) => api.post(`/modify/surfaces/${update.surface_id}/control-point`, update),
  evaluateSurface: (surfaceId, u, v) => api.get(`/modify/surfaces/${surfaceId}/evaluate`, { params: { u, v } }),
  deleteSurface: (surfaceId) => api.delete(`/modify/surfaces/${surfaceId}`),
  // 草图
  createSketch: (data) => api.post('/modify/sketches/create', data),
  getSketch: (sketchId) => api.get(`/modify/sketches/${sketchId}`),
  addSketchEntity: (sketchId, entityData) => api.post(`/modify/sketches/${sketchId}/entities`, entityData),
  addSketchConstraint: (sketchId, constraintData) => api.post(`/modify/sketches/${sketchId}/constraints`, constraintData),
  modifySketch: (sketchId, modification) => api.post(`/modify/sketches/${sketchId}/modify`, modification),
  // 参数
  getParameters: () => api.get('/modify/parameters'),
  addParameter: (data) => api.post('/modify/parameters/add', data),
  updateParameter: (name, value) => api.post('/modify/parameters/update', { name, value }),
  driveWithParameter: (data) => api.post('/modify/parameters/drive', data),
  getAutomotiveParameters: () => api.get('/modify/parameters/automotive'),
  applyAutomotiveParameter: (paramName, value) => api.post(`/modify/parameters/automotive/apply?param_name=${paramName}&value=${value}`),
  // 测量
  measureDistance: (data) => api.post('/modify/measurements/distance', data),
  measureAngle: (data) => api.post('/modify/measurements/angle', data),
  measureCurvature: (data) => api.post('/modify/measurements/curvature', data),
  getMeasurementSummary: () => api.get('/modify/measurements/summary'),
  // 历史
  getHistory: () => api.get('/modify/history'),
  undo: () => api.post('/modify/history/undo'),
  exportState: () => api.post('/modify/export')
}

export default api
