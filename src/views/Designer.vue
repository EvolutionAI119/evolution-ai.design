<template>
  <div class="designer-page">
    <div class="main-layout">
      <!-- Left Panel -->
      <div class="left-panel">
        <div class="card">
          <div class="card-header">
            <span class="card-title">{{ t('designer.carType') }}</span>
          </div>
          <div class="car-type-grid">
            <div
              v-for="ct in carTypes"
              :key="ct.key"
              class="car-type-card"
              :class="{ active: carType === ct.key }"
              @click="designer.setCarType(ct.key)"
            >
              <div class="car-type-icon">
                <svg viewBox="0 0 120 60" class="car-type-svg">
                  <path :d="getCarTypeSvg(ct.key)" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </div>
              <div class="car-type-name">{{ t('designer.' + ct.name) }}</div>
            </div>
          </div>
        </div>

        <div class="card card-brand">
          <div class="card-header">
            <span class="card-title">{{ t('designer.certifiedPresets') }}</span>
            <span class="card-badge">PRO</span>
          </div>
          <div class="brand-section">
            <div class="brand-list">
              <div
                v-for="b in brands"
                :key="b.key"
                class="brand-item"
                :class="{ active: brand === b.key }"
                @click="designer.setBrand(b.key)"
              >
                <span class="brand-dot" :style="{ background: b.color }"></span>
                <span class="brand-name">{{ b.name }}</span>
              </div>
            </div>
            <div class="model-list">
              <div
                v-for="model in currentBrandModels"
                :key="model.key"
                class="model-card"
                :class="{ active: selectedModel === model.key }"
                @click="designer.selectModel(model)"
              >
                <div class="model-image">
                  <img
                    :key="imageRenderKey(model.key)"
                    :src="getImageSrc(model)"
                    :alt="model.name"
                    class="model-img"
                    @error="handleImageError(model.key)"
                  />
                  <div v-if="getImageState(model.key) === 'loading'" class="img-loading-overlay">
                    <svg class="loading-spinner" viewBox="0 0 24 24">
                      <circle class="spinner-ring" cx="12" cy="12" r="10" fill="none" stroke-width="2"/>
                    </svg>
                  </div>
                </div>
                <div class="model-info">
                  <div class="model-name">{{ model.name }}</div>
                  <div class="model-spec">{{ model.params.overall_length }}mm</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Center Panel -->
      <div class="center-panel">
        <div class="center-header">
          <div class="center-title">
            <span class="title-main">{{ t('designer.centerTitle') }}</span>
            <span class="title-sub">{{ t('designer.centerSubtitle') }}</span>
          </div>
          <div class="center-tabs">
            <div class="center-tab active">
              <span class="tab-dot"></span>
              {{ t('designer.tabNurbsAclass') }}
            </div>
            <div class="center-tab">
              {{ t('designer.tabParametric') }}
            </div>
          </div>
          <button class="generate-btn" @click="generateCar" :disabled="generating">
            <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            <svg v-else class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <span>{{ generating ? t('designer.generating') : t('designer.generateCar') }}</span>
          </button>
        </div>
        <div class="viewport-row">
          <!-- Left Viewport - Base Model -->
          <div class="card viewport-card">
            <div class="viewport-header">
              <div class="viewport-tabs">
                <div class="viewport-tab" :class="{ active: baseModelTab === 'parametric' }" @click="baseModelTab = 'parametric'">
                  {{ t('designer.tabParametric') }}
                </div>
                <div class="viewport-tab active-green active" :class="{ active: baseModelTab === 'nurbs' }" @click="baseModelTab = 'nurbs'">
                  {{ t('designer.tabNurbsAclass') }}
                </div>
              </div>
            </div>
            <div class="viewport-container">
              <Car3D
                :car-params="carParams"
                :car-type="carType"
                car-color="#3b82f6"
                :view-angle="baseViewAngle"
                :wireframe="true"
                :nurbs-mesh="nurbsMeshData"
                @update:view-angle="baseViewAngle = $event"
              />
            </div>
          </div>

          <!-- Right Viewport - Live Preview -->
          <div class="card viewport-card">
            <div class="viewport-header">
              <div class="viewport-tabs">
                <div class="viewport-tab blue active" :class="{ active: previewTab === '3d' }" @click="previewTab = '3d'">
                  {{ t('designer.view3d') }}
                </div>
                <div class="viewport-tab blue" :class="{ active: previewTab === '2d' }" @click="previewTab = '2d'">
                  {{ t('designer.view2d') }}
                </div>
              </div>
            </div>
            <div class="viewport-container">
              <Car3D
                v-if="previewTab === '3d'"
                :car-params="carParams"
                :car-type="carType"
                :car-color="selectedColor"
                :view-angle="previewViewAngle"
                :wireframe="false"
                :nurbs-mesh="nurbsMeshData"
                @update:view-angle="previewViewAngle = $event"
              />
              <div v-else class="viewport-2d">
                <Car2D :car-params="carParams" :car-type="carType" />
              </div>
            </div>
          </div>
        </div>

        <div class="bottom-row">
          <div class="card reference-card">
            <div class="card-header">
              <span class="card-title">{{ t('designer.reference') }}</span>
              <div class="ref-tabs">
                <span class="ref-tab active">{{ t('designer.refSide') }}</span>
                <span class="ref-tab">{{ t('designer.refFront') }}</span>
                <span class="ref-tab">{{ t('designer.refTop') }}</span>
              </div>
            </div>
            <div class="reference-image-container">
              <template v-if="currentModel">
                <div class="reference-image-wrapper">
                  <img
                    :key="imageRenderKey(currentModel.key)"
                    :src="getImageSrc(currentModel)"
                    :alt="currentModel.name"
                    class="reference-img"
                    @error="handleImageError(currentModel.key)"
                  />
                  <div v-if="getImageState(currentModel.key) === 'loading'" class="ref-loading-overlay">
                    <svg class="ref-loading-spinner" viewBox="0 0 24 24">
                      <circle class="spinner-ring" cx="12" cy="12" r="10" fill="none" stroke-width="2"/>
                    </svg>
                    <span class="ref-loading-text">{{ t('designer.loadingHd') }}</span>
                  </div>
                </div>
                <div class="ref-model-info">
                  <span class="ref-model-name">{{ currentModel.name }}</span>
                  <span class="ref-model-spec">L:{{ carParams.overall_length }}mm W:{{ carParams.overall_width }}mm H:{{ carParams.overall_height }}mm</span>
                  <span v-if="getImageState(currentModel.key) === 'local-fallback'" class="ref-local-hint">{{ t('designer.localPreviewHint') }}</span>
                </div>
              </template>
              <div v-else class="reference-placeholder">
                <span>{{ t('designer.selectModelReference') }}</span>
              </div>
            </div>
          </div>

          <div class="card wireframe-card">
            <div class="card-header">
              <span class="card-title">{{ t('designer.render2d') }}</span>
            </div>
            <div class="wireframe-container">
              <Car2D :car-params="carParams" :car-type="carType" />
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel -->
      <div class="right-panel">
        <div class="card">
          <div class="card-header">
            <span class="card-title">{{ t('designer.bodyColor') }}</span>
          </div>
          <div class="color-grid">
            <div
              v-for="color in bodyColors"
              :key="color.value"
              class="color-swatch"
              :class="{ active: selectedColor === color.value }"
              :style="{ background: color.value }"
              @click="designer.selectColor(color.value)"
              :title="t('designer.' + color.name)"
            >
              <div v-if="selectedColor === color.value" class="color-check">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
            </div>
          </div>
          <div class="color-input-row">
            <input type="text" v-model="customColor" class="color-input" placeholder="#000000" />
            <button class="apply-btn" @click="applyCustomColor">{{ t('designer.apply') }}</button>
          </div>
        </div>

        <div class="card param-card">
          <div class="card-header">
            <span class="card-title">{{ t('designer.paramConfig') }}</span>
          </div>
          <div class="param-tabs">
            <div class="param-tab active" :class="{ active: paramTab === 'dimensions' }" @click="paramTab = 'dimensions'">
              {{ t('designer.dimensionParameters') }}
            </div>
            <div class="param-tab" :class="{ active: paramTab === 'styling' }" @click="paramTab = 'styling'">
              {{ t('designer.stylingParameters') }}
            </div>
          </div>
          <div class="param-list">
            <div v-if="paramTab === 'dimensions'" class="param-items">
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.overallLength') }}</span>
                  <span class="param-value">{{ carParams.overall_length }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.overall_length"
                  :min="carParams.wheel_base + 1000"
                  :max="carParams.wheel_base + 3800"
                  step="10"
                  class="param-slider"
                  @input="designer.onOverallLengthChange"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.overallWidth') }}</span>
                  <span class="param-value">{{ carParams.overall_width }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.overall_width"
                  min="1600"
                  max="2200"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.overallHeight') }}</span>
                  <span class="param-value">{{ carParams.overall_height }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.overall_height"
                  min="1100"
                  max="2000"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.wheelBase') }}</span>
                  <span class="param-value">{{ carParams.wheel_base }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.wheel_base"
                  :min="1800"
                  :max="carParams.overall_length - 1000"
                  step="10"
                  class="param-slider"
                  @input="designer.onWheelBaseChange"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.frontOverhang') }}</span>
                  <span class="param-value">{{ carParams.front_overhang }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.front_overhang"
                  :min="300"
                  :max="(carParams.overall_length - carParams.wheel_base) * 0.7"
                  step="10"
                  class="param-slider"
                  @input="designer.onOverhangChange"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.rearOverhang') }}</span>
                  <span class="param-value">{{ carParams.rear_overhang }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.rear_overhang"
                  :min="300"
                  :max="(carParams.overall_length - carParams.wheel_base) * 0.7"
                  step="10"
                  class="param-slider"
                  @input="designer.onOverhangChange"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.lengthFormula') }}</span>
                  <span class="param-value" style="color: #4ade80">{{ carParams.front_overhang }} + {{ carParams.wheel_base }} + {{ carParams.rear_overhang }} = {{ carParams.front_overhang + carParams.wheel_base + carParams.rear_overhang }}</span>
                </div>
              </div>
            </div>
            <div v-else class="param-items">
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.hoodLength') }}</span>
                  <span class="param-value">{{ carParams.hood_length }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.hood_length"
                  min="700"
                  max="1800"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.roofHeight') }}</span>
                  <span class="param-value">{{ carParams.roof_height }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.roof_height"
                  min="250"
                  max="1200"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.wheelDiameter') }}</span>
                  <span class="param-value">{{ carParams.wheel_diameter }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.wheel_diameter"
                  min="550"
                  max="850"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.windshieldAngle') }}</span>
                  <span class="param-value">{{ carParams.windshield_angle }}°</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.windshield_angle"
                  min="20"
                  max="60"
                  step="1"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.rearWindowAngle') }}</span>
                  <span class="param-value">{{ carParams.rear_window_angle }}°</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.rear_window_angle"
                  min="10"
                  max="60"
                  step="1"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">Rear Slant Angle</span>
                  <span class="param-value">{{ carParams.rear_slant_angle }}°</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.rear_slant_angle"
                  min="5"
                  max="60"
                  step="1"
                  class="param-slider"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- AI云端计算面板 -->
        <div class="card ai-cloud-card">
          <div class="card-header">
            <span class="card-title">AI CLOUD COMPUTE</span>
            <span class="card-badge cloud">CLOUD</span>
          </div>
          <div class="ai-actions">
            <button class="ai-btn" @click="aiTrain" :disabled="aiLoading">
              {{ aiLoading ? 'Computing...' : 'Generate Training Batch' }}
            </button>
            <button class="ai-btn" @click="aiEvaluateQuality" :disabled="aiLoading">
              Evaluate Quality
            </button>
            <button class="ai-btn" @click="aiGenerateDesign" :disabled="aiLoading">
              AI Generate Design
            </button>
            <button class="ai-btn" @click="aiOptimize" :disabled="aiLoading">
              Multi-Objective Optimize
            </button>
          </div>
          <div v-if="aiStats" class="ai-stats">
            <div class="ai-stat-row">
              <span class="ai-stat-label">Samples</span>
              <span class="ai-stat-val">{{ aiStats.total_samples }}</span>
            </div>
            <div class="ai-stat-row">
              <span class="ai-stat-label">Params</span>
              <span class="ai-stat-val">{{ aiStats.parameter_count }}</span>
            </div>
            <div class="ai-stat-row">
              <span class="ai-stat-label">Components</span>
              <span class="ai-stat-val">{{ aiStats.component_count }}</span>
            </div>
            <div class="ai-stat-row">
              <span class="ai-stat-label">NURBS</span>
              <span class="ai-stat-val">{{ aiStats.nurbs_surface_count }}</span>
            </div>
            <div class="ai-stat-row">
              <span class="ai-stat-label">Ctrl Points</span>
              <span class="ai-stat-val">{{ aiStats.control_points_total }}</span>
            </div>
          </div>
          <div v-if="aiResult" class="ai-result">
            <div class="ai-result-header">Last Cloud Result</div>
            <div class="ai-result-type">{{ aiResultType }}</div>
            <div class="ai-result-metrics" v-html="aiResultDisplay"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import Car3D from '../components/Car3D.vue'
import Car2D from '../components/Car2D.vue'
import { carTypes, brands, bodyColors } from '../config/carPresets'
import { carAPI, buildAPI, aiAPI } from '../api'
import { useDesignerStore } from '../stores/designer'
import { useAuthStore } from '../stores/auth'
import { generateCarSvg, generatePlaceholderSvg, getModelInitials } from '../utils/imageGenerator.js'
import {
  normalizeCarImageUrl,
  markUrlFailed,
  isUrlMarkedFailed,
  buildRuntimeSvgDataUrl,
  UNIVERSAL_FALLBACK,
  clearFailedMarks,
  verifyAllStaticPhotos,
  getStaticPhotoPath
} from '../utils/carImageManager.js'

const designer = useDesignerStore()
const auth = useAuthStore()
const { t } = useI18n({ useScope: 'global' })
const { carType, brand, selectedModel, selectedColor, params, generating } = storeToRefs(designer)

const customColor = ref('')
const baseModelTab = ref('nurbs')
const previewTab = ref('3d')
const paramTab = ref('dimensions')
const baseViewAngle = ref('perspective')
const previewViewAngle = ref('perspective')

// 最近一次生成的**实测**曲面质量快照（来自后端 nurbs_quality）。
// 后端此前把该字段硬编码为 g2_continuous: true 且未返回给前端，
// 现为真实测量结果，故在此保留以便如实展示。
const nurbsQuality = ref(null)

// 最近一次生成的真实 NURBS 采样网格，传给 Car3D 走高保真渲染路径；
// 未生成前为 null，视口保持参数化 fallback（游客态/Demo 不受影响）。
const nurbsMeshData = ref(null)

const carParams = params

const currentBrand = computed(() => {
  return brands.find(b => b.key === brand.value)
})

const currentBrandModels = computed(() => {
  return currentBrand.value ? currentBrand.value.models : []
})

const currentModel = computed(() => {
  if (!selectedModel.value) return null
  return currentBrandModels.value.find(m => m.key === selectedModel.value)
})

const getCarTypeSvg = (type) => {
  const paths = {
    sedan: 'M10,42 L15,42 Q10,30 20,25 L45,18 Q50,15 60,15 L85,15 Q95,15 100,22 L108,30 Q112,32 112,42 Z M30,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0 M92,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0',
    suv: 'M10,40 L10,22 Q10,12 25,10 L90,10 Q105,12 108,22 L112,30 Q115,32 115,40 Z M30,45 m-8,0 a8,8 0 1,0 16,0 a8,8 0 1,0 -16,0 M92,45 m-8,0 a8,8 0 1,0 16,0 a8,8 0 1,0 -16,0',
    coupe: 'M10,42 Q10,30 20,26 L40,20 Q50,10 70,10 L95,15 Q108,18 112,30 L115,42 Z M28,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0 M95,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0',
    sport: 'M8,44 Q8,36 15,32 L30,28 Q40,18 55,16 L90,18 Q105,20 112,32 L116,40 Q116,44 116,44 Z M28,46 m-6,0 a6,6 0 1,0 12,0 a6,6 0 1,0 -12,0 M98,46 m-6,0 a6,6 0 1,0 12,0 a6,6 0 1,0 -12,0',
    mpv: 'M10,40 L10,15 Q10,8 30,8 L100,8 Q110,8 112,15 L115,30 Q115,38 115,40 Z M30,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0 M95,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0',
    pickup: 'M10,42 L10,22 Q10,14 25,12 L60,12 Q65,12 68,14 L68,42 M72,42 L72,18 Q72,12 78,10 L108,10 Q115,10 116,18 L118,42 M30,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0 M100,45 m-7,0 a7,7 0 1,0 14,0 a7,7 0 1,0 -14,0'
  }
  return paths[type] || paths.sedan
}

const applyCustomColor = () => {
  if (customColor.value && /^#[0-9A-Fa-f]{6}$/.test(customColor.value)) {
    designer.selectColor(customColor.value)
  }
}

const imageStates = reactive({})

const ensureState = (key) => {
  if (!imageStates[key] || typeof imageStates[key] !== 'object') {
    imageStates[key] = { layer: 0, attempt: 0, renderKey: 0, minLayer: 0 }
  }
  return imageStates[key]
}

const getImageState = (key) => {
  const s = ensureState(key)
  if (s.layer === 3 || s.layer === 4) return 'local-fallback'
  if (s.attempt === 0 && s.layer === 0) return 'loading'
  return `L${s.layer}`
}

const imageRenderKey = (key) => {
  const s = ensureState(key)
  return `${key}__r${s.renderKey}`
}

/**
 * 显式指定 minLayer：让 normalizeCarImageUrl 从"至少 minLayer 之后"解析，
 * 解决"失败记忆 + online 环境 localStorage 污染"导致永远卡在 L1 的问题。
 */
const resolveByLayer = (model, bk, minLayer = 0) => {
  const all = []
  // 1) 本地 JPG
  const staticPath = getStaticPhotoPath(bk, model?.key || 'x')
  if (staticPath && !isUrlMarkedFailed(staticPath)) {
    all.push({ src: staticPath, layer: 1 })
  }
  // 2) 远程 AI 生成图
  if (model?.image && !isUrlMarkedFailed(model.image)) {
    all.push({ src: model.image, layer: 2 })
  }
  // 3) 运行时 SVG
  const svg = buildRuntimeSvgDataUrl(model, bk)
  if (svg) all.push({ src: svg, layer: 3 })
  // 4) 终极兜底
  all.push({ src: UNIVERSAL_FALLBACK, layer: 4 })

  const chosen = all.find(a => a.layer > minLayer) || all[all.length - 1]
  return { ...chosen, key: model?.key || 'x', brandKey: bk }
}

/**
 * 统一解析车型图片：4 层兜底 + 渲染中不做 reactive 副作用
 */
const getImageSrc = (model) => {
  if (!model) return UNIVERSAL_FALLBACK
  const bk = getBrandKeyForModel(model.key)
  const state = ensureState(model.key)
  const resolved = resolveByLayer(model, bk, state.minLayer || 0)
  // 记录当前 layer，不做赋值触发重渲染（渲染期写 reactive 会告警/递归）
  state.layer = resolved.layer
  return resolved.src
}

const getBrandKeyForModel = (modelKey) => {
  for (const b of brands) {
    if (b.models.some(m => m.key === modelKey)) {
      return b.key
    }
  }
  return 'default'
}

const prepareModelImage = (model) => {
  if (!model) return
  const s = ensureState(model.key)
  s.layer = 0
  s.attempt = 0
  s.renderKey = 0
  s.minLayer = 0
}

/**
 * 图片加载失败处理（确定性降级，不再依赖 localStorage 隐式跳过）：
 *   1. 当前失败 URL 若不是 data:，记入失败名单（远程 / 本地 JPG 都记；但 carImageManager 已会忽略 /brands/*）
 *   2. state.minLayer = 当前 layer → 下次解析直接从下一层开始
 *   3. renderKey++ → Vue 强制重新挂载 <img :key>，保证 onerror 二次触发可用
 *   4. attempt <= 5 防护，到顶直接锁定 L4 dataURL
 */
const MAX_ATTEMPTS = 5
const handleImageError = (modelKey) => {
  const model = getModelByKey(modelKey)
  if (!model) return
  const bk = getBrandKeyForModel(modelKey)
  const state = ensureState(modelKey)
  state.attempt++

  // 先把本次失败的 src（按当前 minLayer 解析所得）标记失败
  const resolved = resolveByLayer(model, bk, state.minLayer || 0)
  if (resolved.src && !resolved.src.startsWith('data:')) {
    markUrlFailed(resolved.src)
  }

  if (state.attempt >= MAX_ATTEMPTS) {
    // 兜底：直接锁定 L4
    state.minLayer = 4
    state.renderKey++
    return
  }

  // 从下一层开始解析
  state.minLayer = Math.max(state.minLayer || 0, resolved.layer)
  // 超过 L3 就锁在 L4（避免 attempt 耗尽前跑乱）
  if (state.minLayer >= 4) state.minLayer = 4
  state.renderKey++
}

const cleanupImageCache = () => {
  clearFailedMarks()
  Object.keys(imageStates).forEach(k => {
    prepareModelImage({ key: k })
  })
}

const getModelByKey = (modelKey) => {
  for (const brand of brands) {
    for (const model of brand.models) {
      if (model.key === modelKey) {
        return model
      }
    }
  }
  return null
}

const preloadAllImages = async () => {
  brands.forEach(brand => {
    brand.models.forEach(model => prepareModelImage(model))
  })
  // 开发环境：静默自检静态 SVG 数量，方便排查
  if (typeof window !== 'undefined' && window.location?.hostname === 'localhost') {
    try {
      const r = await verifyAllStaticPhotos(brands)
      console.log(`[CarImage] Static photo availability: ${r.ok}/${r.expected}`)
      if (r.ok < r.expected) {
        const missing = r.total.filter(i => i.status !== 'ok')
        console.warn('[CarImage] Missing static photos (fallback layer kicks in):', missing)
      }
    } catch (_) { /* ignore */ }
  }
}

const generateCar = async () => {
  // 模型生成服务需登录：游客触发时弹友好登录引导，不强制跳转
  if (!auth.isAuthenticated) {
    window.dispatchEvent(new CustomEvent('evoai:auth-required'))
    return
  }
  designer.setGenerating(true)
  try {
    const response = await carAPI.generate({
      car_type: carType.value,
      params: carParams.value,
      color: selectedColor.value
    })
    const data = response.data
    console.log('Car generated:', data)
    if (data.components && data.components.length > 0) {
      const q = data.nurbs_quality || {}
      const nSurf = q.surface_count || data.total_surfaces
      const nCp = q.control_points_total || 0
      // 实测质量：后端此前把 g2_continuous 硬编码为 true 且未返回，
      // 现改为真实测量结果。这里如实展示，避免给用户"恒定通过"的错觉。
      let quality = ''
      if (q.measured) {
        quality = q.g2_continuous
          ? ' | G2 连续（实测）'
          : ` | G2 未达标（实测：${q.n_flat_surfaces || 0} 个平面曲面）`
      }
      const type = q.g2_continuous === false ? 'warning' : 'success'
      ElMessage({
        type,
        message: `已生成 ${data.components.length} 个部件 | ${nSurf} 个 NURBS 曲面 | ${nCp} 个控制点${quality}`,
        duration: 6000
      })
      // 保留实时质量快照，供面板/后续对照使用
      nurbsQuality.value = q
      // 组装真实 NURBS 网格：曲面部件取采样点，车轮取几何参数。
      // 轮子部件无 points（只有 radius/width/position），需单独提取。
      nurbsMeshData.value = {
        parts: data.components
          .filter(c => c.points && c.points.length)
          .map(c => ({
            name: c.name,
            type: c.type,
            points: c.points,
            color: c.color,
            opacity: c.opacity
          })),
        wheels: data.components
          .filter(c => c.type === 'wheel' && c.radius)
          .map(c => ({
            radius: c.radius,
            width: c.width,
            position: c.position
          }))
      }
    } else {
      ElMessage.success('Car generated successfully')
    }
  } catch (error) {
    console.error('Failed to generate car:', error)
    ElMessage.error('Failed to generate car. Please try again.')
  } finally {
    designer.setGenerating(false)
  }
}

// ============ AI云端计算 ============
const aiLoading = ref(false)
const aiStats = ref(null)
const aiResult = ref(null)
const aiResultType = ref('')

const aiResultDisplay = computed(() => {
  if (!aiResult.value) return ''
  const r = aiResult.value
  const lines = []
  for (const [k, v] of Object.entries(r)) {
    if (typeof v === 'object' && v !== null) {
      for (const [k2, v2] of Object.entries(v)) {
        if (typeof v2 !== 'object') {
          lines.push(`<div class="metric-line"><span class="metric-k">${k}.${k2}</span><span class="metric-v">${v2}</span></div>`)
        }
      }
    } else {
      lines.push(`<div class="metric-line"><span class="metric-k">${k}</span><span class="metric-v">${v}</span></div>`)
    }
  }
  return lines.join('')
})

const loadAiStats = async () => {
  try {
    const res = await aiAPI.getDatasetStats()
    aiStats.value = res.data
  } catch (e) {
    console.warn('AI stats not available:', e)
  }
}

const aiTrain = async () => {
  aiLoading.value = true
  aiResultType.value = 'Training Batch (Cloud)'
  try {
    const res = await aiAPI.trainBatch({ batch_size: 100, car_type: carType.value })
    aiResult.value = {
      batch_size: res.data.batch_size,
      compute_time_ms: res.data.compute_time_ms + 'ms',
      total_generated: res.data.total_generated,
      cloud_compute: res.data.cloud_compute
    }
    ElMessage.success(`Cloud: Generated ${res.data.batch_size} samples in ${res.data.compute_time_ms}ms`)
    await loadAiStats()
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'common.error'))
  } finally {
    aiLoading.value = false
  }
}

const aiEvaluateQuality = async () => {
  aiLoading.value = true
  aiResultType.value = 'Quality Evaluation (Cloud)'
  try {
    const res = await aiAPI.evaluateQuality({
      surface_data: { style: 'modern', ...carParams.value },
      style: 'modern'
    })
    aiResult.value = {
      quality_metrics: res.data.quality_metrics,
      g2_passed: res.data.g2_passed,
      overall_pass: res.data.overall_pass,
      recommendation: res.data.recommendation
    }
    const score = res.data.quality_metrics.overall_score
    ElMessage.success(`Cloud: Quality score ${score}/100 - ${res.data.overall_pass ? 'PASS' : 'REVIEW'}`)
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'common.error'))
  } finally {
    aiLoading.value = false
  }
}

const aiGenerateDesign = async () => {
  aiLoading.value = true
  aiResultType.value = 'Generative Design (Cloud VAE)'
  try {
    const res = await aiAPI.generateDesign({
      car_type: carType.value,
      style: 'elegant',
      brand: brand.value
    })
    aiResult.value = {
      design_id: res.data.design_id,
      car_type: res.data.car_type,
      style: res.data.style,
      quality_score: res.data.quality_metrics.overall_score,
      creativity: res.data.creativity_score,
      brand_dna_match: res.data.brand_dna_match
    }
    ElMessage.success(`Cloud: Design ${res.data.design_id} generated (creativity: ${res.data.creativity_score})`)
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'common.error'))
  } finally {
    aiLoading.value = false
  }
}

const aiOptimize = async () => {
  aiLoading.value = true
  aiResultType.value = 'Multi-Objective Optimization (Cloud Pareto)'
  try {
    const res = await aiAPI.optimize({
      parameters: carParams.value,
      objectives: ['aerodynamics', 'quality', 'manufacturability', 'aesthetics']
    })
    const objs = res.data.objectives
    aiResult.value = {
      pareto_score: res.data.pareto_score,
      is_pareto_optimal: res.data.is_pareto_optimal,
      iterations: res.data.optimization_iterations,
      convergence: res.data.convergence,
      aero_cd: objs.aerodynamics?.cd,
      quality_g2: objs.quality?.g2,
      formability: objs.manufacturability?.formability,
      harmony: objs.aesthetics?.harmony
    }
    ElMessage.success(`Cloud: Pareto score ${res.data.pareto_score} (${res.data.is_pareto_optimal ? 'OPTIMAL' : 'SUB-OPTIMAL'})`)
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'common.error'))
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => {
  loadAiStats()
  preloadAllImages()
})

onUnmounted(() => {
  cleanupImageCache()
})
</script>

<style scoped>
.designer-page {
  width: 100%;
  min-width: 1200px;
  height: calc(100vh - 52px);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
}

.main-layout {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 260px 1fr 280px;
  gap: 10px;
  padding: 10px;
  overflow: hidden;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  overflow-x: hidden;
}

.center-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  min-width: 0;
}

.center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  flex-shrink: 0;
}

