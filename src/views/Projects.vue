<template>
  <div class="projects-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">Projects</h2>
        <p class="page-subtitle">Manage and organize your design projects</p>
      </div>
      <el-button type="primary" class="btn-primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        <span>New Project</span>
      </el-button>
    </div>

    <div class="filter-bar">
      <el-input v-model="projectStore.searchQuery" placeholder="Search projects..." class="search-input" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="projectStore.statusFilter" placeholder="Filter by status" clearable class="filter-select">
        <el-option label="Active" value="Active" />
        <el-option label="Completed" value="Completed" />
        <el-option label="Draft" value="Draft" />
      </el-select>
      <el-select v-model="projectStore.sortBy" placeholder="Sort by" class="sort-select">
        <el-option label="Name" value="name" />
        <el-option label="Created Date" value="createdAt" />
        <el-option label="Updated Date" value="updatedAt" />
      </el-select>
      <el-button
        type="text"
        class="sort-order-btn"
        @click="toggleSortOrder"
        :title="projectStore.sortOrder === 'asc' ? 'Sort ascending' : 'Sort descending'"
      >
        <el-icon><ArrowUp v-if="projectStore.sortOrder === 'asc'" /><ArrowDown v-else /></el-icon>
      </el-button>
      <el-button type="text" class="reset-btn" @click="projectStore.resetFilters">
        <el-icon><RefreshLeft /></el-icon>
        <span>Reset</span>
      </el-button>
    </div>

    <div v-loading="projectStore.isLoading" class="projects-grid">
      <el-card
        v-for="project in projectStore.paginatedProjects"
        :key="project.id"
        class="project-card"
        @click="openProject(project.id)"
      >
        <div class="project-header">
          <div class="project-avatar" :class="(project.status || 'draft').toLowerCase()">
            <el-icon :size="20"><FolderOpened /></el-icon>
          </div>
          <div class="header-actions">
            <el-tag :type="getStatusType(project.status)" effect="dark" size="small">{{ project.status }}</el-tag>
            <el-popconfirm
              title="Delete this project?"
              confirm-button-text="Delete"
              cancel-button-text="Cancel"
              @confirm.stop="handleDelete(project.id)"
            >
              <template #reference>
                <el-button size="small" text type="danger" @click.stop>
                  <el-icon :size="14"><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
        <h3 class="project-name">{{ project.name }}</h3>
        <p class="project-desc">{{ project.description }}</p>
        <div class="project-footer">
          <div class="project-meta">
            <span class="meta-item">
              <el-icon :size="12"><Clock /></el-icon>
              <span>{{ formatDate(project.createdAt) }}</span>
            </span>
            <span class="meta-item">
              <el-icon :size="12"><Picture /></el-icon>
              <span>{{ project.modelCount || 0 }} models</span>
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <div v-if="projectStore.error" class="error-state">
      <el-icon :size="48" class="error-icon"><Warning /></el-icon>
      <p class="error-text">{{ projectStore.error }}</p>
      <el-button type="primary" @click="loadProjectsData">
        <el-icon><Refresh /></el-icon>
        <span>Retry</span>
      </el-button>
    </div>

    <div v-else-if="!projectStore.isLoading && projectStore.filteredProjects.length === 0" class="empty-state">
      <el-icon :size="48" class="empty-icon"><FolderOpened /></el-icon>
      <p class="empty-text">No projects found</p>
      <p class="empty-hint">Create your first project to get started</p>
    </div>

    <div v-if="!projectStore.isLoading && projectStore.filteredProjects.length > 0" class="pagination-bar">
      <span class="pagination-info">
        Showing {{ (projectStore.currentPage - 1) * projectStore.pageSize + 1 }} - 
        {{ Math.min(projectStore.currentPage * projectStore.pageSize, projectStore.filteredProjects.length) }} 
        of {{ projectStore.filteredProjects.length }} projects
      </span>
      <el-pagination
        v-model:current-page="projectStore.currentPage"
        v-model:page-size="projectStore.pageSize"
        :page-sizes="[6, 9, 12, 18]"
        :total="projectStore.filteredProjects.length"
        layout="total, sizes, prev, pager, next"
        class="pagination"
      />
    </div>

    <el-dialog v-model="showCreateDialog" title="Create New Project" width="480px" class="create-dialog">
      <el-form :model="projectForm" label-position="top">
        <el-form-item label="Project Name">
          <el-input v-model="projectForm.name" placeholder="Enter project name" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="projectForm.description" type="textarea" :rows="3" placeholder="Brief description of the project" />
        </el-form-item>
        <el-form-item label="Project Document (Markdown)">
          <div class="upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
            <input
              ref="fileInputRef"
              type="file"
              accept=".md,.txt"
              class="file-input"
              @change="handleFileSelect"
            />
            <el-icon :size="32" class="upload-icon"><Upload /></el-icon>
            <span class="upload-text">{{ projectForm.document ? 'Replace document' : 'Click or drag to upload .md file' }}</span>
            <span v-if="projectForm.document" class="upload-filename">{{ projectForm.documentName }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" class="btn-primary" @click="createProject">Create</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, FolderOpened, Clock, Picture, Upload, Delete, ArrowUp, ArrowDown, RefreshLeft, Warning, Refresh } from '@element-plus/icons-vue'
import { useProjectStore } from '../stores/project.js'

const router = useRouter()
const fileInputRef = ref(null)
const projectStore = useProjectStore()

const showCreateDialog = ref(false)
const projectForm = ref({ name: '', description: '', document: '', documentName: '' })

const toggleSortOrder = () => {
  projectStore.sortOrder = projectStore.sortOrder === 'asc' ? 'desc' : 'asc'
}

const getStatusType = (status) => {
  const types = { Active: 'success', Completed: 'info', Draft: 'warning' }
  return types[status] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toISOString().split('T')[0]
  } catch {
    return dateStr
  }
}

