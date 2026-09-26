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

    <el-card class="section-card workflow-card">
      <template #header>
        <div class="workflow-header">
          <span class="section-title">{{ t('deliver.title') }}</span>
          <el-tag size="small" effect="dark" type="success">{{ sessionBackend }}</el-tag>
        </div>
      </template>
      <div class="workflow-content">
        <!-- Step 1: Import -->
        <div class="workflow-step">
          <div class="step-number">1</div>
          <div class="step-body">
            <h4 class="step-title">{{ t('deliver.step1') }}</h4>
            <el-tabs v-model="importTab">
              <el-tab-pane :label="t('deliver.tabInline')" name="inline">
                <el-input
                  v-model="inlineJson"
                  type="textarea"
                  :rows="4"
                  :placeholder="t('deliver.inlinePlaceholder')"
                />
                <el-button type="primary" size="small" class="mt-8" @click="importInline" :loading="loading.import">
                  {{ t('deliver.importBtn') }}
                </el-button>
              </el-tab-pane>

              <el-tab-pane :label="t('deliver.tabJson')" name="file">
                <div class="upload-hint" v-html="t('deliver.jsonHint')"></div>
                <el-upload
                  :auto-upload="true"
                  :show-file-list="false"
                  accept=".json"
                  :http-request="importFromUpload"
                >
                  <el-button type="primary" size="small" :loading="loading.import">Upload JSON File</el-button>
                </el-upload>
              </el-tab-pane>

              <el-tab-pane :label="t('deliver.tabCad')" name="cad">
                <div class="upload-hint cad-hint">{{ t('deliver.cadHint') }}</div>
                <el-upload
                  :auto-upload="true"
                  :show-file-list="true"
                  :limit="1"
                  accept=".step,.stp,.iges,.igs,.stl,.obj,.glb,.gltf,.catpart,.catproduct,.cgr,.wire,.wrl"
                  :http-request="importFromUpload"
                >
                  <el-button type="success" size="small" :loading="loading.import">
                    <el-icon style="vertical-align: -2px; margin-right: 4px"><Upload /></el-icon>
                    {{ t('deliver.cadBtn') }}
                  </el-button>
                  <template #tip>
                    <div class="el-upload__tip">{{ t('deliver.cadTip') }}</div>
                  </template>
                </el-upload>
              </el-tab-pane>
            </el-tabs>

            <!-- Import warnings -->
            <div v-if="lastImportWarnings && lastImportWarnings.length" class="import-warnings">
              <el-alert
                v-for="(w, i) in lastImportWarnings"
                :key="i"
                :title="w"
                type="warning"
                :closable="false"
                show-icon
                class="mt-8"
              />
            </div>
            <!-- Import meta -->
            <div v-if="lastImportMeta" class="import-meta">
              <el-descriptions :column="2" size="small" border class="mt-8">
                <el-descriptions-item :label="t('deliver.metaSourceFormat')">
                  {{ lastImportMeta.source_format || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('deliver.metaOverrides')">
                  {{ lastImportMeta.overrides_count ?? '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('deliver.metaBbox')" v-if="lastImportMeta.bbox_size_mm">
                  {{ lastImportMeta.bbox_size_mm.map(v => Math.round(v)).join(' × ') }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('deliver.metaParsed')">
                  <el-tag size="small" :type="lastImportMeta.geometry_parsed ? 'success' : 'info'">
                    {{ lastImportMeta.geometry_parsed
                        ? t('deliver.metaParsedOk')
                        : t('deliver.metaParsedNo') }}
                  </el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>
        </div>

        <!-- Import Preview (after Step1, shows once we have a session) -->
        <div class="workflow-step preview-step" v-if="sessionId && lastImportPreview">
          <div class="step-number step-number-preview">◉</div>
          <div class="step-body">
            <h4 class="step-title">{{ t('deliver.importPreview') }}</h4>
            <div class="preview-ribbon">
              <el-tag size="small" type="info" effect="plain" class="mr-8">
                {{ sessionImageStateLabel(lastImportPreview, 'import-main') }}
              </el-tag>
              <span v-if="lastImportPreview.brand_key && lastImportPreview.model_key" class="preview-match">
                {{ lastImportPreview.brand_key }} / {{ lastImportPreview.model_key }}
              </span>
              <span v-else class="preview-match preview-match--fallback">
                {{ t('deliver.previewFallback') }}
              </span>
              <span class="preview-format">{{ lastImportPreview.source_format }}</span>
            </div>
            <div class="reference-image-container">
              <img
                :key="sessionImageRenderKey('import-main')"
                :src="sessionImageSrc(lastImportPreview, 'import-main')"
                :alt="lastImportPreview.model_key || 'imported'"
                class="reference-image"
                loading="lazy"
                @error="handleSessionImageError(lastImportPreview, 'import-main')"
              />
            </div>
          </div>
        </div>

        <!-- Step 2: Params -->
        <div class="workflow-step" v-if="sessionId">
          <div class="step-number">2</div>
          <div class="step-body">
            <h4 class="step-title">{{ t('deliver.step2') }} ({{ paramList.length }} params)</h4>
            <el-empty
              v-if="paramList.length === 0"
              :description="t('deliver.noSession')"
              :image-size="80"
            />
            <el-table v-else :data="paramList" size="small" max-height="360" class="param-table">
              <el-table-column :label="t('deliver.colName')" width="200">
                <template #default="{ row }">
                  <span :title="row.key">{{ paramLabel(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('deliver.colCurrent')" width="120">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.value"
                    :min="row.min_value"
                    :max="row.max_value"
                    :step="Math.abs(row.max_value - row.min_value) > 100 ? 1 : 0.1"
                    size="small"
                    style="width: 110px"
                  />
                </template>
              </el-table-column>
              <el-table-column :label="t('deliver.colUnit')" prop="unit" width="70" />
              <el-table-column :label="t('deliver.colRange')" width="150">
                <template #default="{ row }">
                  <span class="range-text">{{ row.min_value }} ~ {{ row.max_value }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('deliver.colGroup')">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain" :type="groupTagType(row.group_key)">
                    {{ groupLabel(row) }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <el-button type="warning" size="small" class="mt-8" @click="saveParams" :loading="loading.save">
              {{ t('deliver.applyBtn') }}
            </el-button>
          </div>
        </div>

        <!-- Step 3: Export -->
        <div class="workflow-step" v-if="sessionId">
          <div class="step-number">3</div>
          <div class="step-body">
            <h4 class="step-title">{{ t('deliver.step3') }}</h4>
            <div class="export-controls">
              <el-select v-model="exportFormats" multiple placeholder="Select formats" style="width: 320px">
                <el-option v-for="f in exportFmtOptions" :key="f" :label="f.toUpperCase()" :value="f" />
              </el-select>
              <el-button type="success" @click="exportModel" :loading="loading.export">
                {{ t('deliver.exportBtn') }}
              </el-button>
              <el-button @click="getSnapshot" :loading="loading.snapshot">
                {{ t('deliver.snapshotBtn') }}
              </el-button>
            </div>
            <div v-if="exportResult" class="export-result">
              <div v-for="f in exportResult.files" :key="f.filename" class="export-file">
                <span class="file-fmt">{{ f.format.toUpperCase() }}</span>
                <span class="file-name">{{ f.filename }}</span>
                <span class="file-size">{{ (f.size / 1024).toFixed(1) }} KB</span>
                <el-button size="small" text @click="downloadFile(f.filename)">Download</el-button>
              </div>
              <span class="export-time">Export time: {{ exportResult.export_time_ms }}ms</span>
            </div>
          </div>
        </div>

        <!-- Session List -->
        <div class="session-list" v-if="sessions.length">
          <el-divider contentPosition="left">
            {{ t('deliver.sessionsTitle') }} ({{ sessions.length }})
          </el-divider>
          <el-table :data="sessions" size="small">
            <el-table-column :label="t('deliver.previewCol')" width="72" align="center">
              <template #default="{ row }">
                <div class="session-thumb" :title="row.inferred_model_key || row.name">
                  <img
                    :key="sessionImageRenderKey('sess_' + row.session_id)"
                    :src="sessionImageSrc(_sessionPreview(row), 'sess_' + row.session_id)"
                    :alt="row.name"
                    loading="lazy"
                    @error="handleSessionImageError(_sessionPreview(row), 'sess_' + row.session_id)"
                  />
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="session_id" :label="t('deliver.sessionId')" width="140" />
            <el-table-column prop="name" :label="t('deliver.sessionName')" />
            <el-table-column prop="param_count" :label="t('deliver.sessionParams')" width="80" />
            <el-table-column prop="override_count" :label="t('deliver.sessionOverrides')" width="100" />
            <el-table-column :label="t('deliver.sessionActions')" width="140">
              <template #default="{ row }">
                <el-button size="small" text @click="loadSession(row.session_id)">
                  {{ t('deliver.sessionLoad') }}
                </el-button>
                <el-button size="small" text type="danger" @click="deleteSession(row.session_id)">
                  {{ t('deliver.sessionDelete') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
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
import { ref, computed, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { exportAPI, modelAPI, importExportAPI } from '../api'
import {
  getStaticPhotoPath,
  buildRuntimeSvgDataUrl,
  UNIVERSAL_FALLBACK,
  markUrlFailed,
  isUrlMarkedFailed,
} from '../utils/carImageManager.js'
import { useCarSessionImage } from '../utils/useCarSessionImage.js'

// 独立作用域：Deliver 下的图片状态与 Designer 的状态互不干扰（失败 attempt / minLayer 不串扰）
const {
  imageRenderKey: sessionImageRenderKey,
  imageSrc: _composableImgSrc,
  stateLabel: _composableStateLabel,
  handleImageError: _composableHandleError,
  resetState: resetSessionImageState,
} = useCarSessionImage('deliver', { maxAttempts: 5 })

const { t, locale } = useI18n({ useScope: 'global' })

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

// ============ Import -> Modify -> Export workflow ============
const importTab = ref('inline')
const inlineJson = ref(
  ''
)
const sessionId = ref('')
const sessionBackend = ref('memory')
const paramList = ref([])
const sessions = ref([])
const exportFormats = ref(['step', 'json'])
const exportResult = ref(null)
const exportFmtOptions = ['step', 'stl', 'obj', 'glb', 'gltf', 'iges', 'json']
const loading = reactive({ import: false, save: false, export: false, snapshot: false })
const lastImportWarnings = ref([])
const lastImportMeta = ref(null)
// 导入图片预览契约：后端返回的品牌/车型推断 + 当前会话 overrides 参数（用于 SVG 兜底绘制）
const lastImportPreview = ref(null)  // { brand_key, model_key, params, preview_url, source_format }

// ================= 图片预览（复用 useCarSessionImage，与 Designer.vue 完全一致的降级链） =================
/**
 * 统一入口：传入 preview 对象 + scopeKey，返回最终图片 src
 * - preview 形如 { brand_key, model_key, params, image?, source_format }
 * - 所有失败 attempt / minLayer 都写在 "deliver" scope 下，与 Designer 隔离
 */
const sessionImageSrc = (preview, scopeKey) => {
  if (!preview) return UNIVERSAL_FALLBACK
  return _composableImgSrc(scopeKey, { preview })
}
const sessionImageStateLabel = (_preview, scopeKey) => _composableStateLabel(scopeKey)
const handleSessionImageError = (preview, scopeKey) => {
  if (!preview) return
  _composableHandleError(scopeKey, { preview })
}
// 当用户重新 import 时重置当前预览 key 的 attempt，避免"上次失败记忆"污染这次
const resetImportPreviewState = () => {
  resetSessionImageState('import-main')
}
// 在实际 importInline/importFile 成功回调里会被调用（见下）


// i18n-aware labels for parameter/group cells (fallback to backend text)
const _tryT = (key, fallback) => {
  try {
    const out = t(key)
    // missing key in en: vue-i18n returns key itself; detect that to use fallback
    if (out === key) return fallback
    return out
  } catch {
    return fallback
  }
}
const paramLabel = (row) => _tryT(`params.${row.key}`, row.name || row.key)
const groupLabel = (row) => _tryT(`paramGroups.${row.group_key}`, row.group || row.group_key || 'General')

const groupTagType = (groupKey) => {
  switch (groupKey) {
    case 'overall_dimensions': return 'primary'
    case 'body_components': return 'success'
    case 'styling_angles': return 'warning'
    case 'class_a_params': return 'danger'
    case 'proportions': return 'info'
    default: return ''
  }
}

const fetchSessions = async () => {
  try {
    const res = await importExportAPI.listSessions()
    sessions.value = res.data.sessions || []
    sessionBackend.value = res.data.backend || 'memory'
  } catch { /* silent */ }
}

// sessions 行级 preview 对象（供缩略图列用）
const _sessionPreview = (row) => ({
  brand_key: row?.inferred_brand_key || '',
  model_key: row?.inferred_model_key || '',
  preview_url: row?.preview_url || '',
  source_format: row?.source_format || '',
  // sessions 列表接口不返回完整 overrides；SVG 兜底按默认参数绘制
  params: {},
})

const _captureImportResp = (resp) => {
  const d = resp.data || {}
  lastImportWarnings.value = (d.warnings || []).slice()
  const geomParsed = d.meta ? (d.meta.geometry_parsed ?? true) : true
  lastImportMeta.value = {
    source_format: d.source_format,
    bbox_size_mm: d.bbox_size_mm,
    overrides_count: d.overrides_count,
    geometry_parsed: geomParsed,
  }
  // 导入预览需要的品牌/车型 + 参数（overrides 映射成 SVG 所需的扁平 dict）
  const paramsMap = {}
  // 把 overrides（后端结构为 { "整车尺寸": { "overall_length": 4800 } }）映射成 SVG 所需 key -> value
  const overrides = d.overrides || (d.meta ? d.meta.overrides : null) || {}
  for (const gk of Object.keys(overrides)) {
    const items = overrides[gk] || {}
    for (const pk of Object.keys(items)) {
      paramsMap[pk] = items[pk]
    }
  }
  lastImportPreview.value = {
    brand_key: d.inferred_brand_key || '',
    model_key: d.inferred_model_key || '',
    preview_url: d.preview_url || '',
    source_format: d.source_format || '',
    params: paramsMap,
  }
}

const importInline = async () => {
  let body
  try {
    body = JSON.parse(inlineJson.value || '{}')
  } catch {
    ElMessage.error(t('deliver.msgJsonInvalid'))
    return
  }
  loading.import = true
  try {
    const res = await importExportAPI.importModel(body)
    sessionId.value = res.data.session_id
    ElMessage.success(t('deliver.msgImportOk', {
      name: res.data.name, count: res.data.param_count
    }))
    _captureImportResp(res)
    resetImportPreviewState()  // 新会话：重置预览卡片 attempt 状态，避免和上一次串扰
    await loadParams()
    await fetchSessions()
  } catch (err) {
    lastImportWarnings.value = []
    lastImportMeta.value = null
    ElMessage.error(t('deliver.msgImportFail', {
      detail: err.response?.data?.detail || err.message
    }))
  } finally {
    loading.import = false
  }
}

const importFromUpload = async (option) => {
  loading.import = true
  try {
    const res = await importExportAPI.importFile(option.file)
    sessionId.value = res.data.session_id
    const fmtMsg = res.data.source_format ? ` [${res.data.source_format}]` : ''
    ElMessage.success(t('deliver.msgFileImportOk', {
      name: `${res.data.name}${fmtMsg}`, count: res.data.param_count
    }))
    _captureImportResp(res)
    resetImportPreviewState()
    await loadParams()
    await fetchSessions()
  } catch (err) {
    lastImportWarnings.value = []
    lastImportMeta.value = null
    ElMessage.error(t('deliver.msgFileImportFail', {
      detail: err.response?.data?.detail || err.message
    }))
  } finally {
    loading.import = false
  }
}

const loadParams = async () => {
  if (!sessionId.value) return
  try {
    const res = await importExportAPI.getParams(sessionId.value)
    // save original for dirty-detection (backend group may be Chinese, also
    // remember group_key so PUT uses the stable English key)
    paramList.value = (res.data || []).map(p => ({ ...p, _original: p.value }))
  } catch (err) {
    ElMessage.error(t('deliver.msgLoadParamsFail', {
      detail: err.response?.data?.detail || err.message
    }))
  }
}

const saveParams = async () => {
  loading.save = true
  try {
    // Submit group_key (English stable key) for group field. Backend is
    // bilingual via GROUP_ZH_TO_EN / GROUP_EN_TO_ZH so English keys always
    // work regardless of how params were originally imported.
    const changed = paramList.value
      .filter(p => p.value !== p._original)
      .map(p => ({
        group: p.group_key || p.group,
        key: p.key,
        value: p.value
      }))
    if (!changed.length) {
      ElMessage.info(t('deliver.msgNoChange'))
      return
    }
    const res = await importExportAPI.modifyParams(sessionId.value, changed)
    ElMessage.success(t('deliver.msgModifyOk', { count: res.data.length }))
    res.data.forEach(updated => {
      const p = paramList.value.find(x => x.key === updated.key && (x.group_key === updated.group || x.group === updated.group))
      if (p) p._original = updated.value
    })
    await fetchSessions()
  } catch (err) {
    ElMessage.error(t('deliver.msgSaveFail', {
      detail: err.response?.data?.detail || err.message
    }))
  } finally {
    loading.save = false
  }
}

const exportModel = async () => {
  if (!exportFormats.value.length) {
    ElMessage.warning(t('deliver.msgNoFormat'))
    return
  }
  loading.export = true
  try {
    const res = await importExportAPI.exportModel(sessionId.value, exportFormats.value)
    exportResult.value = res.data
    ElMessage.success(t('deliver.msgExportOk', { count: res.data.files.length }))
  } catch (err) {
    ElMessage.error(t('deliver.msgExportFail', {
      detail: err.response?.data?.detail || err.message
    }))
  } finally {
    loading.export = false
  }
}

const getSnapshot = async () => {
  loading.snapshot = true
  try {
    const res = await importExportAPI.getSnapshot(sessionId.value)
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${res.data.name}_snapshot.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(t('deliver.msgSnapshotOk'))
  } catch (err) {
    ElMessage.error(t('deliver.msgSnapshotFail', {
      detail: err.response?.data?.detail || err.message
    }))
  } finally {
    loading.snapshot = false
  }
}

const downloadFile = async (filename) => {
  try {
    const res = await importExportAPI.downloadFile(sessionId.value, filename)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error(t('deliver.msgDownloadFail'))
  }
}

const loadSession = async (sid) => {
  sessionId.value = sid
  await loadParams()
  ElMessage.success(t('deliver.msgSessionLoaded'))
}

const deleteSession = async (sid) => {
  try {
    await ElMessageBox.confirm(t('deliver.msgDeleteConfirm'), t('deliver.msgDeleteTitle'), {
      type: 'warning',
      confirmButtonText: t('deliver.msgDeleteOk'),
      cancelButtonText: t('deliver.msgDeleteCancel')
    })
    await importExportAPI.deleteSession(sid)
    ElMessage.success(t('deliver.msgSessionDeleted'))
    if (sessionId.value === sid) {
      sessionId.value = ''
      paramList.value = []
    }
    await fetchSessions()
  } catch { /* user cancelled */ }
}

onMounted(() => {
  fetchSessions()
})
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

/* ============ 工作流样式 ============ */
.workflow-card {
  margin-bottom: 16px;
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workflow-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-step {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent-bg);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.mt-8 {
  margin-top: 8px;
}

.param-table {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.range-text {
  font-size: 11px;
  color: var(--text-muted);
}

.export-controls {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.export-result {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.export-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.file-fmt {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.file-size {
  font-size: 12px;
  color: var(--text-muted);
}

.export-time {
  font-size: 11px;
  color: var(--text-faint);
  margin-top: 4px;
}

.session-list {
  margin-top: 8px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
  line-height: 1.6;
}
.upload-hint code {
  background: var(--accent-bg);
  color: var(--accent);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}
.cad-hint strong {
  color: var(--text-primary);
}
.import-warnings .el-alert {
  font-size: 12px;
}
.import-meta :deep(.el-descriptions__label) {
  color: var(--text-muted);
  font-size: 12px;
  width: 160px;
}
.import-meta :deep(.el-descriptions__content) {
  font-size: 13px;
  color: var(--text-secondary);
}

.preview-step .step-number-preview {
  background: linear-gradient(135deg, var(--accent), #7c5cff);
}
.preview-ribbon {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-muted);
}
.preview-ribbon .mr-8 {
  margin-right: 8px;
}
.preview-match {
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.preview-match--fallback {
  color: var(--accent);
}
.preview-format {
  margin-left: auto;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.session-thumb {
  width: 56px;
  height: 40px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
}
.session-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