.center-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.title-main {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.title-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.center-tabs {
  display: flex;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 2px;
}

.center-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  font-size: 11px;
  color: var(--text-muted);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.center-tab:hover {
  color: rgba(255, 255, 255, 0.8);
}

.center-tab.active {
  background: var(--accent-bg);
  color: var(--accent);
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--accent);
  color: #0a0a0f;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.generate-btn:hover:not(:disabled) {
  background: #22c55e;
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.3);
}

.generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.generate-btn svg {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.viewport-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  min-height: 0;
}

.viewport-row .viewport-card {
  height: 100%;
  min-height: 0;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  flex-shrink: 0;
  height: 220px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.card-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--accent-bg);
  color: var(--accent);
  letter-spacing: 0.5px;
}

.card-badge.cloud {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.car-type-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.car-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.car-type-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(74, 222, 128, 0.05);
}

.car-type-card.active {
  border-color: var(--accent);
  background: rgba(74, 222, 128, 0.1);
}

.car-type-icon {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.car-type-card.active .car-type-icon {
  color: var(--accent);
}

.car-type-svg {
  width: 90px;
  height: 42px;
}

.car-type-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
}

.car-type-card.active .car-type-name {
  color: var(--accent);
}

.brand-section {
  display: flex;
  gap: 10px;
}