const openProject = (id) => {
  router.push(`/projects/${id}`)
}

const createProject = async () => {
  if (!projectForm.value.name.trim()) {
    ElMessage.warning('Please enter a project name')
    return
  }
  try {
    await projectStore.createProject({
      name: projectForm.value.name,
      description: projectForm.value.description,
      document: projectForm.value.document
    })
    ElMessage.success('Project created successfully')
    showCreateDialog.value = false
    projectForm.value = { name: '', description: '', document: '', documentName: '' }
  } catch (err) {
    ElMessage.error(err.message || 'Failed to create project')
  }
}

const handleDelete = async (id) => {
  try {
    await projectStore.deleteProject(id)
    ElMessage.success('Project deleted successfully')
  } catch (err) {
    ElMessage.error(err.message || 'Failed to delete project')
  }
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    loadFile(file)
  }
}

const handleDrop = (event) => {
  const file = event.dataTransfer?.files?.[0]
  if (file && (file.name.endsWith('.md') || file.name.endsWith('.txt'))) {
    loadFile(file)
  } else if (file) {
    ElMessage.warning('Only .md and .txt files are allowed')
  }
}

const loadFile = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    projectForm.value.document = e.target?.result || ''
    projectForm.value.documentName = file.name
    ElMessage.success(`Loaded: ${file.name}`)
  }
  reader.readAsText(file, 'utf-8')
}

const loadProjectsData = async () => {
  try {
    projectStore.clearError()
    await projectStore.loadProjects()
  } catch (err) {
    console.error('Failed to load projects:', err)
  }
}

onMounted(() => {
  loadProjectsData()
})
</script>

<style scoped>
.projects-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
}

.btn-primary:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  max-width: 360px;
}

.filter-select,
.sort-select {
  min-width: 140px;
}

.filter-select :deep(.el-input__wrapper),
.sort-select :deep(.el-input__wrapper) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.filter-select :deep(.el-input__wrapper:hover),
.sort-select :deep(.el-input__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.filter-select :deep(.el-input__wrapper.is-focus),
.sort-select :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent);
}

