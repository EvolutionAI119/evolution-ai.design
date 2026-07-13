<template>
  <div class="project-detail-page">
    <el-breadcrumb separator="/" style="margin-bottom: 20px">
      <el-breadcrumb-item :to="{ path: '/projects' }">{{ $t('app.projects') }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ project.name }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="project-header">
      <div class="header-info">
        <h2>{{ project.name }}</h2>
        <p>{{ project.description }}</p>
        <div class="header-meta">
          <el-tag :type="getStatusType(project.status)" size="small">
            {{ getStatusText(project.status) }}
          </el-tag>
          <span class="meta-item">{{ $t('projectDetail.createdAt') }} {{ formatDateTime(project.created_at) }}</span>
          <span class="meta-item">{{ $t('projectDetail.updatedAt') }} {{ formatDateTime(project.updated_at) }}</span>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showUploadDialog = true">{{ $t('models.uploadModel') }}</el-button>
        <el-button type="success" @click="runWorkflow">{{ $t('projectDetail.executeWorkflow') }}</el-button>
      </div>
    </div>

    <div class="project-stats">
      <el-card class="stat-card">
        <div class="stat-value">{{ models.length }}</div>
        <div class="stat-label">{{ $t('projectDetail.modelCount') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ reports.length }}</div>
        <div class="stat-label">{{ $t('projectDetail.checkReports') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ workflows.length }}</div>
        <div class="stat-label">{{ $t('projectDetail.workflows') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ qualityRate }}%</div>
        <div class="stat-label">{{ $t('projectDetail.qualityRate') }}</div>
      </el-card>
    </div>

    <div class="project-content">
      <div class="content-section">
        <h3>{{ $t('projectDetail.modelFiles') }}</h3>
        <div class="models-list">
          <div
            v-for="model in models"
            :key="model.id"
            class="model-item"
          >
            <div class="model-icon">
              <el-icon><Picture /></el-icon>
            </div>
            <div class="model-info">
              <div class="model-name">{{ model.filename }}</div>
              <div class="model-meta">
                <span>{{ model.file_type }}</span>
                <span>{{ formatSize(model.file_size) }}</span>
              </div>
            </div>
            <div class="model-actions">
              <el-button type="text" @click="runTopology(model.id)">{{ $t('projectDetail.topologyOpt') }}</el-button>
              <el-button type="text" @click="runQuality(model.id)">{{ $t('projectDetail.qualityCheck') }}</el-button>
              <el-button type="text" @click="runHandover(model.id)">{{ $t('projectDetail.dataHandover') }}</el-button>
            </div>
          </div>
        </div>
        <div v-if="models.length === 0" class="empty-state">
          <el-icon><Picture /></el-icon>
          <p>{{ $t('projectDetail.noModels') }}</p>
        </div>
      </div>

      <div class="content-section">
        <h3>{{ $t('projectDetail.qualityReports') }}</h3>
        <el-table :data="reports" style="width: 100%" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="overall_score" :label="$t('quality.score')" width="100">
            <template #default="{ row }">
              <span :class="row.overall_score >= 80 ? 'score-pass' : 'score-fail'">
                {{ row.overall_score }}/100
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="passed" :label="$t('quality.result')" width="80">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'">
                {{ row.passed ? $t('quality.passed') : $t('quality.failed') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="$t('workflow.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('workflow.actions')" width="80">
            <template #default="{ row }">
              <el-button type="primary" link @click="viewReport(row)">{{ $t('projectDetail.view') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="reports.length === 0" class="empty-state">
          <el-icon><Document /></el-icon>
          <p>{{ $t('projectDetail.noReports') }}</p>
        </div>
      </div>
    </div>

    <el-dialog v-model="showUploadDialog" :title="$t('models.uploadModel')" width="500px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item :label="$t('models.modelFile')" required>
          <el-upload
            :action="uploadUrl"
            :data="{ project_id: projectId }"
            :on-success="handleUploadSuccess"
            :on-error="handleUploadError"
            :before-upload="beforeUpload"
            accept=".glb,.gltf,.obj,.stl,.fbx,.igs,.iges,.step,.stp"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">{{ $t('models.dragUpload') }}</div>
            <div class="el-upload__tip">{{ $t('models.uploadTip') }}</div>
          </el-upload>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Picture, Document, UploadFilled } from '@element-plus/icons-vue'
import { projectAPI, modelAPI, qualityAPI, workflowAPI, topologyAPI } from '../services/api'

const { t } = useI18n()
const route = useRoute()
const projectId = computed(() => parseInt(route.params.id))

const project = ref({
  id: 0,
  name: '',
  description: '',
  status: 'active',
  created_at: '',
  updated_at: ''
})

const models = ref([])
const reports = ref([])
const workflows = ref([])
const showUploadDialog = ref(false)

const uploadForm = ref({})
const uploadUrl = '/api/v1/models/upload/'

const qualityRate = computed(() => {
  if (reports.value.length === 0) return 0
  return Math.round(reports.value.filter(r => r.passed).length / reports.value.length * 100)
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
    active: t('projectDetail.active'),
    pending: t('projectDetail.pending'),
    completed: t('projectDetail.completed'),
    failed: t('projectDetail.failed')
  }
  return texts[status] || status
}

const formatDateTime = (date) => {
  return new Date(date).toLocaleString()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const loadProject = async () => {
  try {
    const response = await projectAPI.get(projectId.value)
    project.value = response.data
  } catch (error) {
    console.error('Failed to load project:', error)
  }
}

const loadModels = async () => {
  try {
    const response = await modelAPI.list(projectId.value)
    models.value = response.data
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const loadReports = async () => {
  try {
    const response = await qualityAPI.list(projectId.value)
    reports.value = response.data
  } catch (error) {
    console.error('Failed to load reports:', error)
  }
}

const loadWorkflows = async () => {
  try {
    const response = await workflowAPI.list(projectId.value)
    workflows.value = response.data
  } catch (error) {
    console.error('Failed to load workflows:', error)
  }
}

const beforeUpload = (file) => {
  const extensions = ['.glb', '.gltf', '.obj', '.stl', '.fbx', '.igs', '.iges', '.step', '.stp']
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  if (!extensions.includes(ext)) {
    alert(t('models.unsupportedFormat'))
    return false
  }
  if (file.size > 52428800) {
    alert(t('models.fileTooLarge'))
    return false
  }
  return true
}

const handleUploadSuccess = () => {
  showUploadDialog.value = false
  loadModels()
  alert(t('models.uploadSuccess'))
}

const handleUploadError = () => {
  alert(t('models.uploadFailed'))
}

const runTopology = async (modelId) => {
  try {
    await topologyAPI.optimize({ model_id: modelId })
    alert(t('projectDetail.topologyStarted'))
  } catch (error) {
    console.error('Topology optimization failed:', error)
    alert(t('projectDetail.topologyFailed'))
  }
}

const runQuality = async (modelId) => {
  try {
    await qualityAPI.check({ model_id: modelId })
    loadReports()
    alert(t('projectDetail.qualityStarted'))
  } catch (error) {
    console.error('Quality check failed:', error)
    alert(t('projectDetail.qualityFailed'))
  }
}

const runHandover = (modelId) => {
  alert(t('projectDetail.handoverPreparing', { id: modelId }))
}

const viewReport = async (report) => {
  alert(t('projectDetail.viewReport', { id: report.id }))
}

const runWorkflow = () => {
  alert(t('projectDetail.executeWorkflow'))
}

onMounted(() => {
  loadProject()
  loadModels()
  loadReports()
  loadWorkflows()
})
</script>

<style>
.project-detail-page { padding: 20px; }

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
}

.header-info h2 { margin: 0; font-size: 28px; }
.header-info p { margin: 10px 0 0 0; color: #666; }

.header-meta {
  display: flex;
  gap: 15px;
  margin-top: 10px;
  align-items: center;
}

.meta-item { font-size: 14px; color: #999; }

.project-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #007bff;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 5px;
}

.project-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.content-section h3 { margin-bottom: 15px; }

.models-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.model-icon {
  width: 45px;
  height: 45px;
  background: linear-gradient(135deg, #00d9ff, #0099cc);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 22px;
}

.model-info { flex: 1; }
.model-name { font-weight: bold; }
.model-meta { display: flex; gap: 15px; color: #999; font-size: 14px; margin-top: 5px; }

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
}

.empty-state .el-icon { font-size: 48px; margin-bottom: 10px; }

.score-pass { color: #00ff88; font-weight: bold; }
.score-fail { color: #ff4757; font-weight: bold; }
</style>