import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectAPI } from '../api.js'

function snakeToCamel(obj) {
  if (!obj || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(snakeToCamel)
  const result = {}
  for (const key in obj) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
    result[camelKey] = snakeToCamel(obj[key])
  }
  return result
}

function camelToSnake(obj) {
  if (!obj || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(camelToSnake)
  const result = {}
  for (const key in obj) {
    const snakeKey = key.replace(/[A-Z]/g, c => '_' + c.toLowerCase())
    result[snakeKey] = camelToSnake(obj[key])
  }
  return result
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref([])
  const currentProject = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  const statusFilter = ref('')
  const searchQuery = ref('')
  const sortBy = ref('createdAt')
  const sortOrder = ref('desc')
  const currentPage = ref(1)
  const pageSize = ref(9)

  const recentProjects = computed(() =>
    [...projects.value]
      .sort((a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt))
      .slice(0, 5)
  )

  const filteredProjects = computed(() => {
    let result = [...projects.value]

    if (statusFilter.value) {
      result = result.filter(p => (p.status || '').toLowerCase() === statusFilter.value.toLowerCase())
    }

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(p =>
        (p.name || '').toLowerCase().includes(query) ||
        (p.description || '').toLowerCase().includes(query)
      )
    }

    result.sort((a, b) => {
      const aVal = a[sortBy.value] || ''
      const bVal = b[sortBy.value] || ''
      if (sortBy.value === 'createdAt' || sortBy.value === 'updatedAt') {
        return sortOrder.value === 'desc'
          ? new Date(bVal) - new Date(aVal)
          : new Date(aVal) - new Date(bVal)
      }
      return sortOrder.value === 'desc'
        ? bVal.localeCompare(aVal)
        : aVal.localeCompare(bVal)
    })

    return result
  })

  const paginatedProjects = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return filteredProjects.value.slice(start, end)
  })

  const totalPages = computed(() => {
    return Math.ceil(filteredProjects.value.length / pageSize.value)
  })

  async function loadProjects(status = null) {
    isLoading.value = true
    error.value = null
    try {
      const response = await projectAPI.list(status)
      projects.value = snakeToCamel(response.data || [])
      return projects.value
    } catch (err) {
      error.value = err.message || 'Failed to load projects'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadProject(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await projectAPI.get(id)
      const project = snakeToCamel(response.data)
      currentProject.value = project
      const idx = projects.value.findIndex(p => String(p.id) === String(id))
      if (idx !== -1) {
        projects.value[idx] = project
      }
      return project
    } catch (err) {
      error.value = err.message || 'Failed to load project'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createProject(data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await projectAPI.create(camelToSnake(data))
      const newProject = snakeToCamel(response.data)
      projects.value.unshift(newProject)
      currentProject.value = newProject
      return newProject
    } catch (err) {
      error.value = err.message || 'Failed to create project'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateProject(id, data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await projectAPI.update(id, camelToSnake(data))
      const updatedProject = snakeToCamel(response.data)
      const index = projects.value.findIndex(p => String(p.id) === String(id))
      if (index !== -1) {
        projects.value[index] = updatedProject
      }
      if (currentProject.value && String(currentProject.value.id) === String(id)) {
        currentProject.value = updatedProject
      }
      return updatedProject
    } catch (err) {
      error.value = err.message || 'Failed to update project'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function deleteProject(id) {
    isLoading.value = true
    error.value = null
    try {
      await projectAPI.delete(id)
      projects.value = projects.value.filter(p => String(p.id) !== String(id))
      if (currentProject.value && String(currentProject.value.id) === String(id)) {
        currentProject.value = null
      }
    } catch (err) {
      error.value = err.message || 'Failed to delete project'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function setCurrentProject(project) {
    currentProject.value = project
  }

  function clearError() {
    error.value = null
  }

  function setFilter(filter) {
    if (filter.status !== undefined) statusFilter.value = filter.status
    if (filter.search !== undefined) searchQuery.value = filter.search
    if (filter.sortBy !== undefined) sortBy.value = filter.sortBy
    if (filter.sortOrder !== undefined) sortOrder.value = filter.sortOrder
    if (filter.currentPage !== undefined) currentPage.value = filter.currentPage
    if (filter.pageSize !== undefined) pageSize.value = filter.pageSize
  }

  function resetFilters() {
    statusFilter.value = ''
    searchQuery.value = ''
    sortBy.value = 'createdAt'
    sortOrder.value = 'desc'
    currentPage.value = 1
    pageSize.value = 9
  }

  function setPage(page) {
    currentPage.value = Math.max(1, Math.min(page, totalPages.value || 1))
  }

  function setPageSize(size) {
    pageSize.value = size
    currentPage.value = 1
  }

  async function loadDesignIntoDesigner(projectId) {
    try {
      const project = await loadProject(projectId)
      const { useDesignerStore } = await import('./designer.js')
      const designer = useDesignerStore()
      designer.importFromProject(project)
      return designer
    } catch (err) {
      error.value = err.message || 'Failed to load design into designer'
      throw err
    }
  }

  async function saveDesignFromDesigner(projectId) {
    const { useDesignerStore } = await import('./designer.js')
    const designer = useDesignerStore()
    const designData = designer.exportToProject()
    
    try {
      const updated = await updateProject(projectId, {
        design_data: designData,
        updated_at: new Date().toISOString()
      })
      return updated
    } catch (err) {
      error.value = err.message || 'Failed to save design'
      throw err
    }
  }

  return {
    projects,
    currentProject,
    isLoading,
    error,
    statusFilter,
    searchQuery,
    sortBy,
    sortOrder,
    currentPage,
    pageSize,
    recentProjects,
    filteredProjects,
    paginatedProjects,
    totalPages,
    loadProjects,
    loadProject,
    createProject,
    updateProject,
    deleteProject,
    setCurrentProject,
    clearError,
    setFilter,
    resetFilters,
    setPage,
    setPageSize,
    loadDesignIntoDesigner,
    saveDesignFromDesigner
  }
})
