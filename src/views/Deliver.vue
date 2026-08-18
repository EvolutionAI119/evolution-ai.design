<template>
  <div class="deliver-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">Data Deliver</h2>
        <p class="page-subtitle">Export your models in industry-standard formats with precision control</p>
      </div>
    </div>

    <el-card class="section-card">
      <template #header>
        <span class="section-title">Supported Formats</span>
      </template>
      <div class="formats-grid">
        <div
          class="format-card"
          v-for="format in formats"
          :key="format.key"
          :class="{ active: selectedFormats.includes(format.key) }"
          @click="toggleFormat(format.key)"
        >
          <div class="format-icon">{{ format.icon }}</div>
          <div class="format-name">{{ format.name }}</div>
          <div class="format-desc">{{ format.description }}</div>
        </div>
      </div>
    </el-card>

    <el-card class="section-card">
      <template #header>
        <span class="section-title">Precision Levels</span>
      </template>
      <div class="precision-grid">
        <div class="precision-item" v-for="level in precisionLevels" :key="level.key">
          <div class="precision-header">
            <span class="precision-name">{{ level.name }}</span>
            <span class="precision-tolerance">{{ level.tolerance }}</span>
          </div>
          <p class="precision-desc">{{ level.description }}</p>
          <div class="precision-uses">
            <el-tag size="small" effect="plain" v-for="use in level.useCases" :key="use">{{ use }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <el-card class="delivery-card">
      <template #header>
        <span class="section-title">Delivery Preparation</span>
      </template>
      <div class="delivery-content">
        <div class="delivery-form">
          <el-form label-position="top">
            <el-form-item label="Select Model">
              <el-select v-model="selectedModel" placeholder="Choose a model to export" class="full-width">
                <el-option v-for="model in models" :key="model.id" :label="model.name" :value="model.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="Precision Level">
              <el-select v-model="selectedPrecision" placeholder="Select precision level" class="full-width">
                <el-option v-for="level in precisionLevels" :key="level.key" :label="level.name" :value="level.key" />
              </el-select>
            </el-form-item>
            <el-form-item label="Output Formats">
              <div class="selected-formats">
                <el-tag
                  v-for="fmt in selectedFormatDetails"
                  :key="fmt.key"
                  closable
                  @close="toggleFormat(fmt.key)"
                  effect="dark"
                >
                  {{ fmt.name }}
                </el-tag>
                <span v-if="selectedFormats.length === 0" class="no-format">No formats selected</span>
              </div>
            </el-form-item>
          </el-form>
        </div>
        <div class="delivery-summary">
          <div class="summary-item">
            <span class="summary-label">Estimated File Size</span>
            <span class="summary-value">~24.5 MB</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Format Count</span>
            <span class="summary-value">{{ selectedFormats.length }} / {{ formats.length }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Quality Check</span>
            <span class="summary-value pass">Passed</span>
          </div>
          <el-button type="primary" class="prepare-btn" :disabled="!canPrepare" @click="prepareDelivery">
            <el-icon><Upload /></el-icon>
            <span>Prepare Delivery</span>
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { exportAPI, modelAPI } from '../api'

const selectedModel = ref('')
const selectedPrecision = ref('engineering')
const selectedFormats = ref(['iges', 'step', 'stl'])

const models = ref([
  { id: 1, name: 'EV-Sedan Concept v1' },
  { id: 2, name: 'SUV-A Platform' },
  { id: 3, name: 'Sports Coupe V2' },
  { id: 4, name: 'Hatchback Design' }
])

const formats = ref([
  { key: 'iges', name: 'IGES', icon: 'IG', description: 'Initial Graphics Exchange Specification' },
  { key: 'step', name: 'STEP', icon: 'ST', description: 'Standard for Exchange of Product data' },
  { key: 'jt', name: 'JT', icon: 'JT', description: 'Jupiter Tessellation - Siemens format' },
  { key: 'obj', name: 'OBJ', icon: 'OB', description: 'Wavefront Object format' },
  { key: 'glb', name: 'GLB', icon: 'GL', description: 'GL Transmission Format binary' },
  { key: 'stl', name: 'STL', icon: 'SL', description: 'Standard Tessellation Language' }
])

const precisionLevels = ref([
  { key: 'concept', name: 'Concept', tolerance: '±5mm', description: 'Quick concept exploration and early design reviews.', useCases: ['Sketching', 'Concept', 'Review'] },
  { key: 'verification', name: 'Verification', tolerance: '±1mm', description: 'Design verification and engineering feasibility studies.', useCases: ['Feasibility', 'Analysis', 'Prototyping'] },
  { key: 'engineering', name: 'Engineering', tolerance: '±0.1mm', description: 'Production-ready engineering surfaces with Class A quality.', useCases: ['Tooling', 'Production', 'Class A'] },
  { key: 'production', name: 'Production', tolerance: '±0.01mm', description: 'Highest precision for direct tooling and manufacturing.', useCases: ['NC Machining', 'Molds', 'Final Release'] }
])

const selectedFormatDetails = computed(() => {
  return formats.value.filter(f => selectedFormats.value.includes(f.key))
})

const canPrepare = computed(() => {
  return selectedModel.value && selectedFormats.value.length > 0
})

const toggleFormat = (key) => {
  const index = selectedFormats.value.indexOf(key)
  if (index > -1) {
    selectedFormats.value.splice(index, 1)
  } else {
    selectedFormats.value.push(key)
  }
}

const prepareDelivery = async () => {
  if (!canPrepare.value) {
    ElMessage.warning('Please select a model and at least one format')
    return
  }
  try {
    const response = await exportAPI.exportModel({
      model_id: selectedModel.value,
      formats: selectedFormats.value,
      precision: selectedPrecision.value
    })
    const result = response.data
    ElMessage.success(`Delivery prepared successfully: ${result.files.length} files exported`)
  } catch (error) {
    ElMessage.error('Delivery preparation failed')
  }
}
</script>

<style scoped>
.deliver-page {
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

.section-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.section-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 20px;
}

.section-card :deep(.el-card__body) {
  padding: 20px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.formats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}

.format-card {
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.format-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(74, 222, 128, 0.05);
}

.format-card.active {
  border-color: var(--accent);
  background: rgba(74, 222, 128, 0.1);
}

.format-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: var(--accent-bg);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  margin: 0 auto 12px;
}

.format-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.format-desc {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
}

.precision-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.precision-item {
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 18px;
}

.precision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.precision-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.precision-tolerance {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 3px 8px;
  border-radius: 4px;
}

.precision-desc {
  margin: 0 0 12px 0;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.precision-uses {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.precision-uses :deep(.el-tag) {
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  background: transparent;
}

.delivery-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.delivery-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 20px;
}

.delivery-card :deep(.el-card__body) {
  padding: 20px;
}

.delivery-content {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
}

.delivery-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-size: 13px;
}

.delivery-form :deep(.el-select__wrapper) {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: none;
}

.delivery-form :deep(.el-select__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.delivery-form :deep(.el-select__wrapper.is-focused) {
  border-color: var(--accent);
}

.delivery-form :deep(.el-select__placeholder) {
  color: var(--text-faint);
}

.delivery-form :deep(.el-select__input-inner) {
  color: var(--text-secondary);
}

.full-width {
  width: 100%;
}

.selected-formats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
}

.selected-formats :deep(.el-tag) {
  background: var(--accent-bg);
  border-color: rgba(74, 222, 128, 0.3);
  color: var(--accent);
}

.no-format {
  font-size: 13px;
  color: var(--text-faint);
}

.delivery-summary {
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-label {
  font-size: 13px;
  color: var(--text-muted);
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.summary-value.pass {
  color: var(--accent);
}

.prepare-btn {
  width: 100%;
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
  margin-top: 8px;
}

.prepare-btn:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
}
</style>
