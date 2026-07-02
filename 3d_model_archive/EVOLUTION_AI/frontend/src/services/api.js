import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const projectAPI = {
  create(data) {
    return api.post('/projects/', data)
  },
  list(status = null) {
    const params = status ? { status } : {}
    return api.get('/projects/', { params })
  },
  get(id) {
    return api.get(`/projects/${id}`)
  },
  update(id, data) {
    return api.put(`/projects/${id}`, data)
  },
  delete(id) {
    return api.delete(`/projects/${id}`)
  }
}

export const modelAPI = {
  upload(projectId, file) {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/models/upload/?project_id=${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list(projectId = null) {
    const params = projectId ? { project_id: projectId } : {}
    return api.get('/models/', { params })
  },
  get(id) {
    return api.get(`/models/${id}`)
  },
  delete(id) {
    return api.delete(`/models/${id}`)
  }
}

export const topologyAPI = {
  optimize(data) {
    return api.post('/topology/optimize/', data)
  }
}

export const qualityAPI = {
  check(data) {
    return api.post('/quality/check/', data)
  },
  list(projectId = null, modelId = null) {
    const params = {}
    if (projectId) params.project_id = projectId
    if (modelId) params.model_id = modelId
    return api.get('/quality/reports/', { params })
  },
  get(id) {
    return api.get(`/quality/reports/${id}`)
  }
}

export const handoverAPI = {
  prepare(data) {
    return api.post('/data/handover/', data)
  }
}

export const parameterAPI = {
  list(projectId = null) {
    const params = projectId ? { project_id: projectId } : {}
    return api.get('/parameters/', { params })
  },
  get(name, projectId = null) {
    const params = projectId ? { project_id: projectId } : {}
    return api.get(`/parameters/${name}`, { params })
  },
  update(name, value, projectId = null) {
    const params = { value }
    if (projectId) params.project_id = projectId
    return api.put(`/parameters/${name}`, null, { params })
  },
  validate(projectId = null) {
    const params = projectId ? { project_id: projectId } : {}
    return api.post('/parameters/validate/', null, { params })
  }
}

export const workflowAPI = {
  create(data) {
    return api.post('/workflows/', data)
  },
  list(projectId = null, status = null) {
    const params = {}
    if (projectId) params.project_id = projectId
    if (status) params.status = status
    return api.get('/workflows/', { params })
  },
  get(id) {
    return api.get(`/workflows/${id}`)
  },
  execute(id) {
    return api.post(`/workflows/${id}/execute`)
  },
  steps(id) {
    return api.get(`/workflows/${id}/steps`)
  },
  delete(id) {
    return api.delete(`/workflows/${id}`)
  }
}

export const reportAPI = {
  get(path) {
    return api.get(`/reports/${path}`)
  }
}

export const healthAPI = {
  check() {
    return api.get('/health')
  }
}

// 车身生成API
export const carAPI = {
  generate(data) {
    return api.post('/car/generate', data)
  },
  generateComponent(component, data) {
    return api.post('/car/generate/component', { component, ...data })
  },
  getComponents() {
    return api.get('/car/components')
  },
  getParameters() {
    return api.get('/car/parameters')
  },
  regenerate(data) {
    return api.post('/car/regenerate', data)
  },
  export(data) {
    return api.post('/car/export', data)
  }
}

// 模型构建API
export const buildAPI = {
  build(data) {
    return api.post('/build/', data)
  },
  rebuild(data) {
    return api.post('/build/rebuild', data)
  },
  batchBuild(data) {
    return api.post('/build/batch', data)
  },
  getCacheStatus() {
    return api.get('/build/cache')
  },
  clearCache(modelId) {
    return api.delete(`/build/cache/${modelId}`)
  },
  getStatus(modelId) {
    return api.get(`/build/status/${modelId}`)
  }
}

// 模型导出API
export const exportAPI = {
  exportModel(data) {
    return api.post('/export/', data)
  },
  download(modelId, format) {
    return api.get(`/export/download/${modelId}/${format}`, { responseType: 'blob' })
  },
  getFormats() {
    return api.get('/export/formats')
  },
  getHistory(modelId) {
    return api.get(`/export/history/${modelId}`)
  }
}

// 模型变体API
export const variantAPI = {
  create(data) {
    return api.post('/variants/', data)
  },
  list(modelId) {
    return api.get(`/variants/${modelId}`)
  },
  get(modelId, variantId) {
    return api.get(`/variants/${modelId}/${variantId}`)
  },
  delete(modelId, variantId) {
    return api.delete(`/variants/${modelId}/${variantId}`)
  },
  compare(data) {
    return api.post('/variants/compare', data)
  },
  getHistory(modelId) {
    return api.get(`/variants/${modelId}/history`)
  },
  rollback(modelId, variantId) {
    return api.post(`/variants/${modelId}/${variantId}/rollback`)
  }
}

// 模型修改API
export const modifyAPI = {
  // NURBS曲面
  createSurface(data) {
    return api.post('/modify/surfaces/create', data)
  },
  getSurface(surfaceId) {
    return api.get(`/modify/surfaces/${surfaceId}`)
  },
  modifySurface(surfaceId, modification) {
    return api.post(`/modify/surfaces/${surfaceId}/modify`, modification)
  },
  updateControlPoint(update) {
    return api.post(`/modify/surfaces/${update.surface_id}/control-point`, update)
  },
  evaluateSurface(surfaceId, u, v) {
    return api.get(`/modify/surfaces/${surfaceId}/evaluate`, { params: { u, v } })
  },
  deleteSurface(surfaceId) {
    return api.delete(`/modify/surfaces/${surfaceId}`)
  },

  // 草图
  createSketch(data) {
    return api.post('/modify/sketches/create', data)
  },
  getSketch(sketchId) {
    return api.get(`/modify/sketches/${sketchId}`)
  },
  addSketchEntity(sketchId, entityData) {
    return api.post(`/modify/sketches/${sketchId}/entities`, entityData)
  },
  addSketchConstraint(sketchId, constraintData) {
    return api.post(`/modify/sketches/${sketchId}/constraints`, constraintData)
  },
  modifySketch(sketchId, modification) {
    return api.post(`/modify/sketches/${sketchId}/modify`, modification)
  },

  // 参数
  getParameters() {
    return api.get('/modify/parameters')
  },
  addParameter(data) {
    return api.post('/modify/parameters/add', data)
  },
  updateParameter(name, value) {
    return api.post('/modify/parameters/update', { name, value })
  },
  driveWithParameter(data) {
    return api.post('/modify/parameters/drive', data)
  },
  getAutomotiveParameters() {
    return api.get('/modify/parameters/automotive')
  },
  applyAutomotiveParameter(paramName, value) {
    return api.post(`/modify/parameters/automotive/apply?param_name=${paramName}&value=${value}`)
  },

  // 测量
  measureDistance(data) {
    return api.post('/modify/measurements/distance', data)
  },
  measureAngle(data) {
    return api.post('/modify/measurements/angle', data)
  },
  measureCurvature(data) {
    return api.post('/modify/measurements/curvature', data)
  },
  getMeasurementSummary() {
    return api.get('/modify/measurements/summary')
  },

  // 历史
  getHistory() {
    return api.get('/modify/history')
  },
  undo() {
    return api.post('/modify/history/undo')
  },
  exportState() {
    return api.post('/modify/export')
  }
}

export default api