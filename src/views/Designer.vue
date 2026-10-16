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
                    @load="handleImageLoad(model.key)"
                  />
                  <div v-if="getImageState(model.key) === 'loading'" class="img-loading-overlay">
                    <svg class="loading-spinner" viewBox="0 0 24 24">
                      <circle class="spinner-ring" cx="12" cy="12" r="10" fill="none" stroke-width="2"/>
                    </svg>
                  </div>
                </div>
                <div class="model-info">
                  <div class="model-name">{{ model.name }}</div>
                  <div class="model-meta">
                    <span class="model-spec">{{ model.params.overall_length }}mm</span>
                    <span
                      v-if="model.car_type"
                      class="model-type-tag"
                      :class="{ linked: carType === model.car_type }"
                    >{{ t('designer.' + (carTypes.find(ct => ct.key === model.car_type)?.name || model.car_type)) }}</span>
                  </div>
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
                    @load="handleImageLoad(currentModel.key)"
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
                  <span class="param-name">{{ t('designer.rearSlantAngle') }}</span>
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
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.sideGlassTumblehome') }}</span>
                  <span class="param-value">{{ carParams.side_glass_angle }}°</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.side_glass_angle"
                  min="1"
                  max="40"
                  step="1"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.glassBarrelAngle') }}</span>
                  <span class="param-value">{{ carParams.glass_barrel_angle }}°</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.glass_barrel_angle"
                  min="0"
                  max="20"
                  step="1"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.glassBarrelRadius') }}</span>
                  <span class="param-value">{{ carParams.glass_barrel_radius }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.glass_barrel_radius"
                  min="500"
                  max="4000"
                  step="50"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">{{ t('designer.vtolBranch') }}</span>
                  <label class="param-toggle">
                    <input type="checkbox" v-model="carParams.enable_vtol" />
                    <span>{{ t('designer.vtolEnable') }}</span>
                  </label>
                </div>
              </div>
              <template v-if="carParams.enable_vtol">
                <div class="param-item">
                  <div class="param-label-row">
                    <span class="param-name">{{ t('designer.hoverAltitude') }}</span>
                    <span class="param-value">{{ carParams.hover_altitude }} mm</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="carParams.hover_altitude"
                    min="400"
                    max="3000"
                    step="50"
                    class="param-slider"
                  />
                </div>
                <div class="param-item">
                  <div class="param-label-row">
                    <span class="param-name">{{ t('designer.exoticDriveRatio') }}</span>
                    <span class="param-value">{{ (carParams.exotic_drive_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="carParams.exotic_drive_ratio"
                    min="0"
                    max="0.3"
                    step="0.01"
                    class="param-slider"
                  />
                </div>
                <div class="param-item">
                  <div class="param-label-row">
                    <span class="param-name">{{ t('designer.darkMatterRatio') }}</span>
                    <span class="param-value">{{ (carParams.dark_matter_ratio * 100).toFixed(0) }}%</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="carParams.dark_matter_ratio"
                    min="0"
                    max="0.3"
                    step="0.01"
                    class="param-slider"
                  />
                </div>
                <div class="param-item">
                  <div class="param-label-row">
                    <span class="param-name">{{ t('designer.liftFanCount') }}</span>
                    <span class="param-value">{{ carParams.lift_fan_count }}</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="carParams.lift_fan_count"
                    min="2"
                    max="8"
                    step="2"
                    class="param-slider"
                  />
                </div>
                <div v-if="flightMetrics" class="param-item flight-metrics">
                  <div class="flight-metrics-title">{{ t('designer.flightMetrics') }}</div>
                  <div class="flight-metric-grid">
                    <div class="flight-metric" :class="{ ok: flightMetrics.enduranceOk }">
                      <span class="metric-label">{{ t('designer.enduranceMultiple') }}</span>
                      <span class="metric-value">×{{ flightMetrics.enduranceMultiple.toFixed(2) }}</span>
                    </div>
                    <div class="flight-metric">
                      <span class="metric-label">{{ t('designer.hoverPower') }}</span>
                      <span class="metric-value">{{ flightMetrics.hoverPowerKw }} kW</span>
                    </div>
                    <div class="flight-metric" :class="{ ok: flightMetrics.attitudeOk }">
                      <span class="metric-label">{{ t('designer.attitudeStability') }}</span>
                      <span class="metric-value">±{{ flightMetrics.attitudePeakDeg.toFixed(2) }}°</span>
                    </div>
                    <div class="flight-metric" :class="{ ok: flightMetrics.latencyOk }">
                      <span class="metric-label">{{ t('designer.controlLatency') }}</span>
                      <span class="metric-value">{{ flightMetrics.latencyMs }} ms</span>
                    </div>
                    <div class="flight-metric" :class="{ ok: flightMetrics.peakOk }">
                      <span class="metric-label">{{ t('designer.peakFactor') }}</span>
                      <span class="metric-value">×{{ flightMetrics.peakFactor.toFixed(2) }}</span>
                    </div>
                    <div class="flight-metric">
                      <span class="metric-label">{{ t('designer.fullTurn') }}</span>
                      <span class="metric-value">{{ flightMetrics.fullTurnSec.toFixed(1) }}s</span>
                    </div>
                  </div>
                </div>
              </template>
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
import { resolveFlightParams, flightControlEnvelope } from '../utils/flightPhysics.js'
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

// 反重力飞控指标卡（与后端 flight_envelope.flight_control 同公式）：
// 续航倍数 ≥3× / 姿态 ±2° / 延迟 ≤100ms / 峰值因子 ≤1.25 —— 随参数实时联动
const flightMetrics = computed(() => {
  const p = params.value
  if (!p || !p.enable_vtol) return null
  return flightControlEnvelope({
    overall_length: p.overall_length,
    overall_width: p.overall_width,
    overall_height: p.overall_height
  }, resolveFlightParams(carType.value, p))
})

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
  if (s._retryTimer) {
    clearTimeout(s._retryTimer)
    s._retryTimer = null
  }
  s.layer = 0
  s.attempt = 0
  s.renderKey = 0
  s.minLayer = 0
  s.l1Retries = 0
  s.l1Recoveries = 0
}

/**
 * 图片加载失败处理（确定性降级，不再依赖 localStorage 隐式跳过）：
 *
 * L1（/brands/* 随包发布的静态真车图）按"瞬时故障"处理——CDN 边缘刷新、
 * cpolar 隧道中断、快速切换品牌导致的请求 abort 都可能让一张本应 200 的
 * 图只抛一次 error。旧逻辑遇到一次 error 就把 minLayer 永久推过 L1，
 * 而公网 L2 远程 AI URL 又必然失败，卡片就此在整个会话锁死成 SVG（漂移）。
 * 现在：
 *   1. L1 失败不标记、不降级，按退避重挂重试（0/500/1500ms，共 3 次）
 *   2. 快速重试仍失败 → 临时退到 L3 SVG 占位，10s 后自动回到 L1 自愈探测（最多 2 轮）
 *   3. L2 及以上失败维持原逻辑：记失败名单 + minLayer 推进，attempt<=5 封顶锁 L4
 */
const MAX_ATTEMPTS = 5
const L1_RETRY_DELAYS = [0, 500, 1500]
const L1_RECOVER_DELAY = 10000
const L1_MAX_RECOVERIES = 2

const scheduleImgRetry = (state, delay, fn) => {
  if (state._retryTimer) clearTimeout(state._retryTimer)
  state._retryTimer = setTimeout(() => {
    state._retryTimer = null
    fn()
  }, delay)
}

const handleImageError = (modelKey) => {
  const model = getModelByKey(modelKey)
  if (!model) return
  const bk = getBrandKeyForModel(modelKey)
  const state = ensureState(modelKey)

  const resolved = resolveByLayer(model, bk, state.minLayer || 0)

  // ── L1 静态真车图：瞬时故障策略（重试 + 延迟自愈，永不永久降级）──
  if (resolved.layer === 1) {
    state.l1Retries = (state.l1Retries || 0) + 1
    if (state.l1Retries <= L1_RETRY_DELAYS.length) {
      const delay = L1_RETRY_DELAYS[state.l1Retries - 1]
      // minLayer 保持 0，重挂 <img> 重新请求同一个静态图
      scheduleImgRetry(state, delay, () => { state.renderKey++ })
      return
    }
    // 快速重试耗尽：临时 SVG 占位（minLayer=2 → 解析直接落到 L3）
    state.minLayer = 2
    state.renderKey++
    // 延迟自愈：网络恢复后自动回到真车图，无需用户刷新
    state.l1Recoveries = (state.l1Recoveries || 0) + 1
    if (state.l1Recoveries <= L1_MAX_RECOVERIES) {
      scheduleImgRetry(state, L1_RECOVER_DELAY, () => {
        state.minLayer = 0
        state.l1Retries = 0
        state.renderKey++
      })
    }
    return
  }

  // ── L2+ 远程/兜底层：失败即推进（原逻辑）──
  state.attempt++
  if (resolved.src && !resolved.src.startsWith('data:')) {
    markUrlFailed(resolved.src)
  }

  if (state.attempt >= MAX_ATTEMPTS) {
    state.minLayer = 4
    state.renderKey++
    return
  }

  state.minLayer = Math.max(state.minLayer || 0, resolved.layer)
  if (state.minLayer >= 4) state.minLayer = 4
  state.renderKey++
}

// L1 图片加载成功：取消挂起重试，若处于 SVG 临时占位则立刻回到真车图层
const handleImageLoad = (modelKey) => {
  const state = ensureState(modelKey)
  if (state._retryTimer) {
    clearTimeout(state._retryTimer)
    state._retryTimer = null
  }
  state.l1Retries = 0
  if ((state.minLayer || 0) === 2) {
    state.minLayer = 0
    state.l1Recoveries = 0
    state.renderKey++
  }
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
          ? t('designer.msgG2Pass')
          : t('designer.msgG2Fail', { n: q.n_flat_surfaces || 0 })
      }
      const type = q.g2_continuous === false ? 'warning' : 'success'
      ElMessage({
        type,
        message: t('designer.msgGenerated', {
          parts: data.components.length, surfaces: nSurf, points: nCp
        }) + quality,
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
  min-width: 0;
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

/* 车型卡连动徽章：显示所属 CAR TYPE，与左侧宫格高亮同步 */
.model-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.model-type-tag {
  font-size: 9px;
  line-height: 1;
  padding: 3px 6px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  white-space: nowrap;
  transition: all 0.2s;
}
.model-type-tag.linked {
  border-color: var(--accent);
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
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

/* VTOL 飞行能力开关（翡翠绿品牌主色） */
.param-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #9ca3af;
  cursor: pointer;
  user-select: none;
}

.param-toggle input {
  accent-color: #10b981;
  cursor: pointer;
}

/* 反重力飞控指标卡：目标达标翡翠绿、未达标琥珀（如实呈现用户调参后果） */
.flight-metrics {
  border-top: 1px dashed rgba(16, 185, 129, 0.25);
  padding-top: 10px;
}

.flight-metrics-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #10b981;
  margin-bottom: 8px;
}

.flight-metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
}

.flight-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.flight-metric .metric-label {
  font-size: 10px;
  color: #9ca3af;
}

.flight-metric .metric-value {
  font-size: 12px;
  font-weight: 600;
  color: #d1d5db;
  font-variant-numeric: tabular-nums;
}

.flight-metric.ok .metric-value {
  color: #10b981;
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

/* ============ 响应式 ============ */
/* 平板：压缩三栏宽度（侧栏已转为抽屉，主区可用宽增加） */
@media (max-width: 1200px) {
  .main-layout { grid-template-columns: 220px 1fr 240px; }
}

/* 手机/窄平板：单列堆叠，3D 视口优先显示 */
@media (max-width: 900px) {
  .designer-page {
    height: auto;
    min-height: calc(100vh - 52px);
    overflow: visible;
  }
  .main-layout {
    grid-template-columns: 1fr;
    overflow: visible;
    padding: 8px;
  }
  .center-panel { order: 1; overflow: visible; }
  .left-panel { order: 2; overflow: visible; }
  .right-panel { order: 3; overflow: visible; }
  .center-header { flex-wrap: wrap; gap: 8px; }
  .viewport-row {
    grid-template-columns: 1fr;
    flex: none;
    gap: 10px;
  }
  .viewport-row .viewport-card { height: 46vh; min-height: 300px; }
  .bottom-row {
    grid-template-columns: 1fr;
    height: auto;
  }
  .bottom-row > * { min-height: 200px; }
  .generate-btn { width: 100%; justify-content: center; }
}
</style>
