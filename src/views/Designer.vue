<template>
  <div class="designer-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">AI Automotive Designer</h1>
        <div class="header-subrow">
          <p class="page-subtitle">Parametric A-Class Surface Generation</p>
          <div class="header-tabs">
            <div class="header-tab active">
              <span class="tab-dot"></span>
              NURBS A-Class
            </div>
            <div class="header-tab">
              Parametric
            </div>
          </div>
        </div>
      </div>
      <button class="generate-btn" @click="generateCar" :disabled="generating">
        <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7"/>
        </svg>
        <svg v-else class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>{{ generating ? 'Generating...' : 'Generate Complete Car' }}</span>
      </button>
    </div>

    <div class="main-layout">
      <!-- Left Panel -->
      <div class="left-panel">
        <div class="card">
          <div class="card-header">
            <span class="card-title">CAR TYPE</span>
          </div>
          <div class="car-type-grid">
            <div
              v-for="ct in carTypes"
              :key="ct.key"
              class="car-type-card"
              :class="{ active: selectedCarType === ct.key }"
              @click="selectCarType(ct.key)"
            >
              <div class="car-type-icon">
                <svg viewBox="0 0 120 60" class="car-type-svg">
                  <path :d="getCarTypeSvg(ct.key)" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </div>
              <div class="car-type-name">{{ ct.name }}</div>
            </div>
          </div>
        </div>

        <div class="card card-brand">
          <div class="card-header">
            <span class="card-title">A-CLASS CERTIFIED PRESETS</span>
            <span class="card-badge">PRO</span>
          </div>
          <div class="brand-section">
            <div class="brand-list">
              <div
                v-for="brand in brands"
                :key="brand.key"
                class="brand-item"
                :class="{ active: selectedBrand === brand.key }"
                @click="selectedBrand = brand.key"
              >
                <span class="brand-dot" :style="{ background: brand.color }"></span>
                <span class="brand-name">{{ brand.name }}</span>
              </div>
            </div>
            <div class="model-list">
              <div
                v-for="model in currentBrandModels"
                :key="model.key"
                class="model-card"
                :class="{ active: selectedModel === model.key }"
                @click="selectModel(model)"
              >
                <div class="model-image">
                  <img :src="model.image" :alt="model.name" />
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
        <div class="viewport-row">
          <!-- Left Viewport - Base Model -->
          <div class="card viewport-card">
            <div class="viewport-header">
              <div class="viewport-tabs">
                <div class="viewport-tab" :class="{ active: baseModelTab === 'parametric' }" @click="baseModelTab = 'parametric'">
                  Parametric
                </div>
                <div class="viewport-tab active-green active" :class="{ active: baseModelTab === 'nurbs' }" @click="baseModelTab = 'nurbs'">
                  NURBS A-Class
                </div>
              </div>
            </div>
            <div class="viewport-container">
              <Car3D
                :car-params="carParams"
                :car-type="selectedCarType"
                car-color="#3b82f6"
                :view-angle="baseViewAngle"
                :wireframe="true"
                @update:view-angle="baseViewAngle = $event"
              />
            </div>
          </div>

          <!-- Right Viewport - Live Preview -->
          <div class="card viewport-card">
            <div class="viewport-header">
              <div class="viewport-tabs">
                <div class="viewport-tab blue active" :class="{ active: previewTab === '3d' }" @click="previewTab = '3d'">
                  3D视图
                </div>
                <div class="viewport-tab blue" :class="{ active: previewTab === '2d' }" @click="previewTab = '2d'">
                  2D视图
                </div>
              </div>
            </div>
            <div class="viewport-container">
              <Car3D
                v-if="previewTab === '3d'"
                :car-params="carParams"
                :car-type="selectedCarType"
                :car-color="selectedColor"
                :view-angle="previewViewAngle"
                :wireframe="false"
                @update:view-angle="previewViewAngle = $event"
              />
              <div v-else class="viewport-2d">
                <Car2D :car-params="carParams" :car-type="selectedCarType" />
              </div>
            </div>
          </div>
        </div>

        <div class="bottom-row">
          <div class="card reference-card">
            <div class="card-header">
              <span class="card-title">REFERENCE</span>
              <div class="ref-tabs">
                <span class="ref-tab active">横向</span>
                <span class="ref-tab">正面</span>
                <span class="ref-tab">俯视</span>
              </div>
            </div>
            <div class="reference-image-container">
              <img v-if="currentModel" :src="currentModel.image" :alt="currentModel.name" class="reference-img" />
              <div v-else class="reference-placeholder">
                <span>Select a model to view reference</span>
              </div>
            </div>
          </div>

          <div class="card wireframe-card">
            <div class="card-header">
              <span class="card-title">2D RENDER</span>
            </div>
            <div class="wireframe-container">
              <Car2D :car-params="carParams" :car-type="selectedCarType" />
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel -->
      <div class="right-panel">
        <div class="card">
          <div class="card-header">
            <span class="card-title">BODY COLOR</span>
          </div>
          <div class="color-grid">
            <div
              v-for="color in bodyColors"
              :key="color.value"
              class="color-swatch"
              :class="{ active: selectedColor === color.value }"
              :style="{ background: color.value }"
              @click="selectedColor = color.value"
              :title="color.name"
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
            <button class="apply-btn" @click="applyCustomColor">Apply</button>
          </div>
        </div>

        <div class="card param-card">
          <div class="card-header">
            <span class="card-title">PARAMETER CONFIGURATION</span>
          </div>
          <div class="param-tabs">
            <div class="param-tab active" :class="{ active: paramTab === 'dimensions' }" @click="paramTab = 'dimensions'">
              Dimension Parameters
            </div>
            <div class="param-tab" :class="{ active: paramTab === 'styling' }" @click="paramTab = 'styling'">
              Styling Parameters
            </div>
          </div>
          <div class="param-list">
            <div v-if="paramTab === 'dimensions'" class="param-items">
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">Overall Length</span>
                  <span class="param-value">{{ carParams.overall_length }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.overall_length"
                  min="3500"
                  max="6000"
                  step="10"
                  class="param-slider"
                />
              </div>
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">Overall Width</span>
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
                  <span class="param-name">Overall Height</span>
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
                  <span class="param-name">WheelBase</span>
                  <span class="param-value">{{ carParams.wheel_base }} mm</span>
                </div>
                <input
                  type="range"
                  v-model.number="carParams.wheel_base"
                  min="2400"
                  max="4000"
                  step="10"
                  class="param-slider"
                />
              </div>
            </div>
            <div v-else class="param-items">
              <div class="param-item">
                <div class="param-label-row">
                  <span class="param-name">Hood Length</span>
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
                  <span class="param-name">Roof Height</span>
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
                  <span class="param-name">Wheel Diameter</span>
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
                  <span class="param-name">Windshield Angle</span>
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
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Car3D from '../components/Car3D.vue'
import Car2D from '../components/Car2D.vue'
import { carTypes, carTypeParams, brands, bodyColors, defaultCarParams } from '../config/carPresets'

const generating = ref(false)
const selectedCarType = ref('sedan')
const selectedBrand = ref('rolls-royce')
const selectedModel = ref(null)
const selectedColor = ref('#4ade80')
const customColor = ref('')
const baseModelTab = ref('nurbs')
const previewTab = ref('3d')
const paramTab = ref('dimensions')
const baseViewAngle = ref('perspective')
const previewViewAngle = ref('perspective')

const carParams = ref({ ...defaultCarParams, ...carTypeParams.sedan })

const currentBrandModels = computed(() => {
  const brand = brands.find(b => b.key === selectedBrand.value)
  return brand ? brand.models : []
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

const selectCarType = (type) => {
  selectedCarType.value = type
  if (carTypeParams[type]) {
    carParams.value = { ...defaultCarParams, ...carTypeParams[type] }
  }
  selectedModel.value = null
}

const selectModel = (model) => {
  selectedModel.value = model.key
  if (model.params) {
    carParams.value = { ...defaultCarParams, ...model.params }
  }
}

const applyCustomColor = () => {
  if (customColor.value && /^#[0-9A-Fa-f]{6}$/.test(customColor.value)) {
    selectedColor.value = customColor.value
  }
}

const generateCar = async () => {
  generating.value = true
  setTimeout(() => {
    generating.value = false
  }, 2000)
}
</script>

<style scoped>
.designer-page {
  width: 100%;
  min-width: 1200px;
  min-height: calc(100vh - 52px - 32px);
  height: calc(100vh - 52px - 32px);
  background: #0a0a0f;
  color: #fff;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: #16161f;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.header-subrow {
  display: flex;
  align-items: center;
  gap: 20px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-align: left;
}

.page-subtitle {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.3px;
}

.header-tabs {
  display: flex;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 3px;
}

.header-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.header-tab:hover {
  color: rgba(255, 255, 255, 0.8);
}

.header-tab.active {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

.tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4ade80;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: #4ade80;
  color: #0a0a0f;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.generate-btn:hover:not(:disabled) {
  background: #22c55e;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 222, 128, 0.3);
}

.generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.generate-btn svg {
  width: 16px;
  height: 16px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.main-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(300px, 1fr) 300px;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
  min-width: 0;
}

.left-panel,
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  overflow-x: hidden;
}

.center-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.viewport-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  min-height: 0;
}

.viewport-row .viewport-card {
  height: 100%;
  min-height: 0;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  flex-shrink: 0;
  height: 240px;
}

.card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.7);
}

