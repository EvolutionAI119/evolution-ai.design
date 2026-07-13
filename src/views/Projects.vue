<template>
  <div class="projects-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('projects.title') }}</h2>
        <p>{{ $t('projects.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        {{ $t('projects.newProject') }}
      </el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterStatus" :placeholder="$t('projects.statusFilter')">
        <el-option :label="$t('projects.all')" value="" />
        <el-option :label="$t('projects.active')" value="active" />
        <el-option :label="$t('projects.pending')" value="pending" />
        <el-option :label="$t('projects.completed')" value="completed" />
        <el-option :label="$t('projects.failed')" value="failed" />
      </el-select>
      <el-input
        v-model="searchQuery"
        :placeholder="$t('projects.search')"
        clearable
        prefix-icon="Search"
      />
    </div>

    <div class="projects-grid">
      <el-card
        v-for="project in filteredProjects"
        :key="project.id"
        class="project-card"
        @click="$router.push(`/projects/${project.id}`)"
      >
        <div class="project-header">
          <div class="project-info">
            <h3 class="project-name">{{ project.name }}</h3>
            <p class="project-desc">{{ project.description || $t('projects.noDesc') }}</p>
          </div>
          <el-tag :type="getStatusType(project.status)" size="small" class="project-status">
            {{ getStatusText(project.status) }}
          </el-tag>
        </div>
        <div class="project-meta">
          <span class="meta-item">
            <el-icon><Clock /></el-icon>
            {{ formatDateTime(project.created_at) }}
          </span>
          <span class="meta-item">
            <el-icon><EditPen /></el-icon>
            {{ formatDateTime(project.updated_at) }}
          </span>
        </div>
        <div class="project-actions">
          <el-button type="primary" size="small" @click.stop="$router.push(`/projects/${project.id}`)">
            <el-icon><View /></el-icon>
            {{ $t('projects.detail') }}
          </el-button>
          <el-button type="success" size="small" @click.stop="editProject(project)">
            <el-icon><Edit /></el-icon>
            {{ $t('projects.edit') }}
          </el-button>
          <el-button type="danger" size="small" @click.stop="deleteProject(project.id)">
            <el-icon><Delete /></el-icon>
            {{ $t('projects.delete') }}
          </el-button>
        </div>
      </el-card>
    </div>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="projects.length"
      layout="total, prev, pager, next, jumper"
      :page-sizes="[10, 20, 50]"
    />

    <el-dialog v-model="showCreateDialog" :title="$t('projects.newProject')" width="500px">
      <el-form :model="projectForm" label-width="80px">
        <el-form-item :label="$t('projects.projectNameLabel')" required>
          <el-input v-model="projectForm.name" :placeholder="$t('projects.enterName')" />
        </el-form-item>
        <el-form-item :label="$t('projects.projectDescLabel')">
          <el-input v-model="projectForm.description" type="textarea" :placeholder="$t('common.pleaseInput')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createProject">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Search, Clock, EditPen, View, Edit, Delete } from '@element-plus/icons-vue'
import { projectAPI } from '../services/api'

const { t } = useI18n()

const projects = ref([])
const filterStatus = ref('')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const showCreateDialog = ref(false)

const projectForm = ref({
  name: '',
  description: ''
})

const filteredProjects = computed(() => {
  return projects.value.filter(project => {
    const matchStatus = !filterStatus.value || project.status === filterStatus.value
    const matchSearch = !searchQuery.value ||
      project.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchStatus && matchSearch
  })
})

const getStatusType = (status) => {
  const types = {
    active: 'success',
    pending: 'warning',
    completed: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: t('projects.active'),
    pending: t('projects.pending'),
    completed: t('projects.completed'),
    failed: t('projects.failed')
  }
  return texts[status] || status
}

const formatDateTime = (date) => {
  return new Date(date).toLocaleString()
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list(filterStatus.value || null)
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const createProject = async () => {
  if (!projectForm.value.name) {
    alert(t('projects.enterName'))
    return
  }

  try {
    await projectAPI.create(projectForm.value)
    showCreateDialog.value = false
    projectForm.value = { name: '', description: '' }
    await loadProjects()
    alert(t('projects.createSuccess'))
  } catch (error) {
    console.error('Failed to create project:', error)
    alert(t('projects.createFailed'))
  }
}

const editProject = (project) => {
  projectForm.value = { name: project.name, description: project.description }
  showCreateDialog.value = true
}

const deleteProject = async (id) => {
  if (!confirm(t('projects.confirmDelete'))) return

  try {
    await projectAPI.delete(id)
    await loadProjects()
    alert(t('projects.deleteSuccess'))
  } catch (error) {
    console.error('Failed to delete project:', error)
    alert(t('projects.deleteFailed'))
  }
}

loadProjects()
</script>

<style scoped>
.projects-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 20px;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.project-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e4e7ed;
}

.project-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  border-color: #00d9ff;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.project-info { flex: 1; }

.project-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.project-desc {
  margin: 0;
  font-size: 14px;
  color: #909399;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-status { flex-shrink: 0; margin-left: 15px; }

.project-meta {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #909399;
}

.project-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.el-pagination {
  display: flex;
  justify-content: center;
}
</style>