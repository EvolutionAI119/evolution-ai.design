import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '../src/stores/project.js'

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

describe('Project Store 测试', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('1. 初始化状态', () => {
    it('初始状态应为空', () => {
      const store = useProjectStore()
      expect(store.projects).toEqual([])
      expect(store.currentProject).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('2. loadProjects - 获取项目列表', () => {
    it('应调用 projectAPI.list 并转换 snake_case 到 camelCase', async () => {
      const store = useProjectStore()
      projectAPI.list.mockResolvedValue({
        data: [
          { id: 1, name: 'Project A', created_at: '2024-01-01', updated_at: '2024-01-02', model_count: 3, status: 'Active' },
          { id: 2, name: 'Project B', created_at: '2024-01-03', updated_at: '2024-01-04', model_count: 0, status: 'Draft' }
        ]
      })

      await store.loadProjects()

      expect(projectAPI.list).toHaveBeenCalledWith(null)
      expect(store.projects).toHaveLength(2)
      expect(store.projects[0]).toEqual({
        id: 1,
        name: 'Project A',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-02',
        modelCount: 3,
        status: 'Active'
      })
      expect(store.isLoading).toBe(false)
    })

    it('应支持 status 过滤参数', async () => {
      const store = useProjectStore()
      projectAPI.list.mockResolvedValue({ data: [] })

      await store.loadProjects('Active')

      expect(projectAPI.list).toHaveBeenCalledWith('Active')
    })

    it('加载失败时应设置 error 并抛出异常', async () => {
      const store = useProjectStore()
      projectAPI.list.mockRejectedValue(new Error('Network error'))

      await expect(store.loadProjects()).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
      expect(store.isLoading).toBe(false)
    })

    it('isLoading 在加载期间应为 true', async () => {
      const store = useProjectStore()
      let loadingDuringCall = null
      projectAPI.list.mockImplementation(() => {
        loadingDuringCall = store.isLoading
        return Promise.resolve({ data: [] })
      })

      await store.loadProjects()

      expect(loadingDuringCall).toBe(true)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('3. loadProject - 获取单个项目', () => {
    it('应调用 projectAPI.get 并设置 currentProject', async () => {
      const store = useProjectStore()
      projectAPI.get.mockResolvedValue({
        data: { id: 42, name: 'Test Project', created_at: '2024-01-01', status: 'Active', description: 'test desc' }
      })

      const result = await store.loadProject(42)

      expect(projectAPI.get).toHaveBeenCalledWith(42)
      expect(store.currentProject).toEqual({
        id: 42,
        name: 'Test Project',
        createdAt: '2024-01-01',
        status: 'Active',
        description: 'test desc'
      })
      expect(result).toEqual(store.currentProject)
    })

    it('如果项目已在列表中，应更新列表中的该项', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 42, name: 'Old Name', createdAt: '2024-01-01', status: 'Draft' })
      projectAPI.get.mockResolvedValue({
        data: { id: 42, name: 'Updated Name', created_at: '2024-01-01', status: 'Active' }
      })

      await store.loadProject(42)

      expect(store.projects[0].name).toBe('Updated Name')
      expect(store.projects[0].status).toBe('Active')
    })
  })

  describe('4. createProject - 创建项目', () => {
    it('应调用 projectAPI.create 并将新项目加入列表头部', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 1, name: 'Existing', createdAt: '2024-01-01' })
      projectAPI.create.mockResolvedValue({
        data: { id: 2, name: 'New Project', created_at: '2024-01-05', status: 'Draft' }
      })

      const result = await store.createProject({ name: 'New Project', description: 'desc' })

      expect(projectAPI.create).toHaveBeenCalledWith({ name: 'New Project', description: 'desc' })
      expect(store.projects).toHaveLength(2)
      expect(store.projects[0].id).toBe(2)
      expect(store.projects[0].name).toBe('New Project')
      expect(store.currentProject).toEqual(result)
    })

    it('发送给后端的数据应为 snake_case', async () => {
      const store = useProjectStore()
      projectAPI.create.mockResolvedValue({ data: { id: 1, name: 'Test' } })

      await store.createProject({ modelCount: 3, createdAt: '2024-01-01' })

      expect(projectAPI.create).toHaveBeenCalledWith({
        model_count: 3,
        created_at: '2024-01-01'
      })
    })
  })

  describe('5. updateProject - 更新项目', () => {
    it('应调用 projectAPI.update 并更新列表和 currentProject', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 1, name: 'Old Name', status: 'Draft' })
      store.currentProject = { id: 1, name: 'Old Name', status: 'Draft' }
      projectAPI.update.mockResolvedValue({
        data: { id: 1, name: 'New Name', status: 'Active' }
      })

      const result = await store.updateProject(1, { name: 'New Name' })

      expect(projectAPI.update).toHaveBeenCalledWith(1, { name: 'New Name' })
      expect(store.projects[0].name).toBe('New Name')
      expect(store.currentProject.name).toBe('New Name')
      expect(result.name).toBe('New Name')
    })

    it('currentProject 不是目标项目时不应修改', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 1, name: 'P1' })
      store.projects.push({ id: 2, name: 'P2' })
      store.currentProject = { id: 2, name: 'P2' }
      projectAPI.update.mockResolvedValue({ data: { id: 1, name: 'Updated P1' } })

      await store.updateProject(1, { name: 'Updated P1' })

      expect(store.currentProject.name).toBe('P2')
    })
  })

  describe('6. deleteProject - 删除项目', () => {
    it('应调用 projectAPI.delete 并从列表移除', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 1, name: 'P1' })
      store.projects.push({ id: 2, name: 'P2' })
      projectAPI.delete.mockResolvedValue({})

      await store.deleteProject(1)

      expect(projectAPI.delete).toHaveBeenCalledWith(1)
      expect(store.projects).toHaveLength(1)
      expect(store.projects[0].id).toBe(2)
    })

    it('删除当前项目时应清空 currentProject', async () => {
      const store = useProjectStore()
      store.projects.push({ id: 1, name: 'P1' })
      store.currentProject = { id: 1, name: 'P1' }
      projectAPI.delete.mockResolvedValue({})

      await store.deleteProject(1)

      expect(store.currentProject).toBeNull()
    })
  })

  describe('7. recentProjects - 最近项目', () => {
    it('应按 updatedAt 倒序返回前 5 个', () => {
      const store = useProjectStore()
      store.projects = [
        { id: 1, name: 'P1', updatedAt: '2024-01-01' },
        { id: 2, name: 'P2', updatedAt: '2024-01-05' },
        { id: 3, name: 'P3', updatedAt: '2024-01-03' },
        { id: 4, name: 'P4', updatedAt: '2024-01-10' },
        { id: 5, name: 'P5', updatedAt: '2024-01-02' },
        { id: 6, name: 'P6', updatedAt: '2024-01-07' }
      ]

      const recent = store.recentProjects

      expect(recent).toHaveLength(5)
      expect(recent[0].id).toBe(4)
      expect(recent[1].id).toBe(6)
      expect(recent[2].id).toBe(2)
    })

    it('没有 updatedAt 时回退到 createdAt', () => {
      const store = useProjectStore()
      store.projects = [
        { id: 1, name: 'P1', createdAt: '2024-01-01' },
        { id: 2, name: 'P2', createdAt: '2024-01-05' }
      ]

      const recent = store.recentProjects

      expect(recent[0].id).toBe(2)
    })
  })

  describe('8. clearError - 清除错误', () => {
    it('应将 error 重置为 null', () => {
      const store = useProjectStore()
      store.error = 'Some error'

      store.clearError()

      expect(store.error).toBeNull()
    })
  })

  describe('9. 筛选和排序功能', () => {
    beforeEach(() => {
      const store = useProjectStore()
      store.projects = [
        { id: 1, name: 'Alpha Project', status: 'Active', createdAt: '2024-01-05', updatedAt: '2024-01-10' },
        { id: 2, name: 'Beta Project', status: 'Draft', createdAt: '2024-01-03', updatedAt: '2024-01-08' },
        { id: 3, name: 'Gamma Project', status: 'Completed', createdAt: '2024-01-01', updatedAt: '2024-01-06' },
        { id: 4, name: 'Delta Project', status: 'Active', createdAt: '2024-01-07', updatedAt: '2024-01-12' },
        { id: 5, name: 'Alpha Beta', status: 'Draft', createdAt: '2024-01-09', updatedAt: '2024-01-11' }
      ]
      store.resetFilters()
    })

    it('filteredProjects 初始应为所有项目', () => {
      const store = useProjectStore()
      expect(store.filteredProjects).toHaveLength(5)
    })

    it('statusFilter 应按状态筛选项目', () => {
      const store = useProjectStore()
      store.statusFilter = 'Active'
      expect(store.filteredProjects).toHaveLength(2)
      expect(store.filteredProjects.every(p => p.status === 'Active')).toBe(true)
    })

    it('searchQuery 应按名称和描述搜索', () => {
      const store = useProjectStore()
      store.searchQuery = 'alpha'
      expect(store.filteredProjects).toHaveLength(2)
      expect(store.filteredProjects.map(p => p.id).sort()).toEqual([1, 5])
    })

    it('searchQuery 搜索应不区分大小写', () => {
      const store = useProjectStore()
      store.searchQuery = 'ALPHA'
      expect(store.filteredProjects).toHaveLength(2)
    })

    it('sortBy=createdAt 应按创建日期排序', () => {
      const store = useProjectStore()
      store.sortBy = 'createdAt'
      store.sortOrder = 'asc'
      const sorted = store.filteredProjects
      expect(sorted[0].id).toBe(3)
      expect(sorted[4].id).toBe(5)
    })

    it('sortBy=name 应按名称排序', () => {
      const store = useProjectStore()
      store.sortBy = 'name'
      store.sortOrder = 'asc'
      const sorted = store.filteredProjects
      expect(sorted[0].name).toBe('Alpha Beta')
      expect(sorted[1].name).toBe('Alpha Project')
      expect(sorted[4].name).toBe('Gamma Project')
    })

    it('组合筛选和排序应正常工作', () => {
      const store = useProjectStore()
      store.statusFilter = 'Active'
      store.sortBy = 'updatedAt'
      store.sortOrder = 'desc'
      const filtered = store.filteredProjects
      expect(filtered).toHaveLength(2)
      expect(filtered[0].id).toBe(4)
      expect(filtered[1].id).toBe(1)
    })
  })

  describe('10. 分页功能', () => {
    beforeEach(() => {
      const store = useProjectStore()
      store.projects = Array.from({ length: 20 }, (_, i) => ({
        id: i + 1,
        name: `Project ${i + 1}`,
        status: 'Active',
        createdAt: `2024-01-${String(i + 1).padStart(2, '0')}`
      }))
      store.resetFilters()
    })

    it('paginatedProjects 应返回当前页的数据', () => {
      const store = useProjectStore()
      store.pageSize = 9
      expect(store.paginatedProjects).toHaveLength(9)
      expect(store.paginatedProjects[0].id).toBe(20)
    })

    it('totalPages 应正确计算', () => {
      const store = useProjectStore()
      store.pageSize = 9
      expect(store.totalPages).toBe(3)
      store.pageSize = 10
      expect(store.totalPages).toBe(2)
    })

    it('setPage 应限制在有效范围内', () => {
      const store = useProjectStore()
      store.pageSize = 9
      store.setPage(10)
      expect(store.currentPage).toBe(3)
      store.setPage(0)
      expect(store.currentPage).toBe(1)
    })

    it('setPageSize 应重置页码', () => {
      const store = useProjectStore()
      store.currentPage = 3
      store.pageSize = 9
      store.setPageSize(10)
      expect(store.currentPage).toBe(1)
      expect(store.pageSize).toBe(10)
    })

    it('筛选后分页应基于过滤结果', () => {
      const store = useProjectStore()
      store.statusFilter = 'Active'
      store.searchQuery = 'Project 20'
      expect(store.filteredProjects).toHaveLength(1)
      expect(store.totalPages).toBe(1)
    })
  })

  describe('11. setFilter 和 resetFilters', () => {
    it('setFilter 应设置指定的筛选条件', () => {
      const store = useProjectStore()
      store.setFilter({ status: 'Active', search: 'test', sortBy: 'name', sortOrder: 'asc', currentPage: 2, pageSize: 6 })
      expect(store.statusFilter).toBe('Active')
      expect(store.searchQuery).toBe('test')
      expect(store.sortBy).toBe('name')
      expect(store.sortOrder).toBe('asc')
      expect(store.currentPage).toBe(2)
      expect(store.pageSize).toBe(6)
    })

    it('setFilter 应只更新指定的字段', () => {
      const store = useProjectStore()
      store.setFilter({ status: 'Completed' })
      expect(store.statusFilter).toBe('Completed')
      expect(store.searchQuery).toBe('')
    })

    it('resetFilters 应重置所有筛选条件', () => {
      const store = useProjectStore()
      store.statusFilter = 'Active'
      store.searchQuery = 'test'
      store.sortBy = 'name'
      store.sortOrder = 'asc'
      store.currentPage = 3
      store.pageSize = 6

      store.resetFilters()

      expect(store.statusFilter).toBe('')
      expect(store.searchQuery).toBe('')
      expect(store.sortBy).toBe('createdAt')
      expect(store.sortOrder).toBe('desc')
      expect(store.currentPage).toBe(1)
      expect(store.pageSize).toBe(9)
    })
  })
})