.card-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
  border-radius: 4px;
  letter-spacing: 0.5px;
}

.car-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.car-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.car-type-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(74, 222, 128, 0.05);
}

.car-type-card.active {
  border-color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
}

.car-type-icon {
  width: 100%;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 6px;
}

.car-type-card.active .car-type-icon {
  color: #4ade80;
}

.car-type-svg {
  width: 80px;
  height: 36px;
}

.car-type-name {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
}

.car-type-card.active .car-type-name {
  color: #4ade80;
}

.brand-section {
  display: flex;
  gap: 10px;
}

.brand-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 70px;
}

.brand-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.brand-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.8);
}

.brand-item.active {
  background: rgba(74, 222, 128, 0.1);
  color: #4ade80;
}

.brand-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.model-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  max-height: 300px;
  padding-right: 2px;
}

.model-list::-webkit-scrollbar {
  width: 3px;
}

.model-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.model-card {
  display: flex;
  gap: 8px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  background: rgba(255, 255, 255, 0.04);
}

.model-card.active {
  border-color: #4ade80;
  background: rgba(74, 222, 128, 0.06);
}

.model-image {
  width: 60px;
  height: 36px;
  flex-shrink: 0;
  overflow: hidden;
  background: #0a0a0f;
  border-radius: 3px;
}