.brand-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 72px;
  flex-shrink: 0;
}

.brand-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.brand-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.brand-item.active {
  background: rgba(74, 222, 128, 0.1);
}

.brand-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.brand-name {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.55);
}

.brand-item.active .brand-name {
  color: var(--accent);
}

.model-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  max-height: 340px;
  padding-right: 4px;
}

.model-card {
  display: flex;
  gap: 10px;
  padding: 8px;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(255, 255, 255, 0.04);
  transform: translateX(2px);
}

.model-card.active {
  border-color: var(--accent);
  background: rgba(74, 222, 128, 0.08);
  box-shadow: 0 2px 8px rgba(74, 222, 128, 0.15);
}

.model-image {
  width: 64px;
  height: 38px;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--bg-primary);
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.model-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.model-img.local-img {
  filter: brightness(1.1) saturate(0.9);
}

.img-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  pointer-events: none;
}

.model-image {
  position: relative;
}

.reference-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.reference-image-wrapper .reference-img {
  max-width: 100%;
  max-height: calc(100% - 40px);
  object-fit: contain;
}

.ref-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  gap: 8px;
  pointer-events: none;
}

.ref-model-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 4px 8px;
}

.ref-model-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ref-model-spec {
  font-size: 10px;
  color: var(--text-muted);
}

