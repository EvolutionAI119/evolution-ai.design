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
      <el-input v-model="searchQuery" placeholder="Search projects..." class="search-input" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="projects-grid">
      <el-card
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-card"
        @click="openProject(project.id)"
      >
        <div class="project-header">
          <div class="project-avatar" :class="project.status.toLowerCase()">
            <el-icon :size="20"><FolderOpened /></el-icon>
          </div>
          <el-tag :type="getStatusType(project.status)" effect="dark" size="small">{{ project.status }}</el-tag>
        </div>
        <h3 class="project-name">{{ project.name }}</h3>
        <p class="project-desc">{{ project.description }}</p>
        <div class="project-footer">
          <div class="project-meta">
            <span class="meta-item">
              <el-icon :size="12"><Clock /></el-icon>
              <span>{{ project.createdAt }}</span>
            </span>
            <span class="meta-item">
              <el-icon :size="12"><Picture /></el-icon>
              <span>{{ project.modelCount }} models</span>
            </span>
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showCreateDialog" title="Create New Project" width="480px" class="create-dialog">
      <el-form :model="projectForm" label-position="top">
        <el-form-item label="Project Name">
          <el-input v-model="projectForm.name" placeholder="Enter project name" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="projectForm.description" type="textarea" :rows="3" placeholder="Brief description of the project" />
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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, FolderOpened, Clock, Picture } from '@element-plus/icons-vue'

const router = useRouter()

const searchQuery = ref('')
const showCreateDialog = ref(false)
const projectForm = ref({ name: '', description: '' })

const projects = ref([
  { id: 1, name: 'EV-Sedan Concept', description: 'Electric sedan concept design with aerodynamic optimization', status: 'Active', createdAt: '2026-07-10', modelCount: 12 },
  { id: 2, name: 'SUV-A Platform', description: 'SUV platform design for mid-size family vehicle', status: 'Completed', createdAt: '2026-07-08', modelCount: 24 },
  { id: 3, name: 'Sports Coupe V2', description: 'Second generation sports coupe design study', status: 'Active', createdAt: '2026-07-05', modelCount: 8 },
  { id: 4, name: 'Hatchback Design', description: 'Compact hatchback urban vehicle concept', status: 'Draft', createdAt: '2026-07-02', modelCount: 3 },
  { id: 5, name: 'Crossover Study', description: 'Crossover SUV coupe variant exploration', status: 'Completed', createdAt: '2026-06-28', modelCount: 18 },
  { id: 6, name: 'Pickup Truck EV', description: 'Electric pickup truck design program', status: 'Draft', createdAt: '2026-06-25', modelCount: 1 },
  { id: 7, name: 'Roadster Concept', description: 'Two-seater roadster sports car design', status: 'Active', createdAt: '2026-06-20', modelCount: 15 },
  { id: 8, name: 'Minivan Design', description: 'Family-oriented minivan interior and exterior', status: 'Completed', createdAt: '2026-06-15', modelCount: 20 },
  { id: 9, name: 'City Car EV', description: 'Ultra-compact city electric vehicle', status: 'Draft', createdAt: '2026-06-10', modelCount: 5 }
])

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projects.value
  const query = searchQuery.value.toLowerCase()
  return projects.value.filter(p =>
    p.name.toLowerCase().includes(query) ||
    p.description.toLowerCase().includes(query)
  )
})

const getStatusType = (status) => {
  const types = { Active: 'success', Completed: 'info', Draft: 'warning' }
  return types[status] || 'info'
}

const openProject = (id) => {
  router.push(`/projects/${id}`)
}

const createProject = () => {
  if (!projectForm.value.name.trim()) {
    ElMessage.warning('Please enter a project name')
    return
  }
  ElMessage.success('Project created successfully')
  showCreateDialog.value = false
  projectForm.value = { name: '', description: '' }
}
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
  color: #fff;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.btn-primary {
  background: #4ade80;
  border-color: #4ade80;
  color: #0a0a0f;
  font-weight: 600;
}

.btn-primary:hover {
  background: #22c55e;
  border-color: #22c55e;
  color: #0a0a0f;
}

.filter-bar {
  display: flex;
  gap: 12px;
}

.search-input {
  max-width: 360px;
}

.search-input :deep(.el-input__wrapper) {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  box-shadow: none;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #4ade80;
}

.search-input :deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.8);
}

.search-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.35);
}

.search-input :deep(.el-input__prefix-inner),
.search-input :deep(.el-input__suffix-inner) {
  color: rgba(255, 255, 255, 0.4);
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.project-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
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

.project-avatar {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-avatar.active {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
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
  color: #fff;
}

.project-desc {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-footer {
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
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
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.create-dialog :deep(.el-dialog__title) {
  color: #fff;
}

.create-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(255, 255, 255, 0.5);
}

.create-dialog :deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.7);
}

.create-dialog :deep(.el-input__wrapper) {
  background: #0a0a0f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: none;
  border-radius: 8px;
}

.create-dialog :deep(.el-input__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.create-dialog :deep(.el-input__wrapper.is-focus) {
  border-color: #4ade80;
}

.create-dialog :deep(.el-input__inner) {
  color: rgba(255, 255, 255, 0.8);
}

.create-dialog :deep(.el-textarea__inner) {
  background: #0a0a0f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: none;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.8);
}

.create-dialog :deep(.el-textarea__inner:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.create-dialog :deep(.el-textarea__inner:focus) {
  border-color: #4ade80;
}

.create-dialog :deep(.el-dialog__footer) {
  padding-top: 0;
}

.create-dialog :deep(.el-button--default) {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
}

.create-dialog :deep(.el-button--default:hover) {
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}
</style>
