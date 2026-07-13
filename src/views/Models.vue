<template>
  <div class="models-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('models.title') }}</h2>
        <p>{{ $t('models.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        {{ $t('models.uploadModel') }}
      </el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterProject" :placeholder="$t('models.projectFilter')">
        <el-option :label="$t('projects.all')" value="" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterType" :placeholder="$t('models.typeFilter')">
        <el-option :label="$t('projects.all')" value="" />
        <el-option label="GLB" value="GLB" />
        <el-option label="OBJ" value="OBJ" />
        <el-option label="STL" value="STL" />
        <el-option label="FBX" value="FBX" />
        <el-option label="IGES" value="IGES" />
        <el-option label="STEP" value="STEP" />
      </el-select>
      <el-input
        v-model="searchQuery"
        :placeholder="$t('models.search')"
        clearable
        prefix-icon="Search"
      />
    </div>

    <div class="models-grid">
      <el-card
        v-for="model in filteredModels"
        :key="model.id"
        class="model-card"
        @click="$router.push(`/projects/${model.project_id}`)"
      >
        <div class="model-icon">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="model-info">
          <div class="model-name">{{ model.filename }}</div>
          <div class="model-meta">
            <span class="model-type">{{ model.file_type }}</span>
            <span class="model-size">{{ formatSize(model.file_size) }}</span>
          </div>
          <div class="model-status">
            <el-tag :type="getStatusType(model.status)" size="small">
              {{ getStatusText(model.status) }}
            </el-tag>
          </div>
        </div>
        <div class="model-actions">
          <el-button type="text" @click.stop="downloadModel(model)">{{ $t('models.download') }}</el-button>
          <el-button type="text" @click.stop="deleteModel(model.id)">{{ $t('models.delete') }}</el-button>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showUploadDialog" :title="$t('models.uploadModel')" width="500px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item :label="$t('models.project')" required>
          <el-select v-model="uploadForm.project_id" :placeholder="$t('common.pleaseSelect')">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('models.modelFile')" required>
          <el-upload
            :action="uploadUrl"
            :data="{ project_id: uploadForm.project_id }"
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
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Upload, Picture, Search, UploadFilled } from '@element-plus/icons-vue'
import { modelAPI, projectAPI } from '../services/api'

const { t } = useI18n()

const models = ref([])
const projects = ref([])
const filterProject = ref('')
const filterType = ref('')
const searchQuery = ref('')
const showUploadDialog = ref(false)

const uploadForm = ref({
  project_id: ''
})

const uploadUrl = '/api/v1/models/upload/'

const filteredModels = computed(() => {
  return models.value.filter(model => {
    const matchProject = !filterProject.value || model.project_id === filterProject.value
    const matchType = !filterType.value || model.file_type === filterType.value
    const matchSearch = !searchQuery.value ||
      model.filename.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchProject && matchType && matchSearch
  })
})

const getStatusType = (status) => {
  const types = {
    uploaded: 'success',
    processing: 'warning',
    error: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    uploaded: t('models.uploaded'),
    processing: t('models.processing'),
    error: t('models.error')
  }
  return texts[status] || status
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const loadModels = async () => {
  try {
    const response = await modelAPI.list()
    models.value = response.data
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list()
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
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
  if (!uploadForm.value.project_id) {
    alert(t('models.selectProject'))
    return false
  }
  return true
}

const handleUploadSuccess = () => {
  showUploadDialog.value = false
  uploadForm.value.project_id = ''
  loadModels()
  alert(t('models.uploadSuccess'))
}

const handleUploadError = () => {
  alert(t('models.uploadFailed'))
}

const downloadModel = (model) => {
  window.open(model.filepath)
}

const deleteModel = async (id) => {
  if (!confirm(t('models.confirmDelete'))) return

  try {
    await modelAPI.delete(id)
    loadModels()
    alert(t('models.deleteSuccess'))
  } catch (error) {
    console.error('Failed to delete model:', error)
    alert(t('models.deleteFailed'))
  }
}

loadModels()
loadProjects()
</script>

<style scoped>
.models-page { padding: 20px; }

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
  gap: 15px;
  margin-bottom: 20px;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.model-card {
  display: flex;
  flex-direction: column;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e4e7ed;
}

.model-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  border-color: #00d9ff;
}

.model-icon {
  width: 70px;
  height: 70px;
  background: linear-gradient(135deg, #00d9ff, #0099cc);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 32px;
  margin-bottom: 15px;
}

.model-info { flex: 1; }
.model-name { font-weight: 600; font-size: 16px; margin-bottom: 8px; color: #303133; }
.model-meta { display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.model-type { font-size: 13px; color: #00d9ff; background: rgba(0, 217, 255, 0.1); padding: 3px 10px; border-radius: 4px; }
.model-size { font-size: 13px; color: #909399; }

.model-status { margin-bottom: 15px; }

.model-actions {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid #f0f0f0;
}
</style>