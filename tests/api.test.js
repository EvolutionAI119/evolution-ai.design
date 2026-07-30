import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('axios', () => {
  const mockInstance = {
    post: vi.fn().mockResolvedValue({ data: { success: true } }),
    get: vi.fn().mockResolvedValue({ data: { success: true } }),
    put: vi.fn().mockResolvedValue({ data: { success: true } }),
    delete: vi.fn().mockResolvedValue({ data: { success: true } }),
    interceptors: {
      response: { use: vi.fn() },
      request: { use: vi.fn() }
    }
  }
  return {
    default: {
      create: vi.fn(() => mockInstance)
    },
    __mockInstance: mockInstance
  }
})

import { __mockInstance } from 'axios'
const mockAxiosInstance = __mockInstance
import {
  projectAPI,
  modelAPI,
  carAPI,
  parameterAPI,
  workflowAPI,
  aiAPI,
  exportAPI,
  modifyAPI,
  variantAPI,
  healthAPI
} from '../src/api.js'

describe('API 模块测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAxiosInstance.post.mockResolvedValue({ data: { success: true } })
    mockAxiosInstance.get.mockResolvedValue({ data: { success: true } })
    mockAxiosInstance.put.mockResolvedValue({ data: { success: true } })
    mockAxiosInstance.delete.mockResolvedValue({ data: { success: true } })
  })

  describe('1. 项目管理 API', () => {
    it('create 应调用 POST /projects/', async () => {
      await projectAPI.create({ name: 'Test' })
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/projects/', { name: 'Test' })
    })

    it('list 应支持 status 参数', async () => {
      await projectAPI.list('active')
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/projects/', { params: { status: 'active' } })
    })

    it('get 应调用 GET /projects/:id', async () => {
      await projectAPI.get(123)
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/projects/123')
    })

    it('update 应调用 PUT /projects/:id', async () => {
      await projectAPI.update(123, { name: 'Updated' })
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/projects/123', { name: 'Updated' })
    })

    it('delete 应调用 DELETE /projects/:id', async () => {
      await projectAPI.delete(123)
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/projects/123')
    })
  })

  describe('2. 模型管理 API', () => {
    it('list 应支持 project_id 参数', async () => {
      await modelAPI.list(123)
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/models/', { params: { project_id: 123 } })
    })
  })

  describe('3. 车身生成 API', () => {
    it('generate 应调用 POST /car/generate', async () => {
      await carAPI.generate({ params: {} })
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/car/generate', { params: {} })
    })

    it('getComponents 应调用 GET /car/components', async () => {
      await carAPI.getComponents()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/car/components')
    })
  })

  describe('4. 参数管理 API', () => {
    it('list 应支持 project_id 参数', async () => {
      await parameterAPI.list(123)
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/parameters/', { params: { project_id: 123 } })
    })
  })

  describe('5. 工作流 API', () => {
    it('execute 应调用 POST /workflows/:id/execute', async () => {
      await workflowAPI.execute(123)
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/workflows/123/execute')
    })
  })

  describe('6. AI API', () => {
    it('train 应调用 POST /ai/train', async () => {
      await aiAPI.train({ epochs: 10 })
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/ai/train', { epochs: 10 })
    })

    it('classifyStyle 应发送 feature_vector 字段', async () => {
      await aiAPI.classifyStyle([1, 2, 3])
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/ai/classify-style', { feature_vector: [1, 2, 3] })
    })
  })

  describe('7. 模型导出 API', () => {
    it('download 应设置 responseType 为 blob', async () => {
      await exportAPI.download(123, 'stl')
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/export/download/123/stl', { responseType: 'blob' })
    })
  })

  describe('8. 修改 API', () => {
    it('undo 应调用 POST /modify/history/undo', async () => {
      await modifyAPI.undo()
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/modify/history/undo')
    })
  })

  describe('9. 模型变体 API', () => {
    it('compare 应调用 POST /variants/compare', async () => {
      await variantAPI.compare({ variants: [1, 2] })
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/variants/compare', { variants: [1, 2] })
    })
  })

  describe('10. 健康检查 API', () => {
    it('check 应调用 GET /health', async () => {
      await healthAPI.check()
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health')
    })
  })
})