.sort-order-btn {
  padding: 6px 8px;
  color: var(--text-muted);
}

.sort-order-btn:hover {
  color: var(--accent);
}

.reset-btn {
  color: var(--text-muted);
  padding: 6px 12px;
}

.reset-btn:hover {
  color: var(--accent);
}

.search-input :deep(.el-input__wrapper) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: none;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent);
}

.search-input :deep(.el-input__inner) {
  color: var(--text-secondary);
}

.search-input :deep(.el-input__inner::placeholder) {
  color: var(--text-faint);
}

.search-input :deep(.el-input__prefix-inner),
.search-input :deep(.el-input__suffix-inner) {
  color: var(--text-muted);
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.project-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  transform: translateY(-2px);
}

.project-card :deep(.el-card__body) {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-avatar {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-avatar.active {
  background: var(--accent-bg);
  color: var(--accent);
}

.project-avatar.completed {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.project-avatar.draft {
  background: rgba(250, 204, 21, 0.15);
  color: #facc15;
}

.project-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.project-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-footer {
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.project-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.create-dialog :deep(.el-dialog) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.create-dialog :deep(.el-dialog__title) {
  color: var(--text-primary);
}

.create-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--text-muted);
}

.create-dialog :deep(.el-form-item__label) {
  color: var(--text-secondary);
}

.create-dialog :deep(.el-input__wrapper) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: none;
  border-radius: 8px;
}

.create-dialog :deep(.el-input__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.create-dialog :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent);
}

.create-dialog :deep(.el-input__inner) {
  color: var(--text-secondary);
}

.create-dialog :deep(.el-textarea__inner) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  box-shadow: none;
  border-radius: 8px;
  color: var(--text-secondary);
}

.create-dialog :deep(.el-textarea__inner:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.create-dialog :deep(.el-textarea__inner:focus) {
  border-color: var(--accent);
}

.create-dialog :deep(.el-dialog__footer) {
  padding-top: 0;
}

.create-dialog :deep(.el-button--default) {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
  border-radius: 8px;
}

.create-dialog :deep(.el-button--default:hover) {
  border-color: rgba(255, 255, 255, 0.3);
  color: var(--text-primary);
}

.upload-area {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--bg-primary);
}

.upload-area:hover {
  border-color: var(--accent);
  background: var(--accent-bg);
}

.upload-icon {
  color: var(--text-muted);
  margin-bottom: 8px;
}

.upload-text {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
}

.upload-filename {
  display: block;
  font-size: 12px;
  color: var(--accent);
  margin-top: 4px;
}

.file-input {
  display: none;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: #ef4444;
}

.error-icon {
  opacity: 0.6;
  margin-bottom: 8px;
}

.error-text {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #ef4444;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 8px;
  color: var(--text-muted);
}

.empty-icon {
  opacity: 0.3;
  margin-bottom: 8px;
}

.empty-text {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: var(--text-secondary);
}

.empty-hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-faint);
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-top: 1px solid var(--border-color);
}

.pagination-info {
  font-size: 13px;
  color: var(--text-muted);
}

.pagination :deep(.el-pagination) {
  color: var(--text-secondary);
}

.pagination :deep(.el-pager li) {
  color: var(--text-secondary);
}

.pagination :deep(.el-pager li:hover) {
  color: var(--accent);
}

.pagination :deep(.el-pager li.is-active) {
  background: var(--accent);
  color: var(--bg-primary);
}

.pagination :deep(.el-pagination__sizes .el-input__wrapper) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
}

.pagination :deep(.el-pagination__prev),
.pagination :deep(.el-pagination__next) {
  color: var(--text-secondary);
}

.pagination :deep(.el-pagination__prev:hover),
.pagination :deep(.el-pagination__next:hover) {
  color: var(--accent);
}
</style>
