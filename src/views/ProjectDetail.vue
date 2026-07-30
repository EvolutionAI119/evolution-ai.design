<template>
  <div class="project-detail-page">
    <div class="page-header">
      <div class="header-left">
        <el-button class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          <span>Back</span>
        </el-button>
        <div class="title-group">
          <h2 class="page-title">{{ project?.name || 'Project Details' }}</h2>
          <el-tag :type="getStatusType(project?.status)" effect="dark" size="small">{{ project?.status }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button @click="showEditDialog = true">
          <el-icon><Edit /></el-icon>
          <span>Edit</span>
        </el-button>
        <el-popconfirm
          title="Delete this project?"
          confirm-button-text="Delete"
          cancel-button-text="Cancel"
          confirm-button-type="danger"
          @confirm="handleDelete"
        >
          <template #reference>
            <el-button type="danger" plain>
              <el-icon><Delete /></el-icon>
              <span>Delete</span>
            </el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <div class="info-row">
      <div class="info-card">
        <div class="info-icon"><Clock /></div>
        <div class="info-content">
          <span class="info-label">Created</span>
          <span class="info-value">{{ project?.createdAt }}</span>
        </div>
      </div>
      <div class="info-card">
        <div class="info-icon"><Picture /></div>
        <div class="info-content">
          <span class="info-label">Models</span>
          <span class="info-value">{{ project?.modelCount }} files</span>
        </div>
      </div>
    </div>

    <div v-loading="projectStore.isLoading" class="main-content">
      <div class="left-panel">
        <div class="card">
          <div class="card-header">
            <span class="card-title">DESCRIPTION</span>
          </div>
          <div class="card-body">
            <p>{{ project?.description || 'No description available.' }}</p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">ACTIONS</span>
          </div>
          <div class="card-body actions-list">
            <el-button class="action-btn" @click="navigateToDesigner">
              <el-icon><Brush /></el-icon>
              <span>Open Designer</span>
            </el-button>
            <el-button class="action-btn" @click="showDocumentUpload = true">
              <el-icon><Upload /></el-icon>
              <span>Update Document</span>
            </el-button>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="card document-card">
          <div class="card-header">
            <span class="card-title">PROJECT DOCUMENT</span>
            <span class="doc-format">Markdown</span>
          </div>
          <div class="card-body document-body">
            <MarkdownRenderer v-if="project?.document" :content="project.document" />
            <div v-else class="no-document">
              <el-icon :size="48" class="no-doc-icon"><Document /></el-icon>
              <span class="no-doc-text">No document uploaded</span>
              <span class="no-doc-hint">Upload a .md file to add project documentation</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 技术选型决策矩阵（仅在有文档的项目展示） -->
    <div v-if="project?.document" class="tech-section">
      <TechSelectionMatrix />
    </div>

    <el-dialog v-model="showEditDialog" title="Edit Project" width="480px" class="edit-dialog">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="Project Name">
          <el-input v-model="editForm.name" placeholder="Enter project name" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="Brief description" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">Cancel</el-button>
        <el-button type="primary" class="btn-primary" @click="saveEdit">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDocumentUpload" title="Upload Document" width="480px" class="upload-dialog">
      <div class="upload-area-large" @click="triggerDocInput" @dragover.prevent @drop.prevent="handleDocDrop">
        <input
          ref="docInputRef"
          type="file"
          accept=".md,.txt"
          class="file-input"
          @change="handleDocSelect"
        />
        <el-icon :size="48" class="upload-icon"><Upload /></el-icon>
        <span class="upload-text">Click or drag to upload .md file</span>
        <span v-if="uploading" class="upload-status">Uploading...</span>
      </div>
      <template #footer>
        <el-button @click="showDocumentUpload = false">Cancel</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Clock, Picture, Brush, Upload, Document, Delete } from '@element-plus/icons-vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import TechSelectionMatrix from '../components/TechSelectionMatrix.vue'
import { useProjectStore } from '../stores/project.js'

const route = useRoute()
const router = useRouter()
const docInputRef = ref(null)
const projectStore = useProjectStore()

const showEditDialog = ref(false)
const showDocumentUpload = ref(false)
const uploading = ref(false)

