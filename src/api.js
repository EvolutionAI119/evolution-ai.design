// API 服务：合并所有模块到一个文件
import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 60000
})

// 请求拦截器：JWT 注入 + 记录请求开始时间和详细信息
api.interceptors.request.use(
  config => {
    config.metadata = { startTime: Date.now() }
    // 自动携带 JWT（登录/注册等公开接口也可携带，不影响）
    const token = localStorage.getItem('evoai_token')
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }
    const { method, url, headers, data, params } = config
    console.groupCollapsed(`🔄 [${method?.toUpperCase()}] ${url}`)
    console.log('📝 Request Headers:', headers)
    if (params) console.log('🔍 Query Params:', params)
    if (data && !(data instanceof FormData)) console.log('📦 Request Body:', data)
    else if (data instanceof FormData) console.log('📦 Request Body: FormData (files attached)')
    console.groupEnd()
    return config
  },
  error => {
    console.error('❌ Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器：记录响应数据和耗时
api.interceptors.response.use(
  response => {
    const { config, status, statusText, headers, data } = response
    const duration = Date.now() - config.metadata.startTime
    console.groupCollapsed(`✅ [${config.method?.toUpperCase()}] ${config.url} (${status} ${statusText}) · ${duration}ms`)
    console.log('📋 Response Headers:', headers)
    if (config.responseType === 'blob') {
      console.log('📤 Response Data: Blob (size: ' + (data?.size || 'N/A') + ' bytes)')
    } else {
      console.log('📤 Response Data:', data)
    }
    console.log(`⏱️ Duration: ${duration}ms`)
    console.groupEnd()
    return response
  },
  error => {
    const { config, response } = error
    const duration = config?.metadata ? Date.now() - config.metadata.startTime : 'N/A'
    console.groupCollapsed(`❌ [${config?.method?.toUpperCase()}] ${config?.url} · ${duration}ms`)
    if (response) {
      console.log(`💥 Status: ${response.status} ${response.statusText}`)
      console.log('📋 Response Headers:', response.headers)
      console.log('📤 Response Data:', response.data)
    } else {
      console.log('💥 Error:', error.message)
    }
    console.log(`⏱️ Duration: ${duration}ms`)
    console.groupEnd()

    // 401 统一处理：令牌缺失/失效 → 清除并跳转登录页
    // （登录/注册接口本身的 401 由调用页面自行提示，不跳转）
    const isAuthEndpoint = typeof config?.url === 'string' &&
      config.url.startsWith('/auth/')
    if (response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem('evoai_token')
      if (!window.location.hash.startsWith('#/login')) {
        window.location.hash = '#/login'
      }
    }
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

// 导入改参导出 API（全链路工作流）
export const importExportAPI = {
  // 导入
  importModel: (data) => api.post('/import-export/import', data),
  importFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/import-export/import/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 参数查询
  getParams: (sid) => api.get(`/import-export/${sid}/params`),
  getParamGroups: (sid) => api.get(`/import-export/${sid}/params/groups`),
  // 参数修改
  modifyParams: (sid, overrides) => api.put(`/import-export/${sid}/params`, { overrides }),
  // 预览
  getPreview: (sid) => api.get(`/import-export/${sid}/preview`),
  // 导出
  exportModel: (sid, formats, name) => api.post(`/import-export/${sid}/export`, { formats, name }),
  downloadFile: (sid, filename) => api.get(`/import-export/${sid}/download/${filename}`, { responseType: 'blob' }),
  // 参数快照
  getSnapshot: (sid) => api.get(`/import-export/${sid}/snapshot`),
  // 会话管理
  listSessions: () => api.get('/import-export/sessions'),
  deleteSession: (sid) => api.delete(`/import-export/${sid}`)
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
  // 参数
  getParameters: () => api.get('/modify/parameters'),
  addParameter: (data) => api.post('/modify/parameters/add', data),
  updateParameter: (name, value) => api.post('/modify/parameters/update', { name, value }),
  getAutomotiveParameters: () => api.get('/modify/parameters/automotive'),
  // 测量
  measureDistance: (data) => api.post('/modify/measurements/distance', data),
  measureAngle: (data) => api.post('/modify/measurements/angle', data),
  getMeasurementSummary: () => api.get('/modify/measurements/summary'),
  // 历史
  getHistory: () => api.get('/modify/history'),
  undo: () => api.post('/modify/history/undo')
}

// AI训练集 API - 云端计算服务
export const aiAPI = {
  // 创建后台 PyTorch 训练任务（返回任务对象，通过 getTask 轮询）
  train: (data) => api.post('/ai/train', data),
  // 同步生成一批合成样本（Designer「云端训练批次」）
  trainBatch: (data) => api.post('/ai/train/batch', data),
  // 训练任务管理
  listTasks: (status = null) => api.get('/ai/tasks', { params: status ? { status_filter: status } : {} }),
  getTask: (id) => api.get(`/ai/tasks/${id}`),
  cancelTask: (id) => api.post(`/ai/tasks/${id}/cancel`),
  getTrainingCapabilities: () => api.get('/ai/training/capabilities'),
  evaluateQuality: (data) => api.post('/ai/evaluate-quality', data),
  generateDesign: (data) => api.post('/ai/generate-design', data),
  optimize: (data) => api.post('/ai/optimize', data),
  getDatasetStats: () => api.get('/ai/dataset-stats'),
  getCarTypes: () => api.get('/ai/car-types'),
  getStyles: () => api.get('/ai/styles'),
  getBrands: () => api.get('/ai/brands'),
  getModelWeights: () => api.get('/ai/model-weights'),
  // NURBS 专家对话（Ollama 集成）
  chatWithExpert: (question, context) => api.post('/ai/chat', { question, context }),
  getAIHealth: () => api.get('/ai/health'),
  getAIModels: () => api.get('/ai/models')
}

// 贝叶斯优化 API（机器学习后台训练的代理寻优容器）
// 闭环：suggest 建议参数 → 评估造型质量分 → observe 回填 → 迭代收敛 → samples 导出训练数据
export const bayesAPI = {
  // 创建寻优会话（space 缺省时使用 14 个造型规范参数，与训练管线对齐）
  createSession: (data) => api.post('/bayes/sessions', data),
  getSession: (sid) => api.get(`/bayes/sessions/${sid}`),
  deleteSession: (sid) => api.delete(`/bayes/sessions/${sid}`),
  suggest: (sid, n = 1) => api.get(`/bayes/sessions/${sid}/suggest`, { params: { n } }),
  observe: (sid, parameters, score) => api.post(`/bayes/sessions/${sid}/observe`, { parameters, score }),
  best: (sid) => api.get(`/bayes/sessions/${sid}/best`),
  samples: (sid) => api.get(`/bayes/sessions/${sid}/samples`)
}

// 用户认证 API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  // 登录方式探测：前端据此隐藏未配置的第三方登录入口
  methods: () => api.get('/auth/methods'),
  // 微信扫码登录：获取授权二维码 URL（未配置时后端返回 503）
  wechatQr: () => api.get('/auth/wechat/qr'),
  // 微信公众号网页授权：按会话票据获取授权 URL（未配置时后端返回 503）
  mpAuthorize: (ticket) => api.get('/auth/mp/authorize', { params: { ticket } }),
  // 公众号扫码轮询：按会话票据查询授权结果（pending / done / expired）
  mpPoll: (ticket) => api.get('/auth/mp/poll', { params: { ticket } })
}

// API Key(Token) 管理
export const apiKeyAPI = {
  list: () => api.get('/api-keys'),
  set: (provider, apiKey) => api.put(`/api-keys/${provider}`, { api_key: apiKey }),
  remove: (provider) => api.delete(`/api-keys/${provider}`)
}

// 百度文心一言 API
export const ernieAPI = {
  chat: (messages, model = 'ernie-4.0') => api.post('/llm/ernie/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/ernie/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/ernie/images/generations', { prompt })
}

// 阿里通义千问 API
export const qwenAPI = {
  chat: (messages, model = 'qwen-2.5-7b-instruct') => api.post('/llm/qwen/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/qwen/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/qwen/images/generations', { prompt })
}

// 腾讯混元 API
export const hunyuanAPI = {
  chat: (messages, model = 'hunyuan-pro') => api.post('/llm/hunyuan/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/hunyuan/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/hunyuan/images/generations', { prompt })
}

// 字节豆包 API
export const doubaoAPI = {
  chat: (messages, model = 'doubao-pro') => api.post('/llm/doubao/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/doubao/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/doubao/images/generations', { prompt })
}

// 深度求索 DeepSeek API
export const deepseekAPI = {
  chat: (messages, model = 'deepseek-chat') => api.post('/llm/deepseek/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/deepseek/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/deepseek/images/generations', { prompt })
}

// Moonshot Kimi API
export const kimiAPI = {
  chat: (messages, model = 'moonshot-v1-8k') => api.post('/llm/kimi/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/kimi/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/kimi/images/generations', { prompt })
}

// 硅基流动 SiliconFlow 聚合平台（OpenAI 兼容）
export const siliconflowAPI = {
  chat: (messages, model = 'Qwen/Qwen2.5-7B-Instruct') => api.post('/llm/siliconflow/chat/completions', {
    model,
    messages,
    temperature: 0.8
  }),
  embeddings: (text) => api.post('/llm/siliconflow/embeddings', { input: text }),
  images: (prompt) => api.post('/llm/siliconflow/images/generations', { prompt })
}

const llmProviders = {
  ernie: ernieAPI,
  qwen: qwenAPI,
  hunyuan: hunyuanAPI,
  doubao: doubaoAPI,
  deepseek: deepseekAPI,
  kimi: kimiAPI,
  siliconflow: siliconflowAPI
}

// 大模型统一调用 API
export const llmAPI = {
  chat: (provider, messages, model = null) => {
    const apiClient = llmProviders[provider]
    if (!apiClient) throw new Error(`Unsupported provider: ${provider}`)
    return apiClient.chat(messages, model)
  },
  embeddings: (provider, text) => {
    const apiClient = llmProviders[provider]
    if (!apiClient) throw new Error(`Unsupported provider: ${provider}`)
    return apiClient.embeddings(text)
  },
  images: (provider, prompt) => {
    const apiClient = llmProviders[provider]
    if (!apiClient) throw new Error(`Unsupported provider: ${provider}`)
    return apiClient.images(prompt)
  },
  listProviders: () => api.get('/llm/providers')
}

export default api