.model-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.model-name {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-spec {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 2px;
}

.model-card.active .model-name {
  color: #4ade80;
}

.viewport-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.viewport-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.viewport-tabs {
  display: flex;
  gap: 4px;
}

.viewport-tab {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
}

.viewport-tab:hover {
  color: rgba(255, 255, 255, 0.7);
}

.viewport-tab.active {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

.viewport-tab.active-green.active {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

.viewport-tab.blue.active {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.viewport-container {
  flex: 1;
  position: relative;
  min-height: 0;
}

.viewport-2d {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0f;
}

.ref-tabs {
  display: flex;
  gap: 2px;
}

.ref-tab {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 3px;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
}

.ref-tab:hover {
  color: rgba(255, 255, 255, 0.7);
}

.ref-tab.active {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

.viewport-container {
  flex: 1;
  position: relative;
  min-height: 0;
}

.viewport-2d {
  width: 100%;
  height: 100%;
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.reference-image-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0f;
  overflow: hidden;
  min-height: 0;
}

.reference-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.reference-placeholder {
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.wireframe-container {
  flex: 1;
  padding: 12px;
  min-height: 0;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

.color-swatch {
  aspect-ratio: 1;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

.color-swatch:hover {
  transform: scale(1.05);
}

.color-swatch.active {
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.5);
}

.color-check {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  width: 16px;
  height: 16px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
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
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: #fff;
  font-size: 11px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s ease;
}

.color-input:focus {
  border-color: rgba(74, 222, 128, 0.4);
}

.color-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.apply-btn {
  padding: 6px 14px;
  background: rgba(74, 222, 128, 0.15);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 6px;
  color: #4ade80;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.apply-btn:hover {
  background: rgba(74, 222, 128, 0.25);
}

.param-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}

.param-tab {
  flex: 1;
  font-size: 10px;
  padding: 6px 4px;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.2s ease;
}

.param-tab:hover {
  background: rgba(255, 255, 255, 0.05);
}

.param-tab.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

.param-list {
  max-height: 300px;
  overflow-y: auto;
}

.param-items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.param-value {
  font-size: 11px;
  font-weight: 600;
  color: #4ade80;
  font-family: 'Inter', monospace;
}

.param-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  cursor: pointer;
}

.param-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #4ade80;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(74, 222, 128, 0.4);
  transition: transform 0.15s ease;
}

.param-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.param-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #4ade80;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 6px rgba(74, 222, 128, 0.4);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
