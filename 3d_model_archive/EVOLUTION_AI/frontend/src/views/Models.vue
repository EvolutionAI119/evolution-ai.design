<template>
  <div class="models-page">
    <div class="page-header">
      <div class="header-left">
        <h2>模型管理</h2>
        <p>上传和管理3D模型文件</p>
      </div>
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        上传模型
      </el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterProject" placeholder="项目筛选" style="width: 200px">
        <el-option label="全部" value="" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterType" placeholder="类型筛选" style="width: 150px">
        <el-option label="全部" value="" />
        <el-option label="GLB" value="GLB" />
        <el-option label="OBJ" value="OBJ" />
        <el-option label="STL" value="STL" />
        <el-option label="FBX" value="FBX" />
        <el-option label="IGES" value="IGES" />
        <el-option label="STEP" value="STEP" />
      </el-select>
      <el-input
        v-model="searchQuery"
        placeholder="搜索模型..."
        style="width: 250px"
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
              {{ model.status }}
            </el-tag>
          </div>
        </div>
        <div class="model-actions">
          <el-button type="text" @click.stop="downloadModel(model)">下载</el-button>
          <el-button type="text" @click.stop="deleteModel(model.id)">删除</el-button>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showUploadDialog" title="上传模型" width="500px">
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="项目" required>
          <el-select v-model="uploadForm.project_id" placeholder="请选择项目">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型文件" required>
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
            <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
            <div class="el-upload__tip">支持 GLB, OBJ, STL, FBX, IGES, STEP 格式</div>
          </el-upload>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Upload, Picture, Search, UploadFilled } from '@element-plus/icons-vue'
import { modelAPI, projectAPI } from '../services/api'

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
    alert('文件格式不支持，请上传GLB, OBJ, STL, FBX, IGES, STEP格式')
    return false
  }
  if (file.size > 52428800) {
    alert('文件大小不能超过50MB')
    return false
  }
  if (!uploadForm.value.project_id) {
    alert('请先选择项目')
    return false
  }
  return true
}

const handleUploadSuccess = () => {
  showUploadDialog.value = false
  uploadForm.value.project_id = ''
  loadModels()
  alert('模型上传成功')
}

const handleUploadError = () => {
  alert('模型上传失败')
}

const downloadModel = (model) => {
  window.open(model.filepath)
}

const deleteModel = async (id) => {
  if (!confirm('确定要删除这个模型吗？')) return

  try {
    await modelAPI.delete(id)
    loadModels()
    alert('模型删除成功')
  } catch (error) {
    console.error('Failed to delete model:', error)
    alert('模型删除失败')
  }
}

loadModels()
loadProjects()
</script>

<style>
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
  align-items: center;
  gap: 15px;
  cursor: pointer;
  transition: transform 0.2s;
}

.model-card:hover { transform: translateY(-5px); }

.model-icon {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #00d9ff, #0099cc);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 28px;
}

.model-info { flex: 1; }
.model-name { font-weight: bold; margin-bottom: 5px; }
.model-meta { display: flex; gap: 10px; margin-bottom: 5px; }
.model-type { font-size: 12px; color: #00d9ff; background: rgba(0, 217, 255, 0.1); padding: 2px 8px; border-radius: 4px; }
.model-size { font-size: 12px; color: #999; }

.model-actions { display: flex; gap: 10px; }
</style>