.ref-local-hint {
  font-size: 9px;
  color: #f59e0b;
  margin-top: 2px;
}

.model-image-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--hover-bg);
}

.fallback-svg {
  width: 44px;
  height: 22px;
  margin-bottom: 2px;
}

.fallback-text {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 56px;
}

.model-image-loading {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: var(--hover-bg);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

.spinner-ring {
  stroke: rgba(74, 222, 128, 0.6);
  stroke-linecap: round;
  stroke-dasharray: 30;
  stroke-dashoffset: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 7px;
  color: rgba(74, 222, 128, 0.5);
}

.model-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  gap: 2px;
}

.model-name {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-card.active .model-name {
  color: var(--accent);
  font-weight: 600;
}

.model-spec {
  font-size: 10px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.viewport-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.viewport-tabs {
  display: flex;
  background: var(--hover-bg);
  border-radius: 4px;
  padding: 2px;
}

.viewport-tab {
  padding: 4px 10px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.viewport-tab:hover {
  color: rgba(255, 255, 255, 0.7);
}

.viewport-tab.active {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.85);
}

.viewport-tab.active-green.active {
  background: var(--accent-bg);
  color: var(--accent);
}

.viewport-tab.blue.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.viewport-container {
  width: 100%;
  height: calc(100% - 36px);
  position: relative;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
}

.ref-tabs {
  display: flex;
  gap: 2px;
}

.ref-tab {
  padding: 3px 8px;
  font-size: 10px;
  color: var(--text-muted);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.ref-tab:hover {
  color: rgba(255, 255, 255, 0.7);
}

.ref-tab.active {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
}

.reference-image-container {
  width: 100%;
  height: calc(100% - 32px);
  /* 关键兜底：父级 flex 高度塌陷时，至少给图片一个可渲染形状 */
  min-height: 280px;
  aspect-ratio: 16 / 9;
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.reference-img {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
}

.reference-placeholder {
  color: rgba(255, 255, 255, 0.25);
  font-size: 11px;
}

.reference-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(74, 222, 128, 0.6);
}

.ref-loading-spinner {
  width: 32px;
  height: 32px;
  animation: spin 1s linear infinite;
}

.ref-loading-text {
  font-size: 13px;
  font-weight: 500;
}

.reference-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-faint);
}

.ref-fallback-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.ref-fallback-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.ref-fallback-spec {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
}

.ref-fallback-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.ref-fallback-svg {
  width: 160px;
  height: 80px;
  opacity: 0.8;
}

.wireframe-container {
  width: 100%;
  height: calc(100% - 32px);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-radius: 4px;
  overflow: hidden;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.color-swatch {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.color-swatch:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.color-swatch.active {
  border-color: #fff;
  box-shadow: 0 0 0 2px var(--accent), 0 4px 8px rgba(0, 0, 0, 0.3);
  transform: scale(1.05);
}

.color-check {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  color: #fff;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.6));
}

.color-check svg {
  width: 100%;
  height: 100%;
}

.color-input-row {
  display: flex;
  gap: 8px;
}

.color-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 11px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s ease;
}

.color-input:focus {
  border-color: var(--accent);
  background: rgba(74, 222, 128, 0.05);
}

.color-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.apply-btn {
  padding: 8px 16px;
  background: var(--accent-bg);
  color: var(--accent);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.apply-btn:hover {
  background: rgba(74, 222, 128, 0.25);
  border-color: rgba(74, 222, 128, 0.5);
}

.param-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  background: var(--hover-bg);
  border-radius: 6px;
  padding: 3px;
  border: 1px solid var(--border-color);
}

.param-tab {
  flex: 1;
  text-align: center;
  padding: 6px 8px;
  font-size: 10px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.45);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.param-tab:hover {
  color: rgba(255, 255, 255, 0.7);
}

.param-tab.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.param-list {
  max-height: 300px;
  overflow-y: auto;
  padding-right: 4px;
}

.param-item {
  margin-bottom: 14px;
  padding: 10px 12px;
  background: var(--hover-bg);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.param-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.param-name {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.param-value {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  background: rgba(74, 222, 128, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.param-slider {
  width: 100%;
  height: 5px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(74, 222, 128, 0.4);
  border: 2px solid var(--bg-primary);
}

.param-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 12px rgba(74, 222, 128, 0.6);
}

.ai-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.ai-btn {
  width: 100%;
  padding: 10px 14px;
  background: rgba(59, 130, 246, 0.08);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.ai-btn::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #3b82f6;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.ai-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateX(2px);
}

.ai-btn:hover:not(:disabled)::before {
  opacity: 1;
}

.ai-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.ai-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.ai-stat-row:last-child {
  border-bottom: none;
}

.ai-stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 500;
}

.ai-stat-val {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  font-family: 'Courier New', monospace;
}

.ai-result {
  margin-top: 12px;
  padding: 12px;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
}

.ai-result-header {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ai-result-type {
  font-size: 12px;
  color: #60a5fa;
  font-weight: 600;
  margin-bottom: 8px;
}

.ai-result-metrics {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.8;
}

::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.viewport-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.viewport-card .viewport-header {
  padding: 10px 14px;
  margin: 0;
  border-bottom: 1px solid var(--border-color);
}

.viewport-card .viewport-container {
  flex: 1;
  position: relative;
  min-height: 0;
  width: 100%;
  height: auto;
  background: var(--bg-primary);
  border-radius: 0;
}

.viewport-2d {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
}

.reference-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.reference-card .card-header {
  padding: 10px 14px;
  margin: 0;
  border-bottom: 1px solid var(--border-color);
}

.reference-image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  overflow: hidden;
  min-height: 0;
  width: 100%;
  height: auto;
  border-radius: 0;
}

.wireframe-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.wireframe-card .card-header {
  padding: 10px 14px;
  margin: 0;
  border-bottom: 1px solid var(--border-color);
}

.wireframe-container {
  flex: 1;
  padding: 12px;
  min-height: 0;
}

.ai-cloud-card {
  border: 1px solid rgba(59, 130, 246, 0.2);
}
</style>
