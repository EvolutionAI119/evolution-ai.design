<template>
  <div class="export-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('export.title') }}</h2>
        <p>{{ $t('export.subtitle') }}</p>
      </div>
    </div>

    <div class="export-container">
      <div class="export-panel">
        <el-card class="config-card">
          <template #header>
            <span>{{ $t('export.exportConfig') }}</span>
          </template>
          <el-form :model="exportForm" label-width="100px">
            <el-form-item :label="$t('export.selectModel')" required>
              <el-select v-model="exportForm.model_id" :placeholder="$t('common.pleaseSelect')">
                <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
              </el-select>
            </el-form-item>
            
            <el-form-item :label="$t('export.exportFormat')">
              <div class="format-grid">
                <div
                  v-for="fmt in availableFormats"
                  :key="fmt.key"
                  class="format-item"
                  :class="{ selected: exportForm.formats.includes(fmt.key) }"
                  @click="toggleFormat(fmt.key)"
                >
                  <div class="format-icon" :style="{ background: fmt.color }">
                    <el-icon><component :is="fmt.icon" /></el-icon>
                  </div>
                  <div class="format-name">{{ fmt.name }}</div>
                  <div class="format-desc">{{ fmt.description }}</div>
                </div>
              </div>
            </el-form-item>

            <el-form-item :label="$t('export.precision')">
              <el-input-number v-model="exportForm.precision" :min="0.001" :max="1" step="0.001" />
              <span class="precision-hint">{{ $t('export.precisionHint') }}</span>
            </el-form-item>

            <el-form-item :label="$t('export.metadata')">
              <el-checkbox v-model="exportForm.include_metadata">{{ $t('export.includeMetadata') }}</el-checkbox>
            </el-form-item>
          </el-form>

          <div class="export-button">
            <el-button type="primary" size="large" @click="startExport" :disabled="!exportForm.model_id || exportForm.formats.length === 0">
              <el-icon><Download /></el-icon>
              {{ $t('export.startExport') }}
            </el-button>
          </div>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>{{ $t('export.exportHistory') }}</span>
          </template>
          <div v-if="exportHistory.length === 0" class="empty-history">
            <p>{{ $t('export.noHistory') }}</p>
          </div>
          <div v-else class="history-list">
            <div
              v-for="(history, idx) in exportHistory"
              :key="idx"
              class="history-item"
            >
              <div class="history-header">
                <span class="history-title">{{ $t('export.model') }} {{ history.model_id }}</span>
                <span class="history-time">{{ history.timestamp }}</span>
              </div>
              <div class="history-formats">
                <el-tag
                  v-for="f in history.formats"
                  :key="f"
                  size="small"
                >{{ f }}</el-tag>
              </div>
              <div class="history-actions">
                <el-button type="text" size="small" @click="downloadFile(history.model_id, history.formats[0])">{{ $t('export.download') }}</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <div class="result-panel">
        <el-card class="result-card" v-if="exportResult">
          <template #header>
            <span>{{ $t('export.exportResult') }}</span>
          </template>
          <div class="result-summary">
            <div class="summary-item">
              <span class="summary-label">{{ $t('export.modelId') }}</span>
              <span class="summary-value">{{ exportResult.model_id }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">{{ $t('export.exportTime') }}</span>
              <span class="summary-value">{{ exportResult.export_time_ms }}ms</span>
            </div>
          </div>

          <div class="exported-files">
            <h4>{{ $t('export.exportedFiles') }}</h4>
            <div class="files-grid">
              <div
                v-for="file in exportResult.files"
                :key="file.filename"
                class="file-card"
              >
                <div class="file-icon" :style="{ background: getFormatColor(file.format) }">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="file-info">
                  <div class="file-name">{{ file.filename }}</div>
                  <div class="file-meta">
                    <span class="file-size">{{ formatSize(file.size) }}</span>
                    <span class="file-type">{{ file.format.toUpperCase() }}</span>
                  </div>
                </div>
                <div class="file-action">
                  <el-button type="primary" size="small" @click="downloadFile(exportResult.model_id, file.format)">
                    <el-icon><Download /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="formats-info">
          <template #header>
            <span>{{ $t('export.formatInfo') }}</span>
          </template>
          <div class="format-descriptions">
            <div class="format-desc-item">
              <span class="desc-format">GLB/GLTF</span>
              <span class="desc-text">{{ $t('export.glbDesc') }}</span>
            </div>
            <div class="format-desc-item">
              <span class="desc-format">STL</span>
              <span class="desc-text">{{ $t('export.stlDesc') }}</span>
            </div>
            <div class="format-desc-item">
              <span class="desc-format">OBJ</span>
              <span class="desc-text">{{ $t('export.objDesc') }}</span>
            </div>
            <div class="format-desc-item">
              <span class="desc-format">STEP/IGES</span>
              <span class="desc-text">{{ $t('export.stepDesc') }}</span>
            </div>
            <div class="format-desc-item">
              <span class="desc-format">JSON</span>
              <span class="desc-text">{{ $t('export.jsonDesc') }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Download, Document, Picture, Box, Cpu, Briefcase } from '@element-plus/icons-vue'
import { exportAPI, modelAPI } from '../services/api'

const { t } = useI18n()

const models = ref([])
const exportForm = ref({
  model_id: '',
  formats: [],
  precision: 0.01,
  include_metadata: true
})
const exportResult = ref(null)
const exportHistory = ref([])

const availableFormats = [
  { key: 'glb', name: 'GLB', description: 'GLTF Binary', icon: Box, color: '#00d9ff' },
  { key: 'gltf', name: 'GLTF', description: 'GLTF JSON', icon: Box, color: '#0099cc' },
  { key: 'stl', name: 'STL', description: '3D打印', icon: Picture, color: '#ff6b6b' },
  { key: 'obj', name: 'OBJ', description: t('export.objDesc'), icon: Picture, color: '#ffd93d' },
  { key: 'step', name: 'STEP', description: 'CAD交换', icon: Briefcase, color: '#6bcb77' },
  { key: 'iges', name: 'IGES', description: 'IGES', icon: Briefcase, color: '#4d96ff' },
  { key: 'json', name: 'JSON', description: t('export.jsonDesc'), icon: Document, color: '#9966ff' }
]

const formatColors = {
  glb: '#00d9ff', gltf: '#0099cc', stl: '#ff6b6b', obj: '#ffd93d',
  step: '#6bcb77', iges: '#4d96ff', json: '#9966ff'
}

const toggleFormat = (format) => {
  const idx = exportForm.value.formats.indexOf(format)
  if (idx > -1) {
    exportForm.value.formats.splice(idx, 1)
  } else {
    exportForm.value.formats.push(format)
  }
}

const getFormatColor = (format) => {
  return formatColors[format] || '#999'
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

const loadFormats = async () => {
  try {
    const response = await exportAPI.getFormats()
    console.log('Available formats:', response.data)
  } catch (error) {
    console.error('Failed to load formats:', error)
  }
}

const startExport = async () => {
  if (!exportForm.value.model_id || exportForm.value.formats.length === 0) return

  try {
    const response = await exportAPI.exportModel({
      model_id: exportForm.value.model_id,
      formats: exportForm.value.formats,
      precision: exportForm.value.precision,
      include_metadata: exportForm.value.include_metadata
    })
    exportResult.value = response.data

    exportHistory.value.unshift({
      model_id: exportForm.value.model_id,
      formats: exportForm.value.formats,
      timestamp: new Date().toLocaleString()
    })
  } catch (error) {
    console.error('Export failed:', error)
    alert(t('export.exportFailed'))
  }
}

const downloadFile = async (modelId, format) => {
  try {
    const response = await exportAPI.download(modelId, format)
    const blob = new Blob([response.data], { type: response.headers['content-type'] })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `model_${modelId}.${format}`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    console.error('Download failed:', error)
    alert(t('export.downloadFailed'))
  }
}

onMounted(() => {
  loadModels()
  loadFormats()
})
</script>

<style scoped>
.export-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.export-container {
  display: grid;
  grid-template-columns: minmax(400px, 55%) minmax(350px, 45%);
  gap: 25px;
}

.config-card { margin-bottom: 20px; }

.format-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.format-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px;
  border: 2px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.format-item:hover {
  border-color: #c0c4cc;
  background: #fafafa;
}

.format-item.selected {
  border-color: #00d9ff;
  background: rgba(0, 217, 255, 0.05);
  transform: translateY(-2px);
}

.format-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 22px;
  margin-bottom: 12px;
}

.format-name { font-weight: 600; font-size: 15px; }
.format-desc { font-size: 12px; color: #909399; margin-top: 4px; }

.precision-hint { margin-left: 12px; color: #909399; font-size: 12px; }

.export-button {
  margin-top: 25px;
  text-align: center;
}

.history-card { min-height: 280px; }

.empty-history {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.history-list { height: calc(100% - 50px); overflow-y: auto; }

.history-item {
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
}

.history-item:last-child { border-bottom: none; }

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.history-title { font-weight: 600; }
.history-time { font-size: 12px; color: #909399; }

.history-formats { margin-bottom: 10px; }

.result-card { min-height: 300px; }

.result-summary {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.summary-item { display: flex; flex-direction: column; }

.summary-label { font-size: 13px; color: #909399; }
.summary-value { font-size: 24px; font-weight: 600; color: #303133; }

.exported-files h4 { margin-bottom: 15px; font-size: 16px; }

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.file-card:hover {
  border-color: #00d9ff;
  box-shadow: 0 2px 12px rgba(0, 217, 255, 0.15);
}

.file-icon {
  width: 55px;
  height: 55px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.file-info { flex: 1; }

.file-name { font-weight: 600; font-size: 14px; color: #303133; }

.file-meta {
  display: flex;
  gap: 10px;
  margin-top: 6px;
}

.file-size { font-size: 12px; color: #909399; }

.file-type {
  font-size: 12px;
  color: #00d9ff;
  background: rgba(0, 217, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.formats-info { margin-top: 20px; }

.format-descriptions { display: flex; flex-direction: column; gap: 12px; }

.format-desc-item {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.desc-format {
  font-weight: 600;
  color: #00d9ff;
  min-width: 110px;
  flex-shrink: 0;
}

.desc-text { color: #606266; font-size: 14px; }

@media (max-width: 850px) {
  .export-container {
    grid-template-columns: 1fr;
  }
}
</style>
