import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '../src/stores/project.js'
import { useDesignerStore } from '../src/stores/designer.js'
import { defaultCarParams } from '../src/config/carPresets'

vi.mock('../src/api.js', () => ({
  projectAPI: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn()
  }
}))

import { projectAPI } from '../src/api.js'

describe('架构契约测试 - ProjectStore ↔ DesignerStore 互操作', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('1. DesignerStore 导出接口', () => {
    it('exportToProject 应返回完整的设计数据结构', () => {
      const designer = useDesignerStore()
      
      designer.setCarType('suv')
      designer.setBrand('tesla')
      designer.updateParam('overall_length', 5000)
      
      const exported = designer.exportToProject()
      
      expect(exported).toHaveProperty('carType', 'suv')
      expect(exported).toHaveProperty('brand', 'tesla')
      expect(exported).toHaveProperty('params')
      expect(exported.params.overall_length).toBe(5000)
      expect(exported).toHaveProperty('exportTime')
      expect(new Date(exported.exportTime)).toBeInstanceOf(Date)
    })

    it('exportToProject 返回的 params 应为副本，修改不影响原数据', () => {
      const designer = useDesignerStore()
      const originalLength = designer.params.overall_length
      
      const exported = designer.exportToProject()
      exported.params.overall_length = 9999
      
      expect(designer.params.overall_length).toBe(originalLength)
    })

    it('importFromProject 应正确导入项目中的设计数据', () => {
      const designer = useDesignerStore()
      const testProject = {
        id: 'project-001',
        name: 'Test Project',
        designData: {
          carType: 'sport',
          brand: 'ferrari',
          params: { overall_length: 4500, overall_width: 1900 }
        }
      }
      
      designer.importFromProject(testProject)
      
      expect(designer.carType).toBe('sport')
      expect(designer.brand).toBe('ferrari')
      expect(designer.params.overall_length).toBe(4500)
      expect(designer.params.overall_width).toBe(1900)
    })

    it('importFromProject 当项目无 designData 时应保持默认状态', () => {
      const designer = useDesignerStore()
      designer.setCarType('suv')
      
      designer.importFromProject({ id: 'p1', name: 'No Design' })
      
      expect(designer.carType).toBe('sedan')
      expect(designer.brand).toBe('rolls-royce')
    })

    it('importFromProject 传入 null 时应重置参数为 sedan 默认值', () => {
      const designer = useDesignerStore()
      designer.updateParam('overall_length', 9999)
      
      designer.importFromProject(null)
      
      expect(designer.carType).toBe('sedan')
      expect(designer.params.overall_length).toBe(4950)
    })

    it('clear 方法应重置所有设计状态到初始值', () => {
      const designer = useDesignerStore()
      designer.setCarType('suv')
      designer.setBrand('tesla')
      designer.updateParam('overall_length', 5000)
      designer.setViewMode('2d')
      
      designer.clear()
      
      expect(designer.carType).toBe('sedan')
      expect(designer.brand).toBe('rolls-royce')
      expect(designer.params.overall_length).toBe(4950)
      expect(designer.viewMode).toBe('3d')
    })
  })

  describe('2. ProjectStore 互操作接口', () => {
    it('loadDesignIntoDesigner 应加载项目并导入到设计器', async () => {
      const projectStore = useProjectStore()
      const designer = useDesignerStore()
      
      projectAPI.get.mockResolvedValue({
        data: {
          id: 123,
          name: 'My Project',
          design_data: {
            car_type: 'coupe',
            brand: 'bmw',
            params: { overall_length: 4800 }
          }
        }
      })
      
      await projectStore.loadDesignIntoDesigner(123)
      
      expect(projectAPI.get).toHaveBeenCalledWith(123)
      expect(designer.carType).toBe('coupe')
      expect(designer.brand).toBe('bmw')
      expect(designer.params.overall_length).toBe(4800)
    })

    it('saveDesignFromDesigner 应导出设计并更新项目', async () => {
      const projectStore = useProjectStore()
      const designer = useDesignerStore()
      
      designer.setCarType('suv')
      designer.updateParam('overall_length', 5000)
      
      projectAPI.update.mockResolvedValue({
        data: {
          id: 456,
          name: 'Updated Project',
          design_data: {
            car_type: 'suv',
            brand: 'default',
            params: { overall_length: 5000 }
          }
        }
      })
      
      await projectStore.saveDesignFromDesigner(456)
      
      expect(projectAPI.update).toHaveBeenCalledWith(456, expect.objectContaining({
        design_data: expect.objectContaining({
          car_type: 'suv',
          params: expect.objectContaining({ overall_length: 5000 })
        })
      }))
    })

    it('loadDesignIntoDesigner 加载失败时应设置 error', async () => {
      const projectStore = useProjectStore()
      projectAPI.get.mockRejectedValue(new Error('Network error'))
      
      await expect(projectStore.loadDesignIntoDesigner(123)).rejects.toThrow('Network error')
      expect(projectStore.error).toBe('Network error')
    })

    it('saveDesignFromDesigner 更新失败时应设置 error', async () => {
      const projectStore = useProjectStore()
      projectAPI.update.mockRejectedValue(new Error('Save failed'))
      
      await expect(projectStore.saveDesignFromDesigner(456)).rejects.toThrow('Save failed')
      expect(projectStore.error).toBe('Save failed')
    })
  })

  describe('3. 端到端流程测试', () => {
    it('完整流程：创建项目 → 设计 → 保存 → 重新加载', async () => {
      const projectStore = useProjectStore()
      const designer = useDesignerStore()
      
      projectAPI.create.mockResolvedValue({
        data: { id: 1, name: 'New Project', design_data: null }
      })
      projectAPI.update.mockResolvedValue({
        data: { id: 1, name: 'New Project', design_data: { car_type: 'sport', params: { overall_length: 4600 } } }
      })
      projectAPI.get.mockResolvedValue({
        data: { id: 1, name: 'New Project', design_data: { car_type: 'sport', params: { overall_length: 4600 } } }
      })
      
      await projectStore.createProject({ name: 'New Project' })
      
      designer.setCarType('sport')
      designer.updateParam('overall_length', 4600)
      
      await projectStore.saveDesignFromDesigner(1)
      
      designer.clear()
      expect(designer.carType).toBe('sedan')
      
      await projectStore.loadDesignIntoDesigner(1)
      expect(designer.carType).toBe('sport')
      expect(designer.params.overall_length).toBe(4600)
    })
  })
})