const editForm = ref({ name: '', description: '' })

const project = computed(() => projectStore.currentProject)

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

const loadProject = async () => {
  const projectId = route.params.id
  if (!projectId) return
  try {
    await projectStore.loadProject(projectId)
    if (projectStore.currentProject) {
      editForm.value = {
        name: projectStore.currentProject.name || '',
        description: projectStore.currentProject.description || ''
      }
    }
  } catch (err) {
    ElMessage.error(err.message || 'Failed to load project')
  }
}

const goBack = () => {
  router.push('/projects')
}

const saveEdit = async () => {
  if (!editForm.value.name.trim()) {
    ElMessage.warning('Please enter a project name')
    return
  }
  const projectId = route.params.id
  try {
    await projectStore.updateProject(projectId, {
      name: editForm.value.name,
      description: editForm.value.description
    })
    ElMessage.success('Project updated successfully')
    showEditDialog.value = false
  } catch (err) {
    ElMessage.error(err.message || 'Failed to update project')
  }
}

const handleDelete = async () => {
  const projectId = route.params.id
  try {
    await projectStore.deleteProject(projectId)
    ElMessage.success('Project deleted successfully')
    router.push('/projects')
  } catch (err) {
    ElMessage.error(err.message || 'Failed to delete project')
  }
}

const navigateToDesigner = () => {
  router.push('/designer')
}

const triggerDocInput = () => {
  docInputRef.value?.click()
}

const handleDocSelect = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    loadDocFile(file)
  }
}

const handleDocDrop = (event) => {
  const file = event.dataTransfer?.files?.[0]
  if (file && (file.name.endsWith('.md') || file.name.endsWith('.txt'))) {
    loadDocFile(file)
  } else if (file) {
    ElMessage.warning('Only .md and .txt files are allowed')
  }
}

const loadDocFile = (file) => {
  uploading.value = true
  const reader = new FileReader()
  reader.onload = (e) => {
    if (project.value) {
      project.value.document = e.target?.result || ''
    }
    uploading.value = false
    showDocumentUpload.value = false
    ElMessage.success('Document uploaded successfully')
  }
  reader.readAsText(file, 'utf-8')
}

onMounted(loadProject)
watch(() => route.params.id, loadProject)
</script>

<style scoped>
.project-detail-page {
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
  align-items: center;
  gap: 16px;
}

.back-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.back-btn:hover {
  border-color: rgba(74, 222, 128, 0.3);
  color: var(--text-primary);
}

.title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-row {
  display: flex;
  gap: 16px;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 20px;
  min-width: 200px;
}

.info-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--accent-bg);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 11px;
  color: var(--text-muted);
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.main-content {
  display: flex;
  gap: 16px;
}

.left-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-panel {
  flex: 1;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-body {
  padding: 16px;
}

.card-body p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.6;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  width: 100%;
  justify-content: flex-start;
  gap: 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  padding: 12px 16px;
}

.action-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.document-card {
  height: calc(100vh - 280px);
  display: flex;
  flex-direction: column;
}

.document-body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.doc-format {
  font-size: 11px;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 2px 8px;
  border-radius: 4px;
}

.no-document {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted);
}

.no-doc-icon {
  opacity: 0.3;
}

.no-doc-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.no-doc-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.edit-dialog :deep(.el-dialog),
.upload-dialog :deep(.el-dialog) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.edit-dialog :deep(.el-dialog__title),
.upload-dialog :deep(.el-dialog__title) {
  color: var(--text-primary);
}

.edit-dialog :deep(.el-form-item__label) {
  color: var(--text-secondary);
}

.edit-dialog :deep(.el-input__wrapper),
.edit-dialog :deep(.el-textarea__inner) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
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

.upload-area-large {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--bg-primary);
}

.upload-area-large:hover {
  border-color: var(--accent);
  background: var(--accent-bg);
}

.upload-icon {
  color: var(--text-muted);
  margin-bottom: 12px;
}

.upload-text {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
}

.upload-status {
  display: block;
  font-size: 12px;
  color: var(--accent);
  margin-top: 8px;
}

.file-input {
  display: none;
}

.tech-section {
  margin-top: 8px;
}
</style>