<template>
  <div class="designer-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('designer.title') }}</h2>
        <p>{{ $t('designer.subtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="generateCar" :loading="generating">
          <el-icon><VideoPlay /></el-icon>
          {{ $t('designer.generateCar') }}
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="left-panel">
        <el-card class="panel-card">
          <template #header>
            <span>{{ $t('designer.carType') }}</span>
          </template>
          <div class="car-type-grid">
            <div
              v-for="ct in carTypes"
              :key="ct.key"
              class="car-type-item"
              :class="{ active: selectedCarType === ct.key }"
              @click="selectCarType(ct.key)"
            >
              <svg viewBox="0 0 120 60" class="car-type-svg" v-html="ct.svgPath"></svg>
              <div class="car-type-name">{{ ct.name }}</div>
              <div class="car-type-desc">{{ ct.desc }}</div>
            </div>
          </div>
        </el-card>

        <el-card class="panel-card">
          <template #header>
            <span>{{ $t('designer.bodyColor') }}</span>
          </template>
          <div class="color-picker">
            <div
              v-for="color in bodyColors"
              :key="color.value"
              class="color-item"
              :class="{ active: selectedColor === color.value }"
              :style="{ background: color.value }"
              @click="selectedColor = color.value"
            >
              <div class="color-check" v-if="selectedColor === color.value">
                <el-icon><CircleCheck /></el-icon>
              </div>
            </div>
          </div>
          <div class="custom-color">
            <el-input v-model="customColor" type="text" placeholder="#000000" size="small" />
            <el-button size="small" @click="applyCustomColor">应用</el-button>
          </div>
        </el-card>

        <el-card class="panel-card">
          <template #header>
            <span>{{ $t('designer.paramConfig') }}</span>
          </template>
          <el-tabs v-model="paramTab" type="border-card">
            <el-tab-pane :label="$t('designer.dimensions')" name="dimensions">
              <el-form :model="carParams" label-width="100px" size="small">
                <el-form-item :label="$t('designer.overallLength')">
                  <el-slider v-model="carParams.overall_length" :min="3000" :max="6000" :step="50" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.overallWidth')">
                  <el-slider v-model="carParams.overall_width" :min="1500" :max="2200" :step="10" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.overallHeight')">
                  <el-slider v-model="carParams.overall_height" :min="1200" :max="2000" :step="10" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.wheelBase')">
                  <el-slider v-model="carParams.wheel_base" :min="2300" :max="4000" :step="50" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.trackWidth')">
                  <el-slider v-model="carParams.track_width" :min="1400" :max="1800" :step="10" show-input />
                </el-form-item>
              </el-form>
            </el-tab-pane>
            <el-tab-pane :label="$t('designer.components')" name="components">
              <el-form :model="componentParams" label-width="100px" size="small">
                <el-form-item :label="$t('designer.hoodLength')">
                  <el-slider v-model="componentParams.hood_length" :min="500" :max="2000" :step="50" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.roofHeight')">
                  <el-slider v-model="componentParams.roof_height" :min="200" :max="800" :step="10" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.wheelDiameter')">
                  <el-slider v-model="componentParams.wheel_diameter" :min="500" :max="800" :step="10" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.doorFrontLength')">
                  <el-slider v-model="componentParams.door_front_length" :min="600" :max="1400" :step="50" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.groundClearance')">
                  <el-slider v-model="componentParams.ground_clearance" :min="100" :max="300" :step="5" show-input />
                </el-form-item>
              </el-form>
            </el-tab-pane>
            <el-tab-pane :label="$t('designer.angles')" name="angles">
              <el-form :model="angleParams" label-width="100px" size="small">
                <el-form-item :label="$t('designer.hoodAngle')">
                  <el-slider v-model="angleParams.hood_angle" :min="0" :max="45" :step="1" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.windshieldAngle')">
                  <el-slider v-model="angleParams.windshield_angle" :min="20" :max="70" :step="1" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.rearWindowAngle')">
                  <el-slider v-model="angleParams.rear_window_angle" :min="10" :max="55" :step="1" show-input />
                </el-form-item>
                <el-form-item :label="$t('designer.rearSlantAngle')">
                  <el-slider v-model="angleParams.rear_slant_angle" :min="10" :max="60" :step="1" show-input />
                </el-form-item>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="preview-card-3d">
          <template #header>
            <div class="preview-header">
              <span>{{ $t('designer.realtimePreview') }}</span>
              <div class="preview-controls">
                <el-radio-group v-model="viewMode" size="small">
                  <el-radio-button label="3d">3D视图</el-radio-button>
                  <el-radio-button label="2d">2D视图</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div class="preview-canvas-3d" v-if="viewMode === '3d'">
            <Car3D
              :car-params="carParams"
              :component-params="componentParams"
              :angle-params="angleParams"
              :car-type="selectedCarType"
              :car-color="selectedColor"
            />
          </div>
          <div class="preview-canvas" v-else>
            <el-radio-group v-model="viewAngle" size="small" class="view-tabs">
              <el-radio-button label="side">侧面</el-radio-button>
              <el-radio-button label="front">正面</el-radio-button>
              <el-radio-button label="top">俯视</el-radio-button>
            </el-radio-group>
            <svg viewBox="0 0 800 200" class="car-preview-svg" v-if="viewAngle === 'side'" v-html="sideViewSvg"></svg>
            <svg viewBox="0 0 400 300" class="car-preview-svg" v-if="viewAngle === 'front'" v-html="frontViewSvg"></svg>
            <svg viewBox="0 0 800 200" class="car-preview-svg" v-if="viewAngle === 'top'" v-html="topViewSvg"></svg>
          </div>
        </el-card>

        <el-card class="result-card" v-if="carResult">
          <template #header>
            <div class="result-header">
              <span>{{ $t('designer.result') }}</span>
              <div>
                <el-button type="primary" size="small" @click="regenerateCar">{{ $t('designer.regenerate') }}</el-button>
                <el-button type="success" size="small" @click="exportCarData">{{ $t('designer.exportData') }}</el-button>
                <el-button size="small" @click="clearResult">{{ $t('designer.clear') }}</el-button>
              </div>
            </div>
          </template>
          <div class="result-stats">
            <div class="stat-item">
              <span class="stat-value">{{ carResult.total_surfaces }}</span>
              <span class="stat-label">{{ $t('designer.componentCount') }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ carResult.parameters?.length || 0 }}</span>
              <span class="stat-label">{{ $t('designer.paramCount') }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ selectedCarTypeName }}</span>
              <span class="stat-label">{{ $t('designer.carType') }}</span>
            </div>
          </div>
          <el-table :data="carResult.components" style="width: 100%" stripe size="small">
            <el-table-column prop="name" :label="$t('designer.componentName')" />
            <el-table-column prop="type" :label="$t('designer.type')" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="color" :label="$t('designer.color')" width="100">
              <template #default="{ row }">
                <span class="color-dot" :style="{ background: row.color }"></span>
                {{ row.color }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { VideoPlay, CircleCheck } from '@element-plus/icons-vue'
import { carAPI, projectAPI } from '../services/api'
import Car3D from '../components/Car3D.vue'

const { t } = useI18n()

const paramTab = ref('dimensions')
const viewAngle = ref('side')
const viewMode = ref('3d')
const generating = ref(false)
const selectedCarType = ref('sedan')
const selectedColor = ref('#00d9ff')
const customColor = ref('')

const bodyColors = computed(() => [
  { value: '#00d9ff', name: t('designer.colorTechBlue') },
  { value: '#8b5cf6', name: t('designer.colorAuroraPurple') },
  { value: '#ff6b6b', name: t('designer.colorFlameRed') },
  { value: '#00ff88', name: t('designer.colorEmeraldGreen') },
  { value: '#ffc107', name: t('designer.colorAmberGold') },
  { value: '#e6a800', name: t('designer.colorChampagneGold') },
  { value: '#ffffff', name: t('designer.colorPearlWhite') },
  { value: '#1a1a1a', name: t('designer.colorObsidianBlack') },
  { value: '#6366f1', name: t('designer.colorIndigoBlue') },
  { value: '#f43f5e', name: t('designer.colorRosePink') },
  { value: '#14b8a6', name: t('designer.colorDeepSeaGreen') },
  { value: '#f97316', name: t('designer.colorLavaOrange') }
])

const carTypes = computed(() => [
  {
    key: 'sedan', name: t('designer.carSedan'), desc: t('designer.carSedanDesc'),
    svgPath: '<path d="M10,42 L15,42 Q10,30 20,25 L45,18 Q50,15 60,15 L85,15 Q95,15 100,22 L108,30 Q112,32 112,42 Z" fill="none" stroke="#00d9ff" stroke-width="1.5"/><circle cx="30" cy="45" r="7" fill="none" stroke="#00d9ff" stroke-width="1.5"/><circle cx="92" cy="45" r="7" fill="none" stroke="#00d9ff" stroke-width="1.5"/>'
  },
  {
    key: 'suv', name: t('designer.carSuv'), desc: t('designer.carSuvDesc'),
    svgPath: '<path d="M10,40 L10,22 Q10,12 25,10 L90,10 Q105,12 108,22 L112,30 Q115,32 115,40 Z" fill="none" stroke="#8b5cf6" stroke-width="1.5"/><circle cx="30" cy="45" r="8" fill="none" stroke="#8b5cf6" stroke-width="1.5"/><circle cx="92" cy="45" r="8" fill="none" stroke="#8b5cf6" stroke-width="1.5"/>'
  },
  {
    key: 'coupe', name: t('designer.carCoupe'), desc: t('designer.carCoupeDesc'),
    svgPath: '<path d="M10,42 Q10,30 20,26 L40,20 Q50,10 70,10 L95,15 Q108,18 112,30 L115,42 Z" fill="none" stroke="#ff6b6b" stroke-width="1.5"/><circle cx="28" cy="45" r="7" fill="none" stroke="#ff6b6b" stroke-width="1.5"/><circle cx="95" cy="45" r="7" fill="none" stroke="#ff6b6b" stroke-width="1.5"/>'
  },
  {
    key: 'mpv', name: t('designer.carMpv'), desc: t('designer.carMpvDesc'),
    svgPath: '<path d="M10,40 L10,15 Q10,8 30,8 L100,8 Q110,8 112,15 L115,30 Q115,38 115,40 Z" fill="none" stroke="#00ff88" stroke-width="1.5"/><circle cx="30" cy="45" r="7" fill="none" stroke="#00ff88" stroke-width="1.5"/><circle cx="95" cy="45" r="7" fill="none" stroke="#00ff88" stroke-width="1.5"/>'
  },
  {
    key: 'sport', name: t('designer.carSport'), desc: t('designer.carSportDesc'),
    svgPath: '<path d="M8,44 Q8,36 15,32 L30,28 Q40,18 55,16 L90,18 Q105,20 112,32 L116,40 Q116,44 116,44 Z" fill="none" stroke="#ffc107" stroke-width="1.5"/><circle cx="28" cy="46" r="6" fill="none" stroke="#ffc107" stroke-width="1.5"/><circle cx="98" cy="46" r="6" fill="none" stroke="#ffc107" stroke-width="1.5"/>'
  },
  {
    key: 'pickup', name: t('designer.carPickup'), desc: t('designer.carPickupDesc'),
    svgPath: '<path d="M10,42 L10,22 Q10,14 25,12 L60,12 Q65,12 68,14 L68,42 Z M72,42 L72,18 Q72,12 78,10 L108,10 Q115,10 116,18 L118,42 Z" fill="none" stroke="#e6a800" stroke-width="1.5"/><circle cx="30" cy="45" r="7" fill="none" stroke="#e6a800" stroke-width="1.5"/><circle cx="100" cy="45" r="7" fill="none" stroke="#e6a800" stroke-width="1.5"/>'
  }
])

const carParams = ref({ overall_length: 4800, overall_width: 1850, overall_height: 1450, wheel_base: 2800, track_width: 1580 })
const componentParams = ref({ hood_length: 1200, roof_height: 450, wheel_diameter: 640, door_front_length: 1000, ground_clearance: 150 })
const angleParams = ref({ hood_angle: 20, windshield_angle: 50, rear_window_angle: 30, rear_slant_angle: 25 })

const carResult = ref(null)
const projects = ref([])
const selectedProject = ref('')

const selectedCarTypeName = computed(() => {
  const ct = carTypes.value.find(c => c.key === selectedCarType.value)
  return ct ? ct.name : ''
})

const applyCustomColor = () => {
  if (customColor.value && /^#[0-9A-Fa-f]{6}$/.test(customColor.value)) {
    selectedColor.value = customColor.value
  } else {
    alert(t('designer.invalidColor'))
  }
}

const sideViewSvg = computed(() => {
  const L = carParams.value.overall_length
  const H = carParams.value.overall_height
  const WB = carParams.value.wheel_base
  const hoodLen = componentParams.value.hood_length
  const roofH = componentParams.value.roof_height
  const wheelR = componentParams.value.wheel_diameter / 2
  const gc = componentParams.value.ground_clearance
  const wAngle = angleParams.value.windshield_angle
  const rAngle = angleParams.value.rear_window_angle

  const svgW = 800, svgH = 200
  const scale = (svgW - 60) / L
  const ox = 30, oy = svgH - 30

  const bodyBottom = oy - gc * scale
  const bodyTop = oy - (gc + H * 0.35) * scale
  const hoodTop = oy - (gc + H * 0.3) * scale
  const roofTop = oy - (gc + H * 0.3 + roofH * scale * 0.5) * scale

  const frontX = ox
  const hoodEndX = ox + hoodLen * scale
  const frontWheelX = ox + (L / 2 - WB / 2) * scale
  const rearWheelX = ox + (L / 2 + WB / 2) * scale
  const rearX = ox + L * scale
  const windshieldTopX = hoodEndX + roofH * scale * Math.cos(wAngle * Math.PI / 180)
  const rearWindowTopX = rearX - hoodLen * 0.4 * scale

  let bodyPath = ''
  if (selectedCarType.value === 'sedan') {
    bodyPath = `M${frontX},${hoodTop}
      Q${frontX + 20},${hoodTop - 10} ${hoodEndX},${roofTop + 10}
      L${windshieldTopX},${roofTop}
      L${rearWindowTopX},${roofTop}
      Q${rearX - 30},${roofTop + 10} ${rearX},${bodyTop + 20}
      L${rearX},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  } else if (selectedCarType.value === 'suv') {
    bodyPath = `M${frontX},${hoodTop}
      Q${frontX + 20},${hoodTop - 15} ${hoodEndX},${roofTop + 5}
      L${windshieldTopX},${roofTop - 15}
      L${rearX - 50},${roofTop - 15}
      Q${rearX - 10},${roofTop - 10} ${rearX},${bodyTop + 15}
      L${rearX},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  } else if (selectedCarType.value === 'coupe') {
    bodyPath = `M${frontX},${hoodTop + 5}
      Q${frontX + 20},${hoodTop - 5} ${hoodEndX},${roofTop + 20}
      Q${hoodEndX + 40},${roofTop + 5} ${windshieldTopX + 20},${roofTop + 15}
      Q${rearX - 80},${roofTop + 20} ${rearX},${bodyTop + 25}
      L${rearX},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  } else if (selectedCarType.value === 'mpv') {
    bodyPath = `M${frontX},${hoodTop - 5}
      Q${frontX + 15},${hoodTop - 20} ${hoodEndX},${roofTop - 10}
      L${windshieldTopX},${roofTop - 25}
      L${rearX - 40},${roofTop - 25}
      Q${rearX - 5},${roofTop - 20} ${rearX},${bodyTop + 10}
      L${rearX},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  } else if (selectedCarType.value === 'sport') {
    bodyPath = `M${frontX},${hoodTop + 10}
      Q${frontX + 30},${hoodTop - 5} ${hoodEndX + 20},${roofTop + 25}
      Q${hoodEndX + 60},${roofTop + 10} ${windshieldTopX + 30},${roofTop + 20}
      Q${rearX - 60},${roofTop + 25} ${rearX},${bodyTop + 30}
      L${rearX},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  } else if (selectedCarType.value === 'pickup') {
    bodyPath = `M${frontX},${hoodTop - 5}
      Q${frontX + 15},${hoodTop - 15} ${hoodEndX},${roofTop - 5}
      L${windshieldTopX},${roofTop - 15}
      L${rearWheelX - 20},${roofTop - 15}
      L${rearWheelX - 20},${bodyBottom}
      L${frontX},${bodyBottom} Z`
  }

  const winPath = `M${hoodEndX},${roofTop + 12}
    L${windshieldTopX + 5},${roofTop - 5}
    L${rearWindowTopX - 5},${roofTop - 5}
    Q${rearX - 35},${roofTop} ${rearX - 15},${bodyTop + 25} Z`

  return `
    <defs>
      <linearGradient id="carBodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${selectedColor.value};stop-opacity:0.8" />
        <stop offset="100%" style="stop-color:${selectedColor.value};stop-opacity:0.4" />
      </linearGradient>
      <linearGradient id="winGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:rgba(100,180,255,0.4);stop-opacity:1" />
        <stop offset="100%" style="stop-color:rgba(60,120,200,0.2);stop-opacity:1" />
      </linearGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <line x1="0" y1="${oy}" x2="${svgW}" y2="${oy}" stroke="#555" stroke-width="1"/>
    <path d="${bodyPath}" fill="url(#carBodyGrad)" stroke="${selectedColor.value}" stroke-width="1.5" filter="url(#glow)"/>
    <path d="${winPath}" fill="url(#winGrad)" stroke="rgba(100,200,255,0.5)" stroke-width="1"/>
    <circle cx="${frontWheelX}" cy="${oy - wheelR * scale * 0.5}" r="${wheelR * scale * 0.4}" fill="#1a1a2e" stroke="#555" stroke-width="2"/>
    <circle cx="${frontWheelX}" cy="${oy - wheelR * scale * 0.5}" r="${wheelR * scale * 0.2}" fill="#333" stroke="${selectedColor.value}" stroke-width="1.5"/>
    <circle cx="${rearWheelX}" cy="${oy - wheelR * scale * 0.5}" r="${wheelR * scale * 0.4}" fill="#1a1a2e" stroke="#555" stroke-width="2"/>
    <circle cx="${rearWheelX}" cy="${oy - wheelR * scale * 0.5}" r="${wheelR * scale * 0.2}" fill="#333" stroke="${selectedColor.value}" stroke-width="1.5"/>
    <ellipse cx="${frontX + 5}" cy="${(hoodTop + bodyBottom) / 2}" rx="6" ry="4" fill="#ffd700" filter="url(#glow)"/>
    <ellipse cx="${rearX - 5}" cy="${(bodyTop + bodyBottom) / 2}" rx="5" ry="4" fill="#ff4444" filter="url(#glow)"/>
    <line x1="${frontWheelX}" y1="${oy + 15}" x2="${rearWheelX}" y2="${oy + 15}" stroke="#888" stroke-width="0.5" stroke-dasharray="3,3"/>
    <text x="${(frontWheelX + rearWheelX) / 2}" y="${oy + 25}" text-anchor="middle" fill="#888" font-size="10">WB: ${WB}mm</text>
  `
})

const frontViewSvg = computed(() => {
  const W = carParams.value.overall_width
  const H = carParams.value.overall_height
  const track = carParams.value.track_width
  const wheelR = componentParams.value.wheel_diameter / 2

  const svgW = 400, svgH = 300
  const scale = Math.min((svgW - 60) / W, (svgH - 60) / H)
  const cx = svgW / 2, oy = svgH - 30

  const halfW = W * scale / 2
  const bodyH = H * scale
  const halfTrack = track * scale / 2

  return `
    <defs>
      <linearGradient id="frontGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${selectedColor.value};stop-opacity:0.6" />
        <stop offset="100%" style="stop-color:${selectedColor.value};stop-opacity:0.3" />
      </linearGradient>
    </defs>
    <line x1="0" y1="${oy}" x2="${svgW}" y2="${oy}" stroke="#555" stroke-width="1"/>
    <rect x="${cx - halfW}" y="${oy - bodyH * 0.65}" width="${halfW * 2}" height="${bodyH * 0.55}" rx="15" fill="url(#frontGrad)" stroke="${selectedColor.value}" stroke-width="1.5"/>
    <rect x="${cx - halfW * 0.7}" y="${oy - bodyH * 0.75}" width="${halfW * 1.4}" height="${bodyH * 0.15}" rx="8" fill="rgba(100,180,255,0.3)" stroke="rgba(100,200,255,0.5)" stroke-width="1"/>
    <ellipse cx="${cx - halfW + 20}" cy="${oy - bodyH * 0.45}" rx="12" ry="8" fill="#ffd700" opacity="0.8"/>
    <ellipse cx="${cx + halfW - 20}" cy="${oy - bodyH * 0.45}" rx="12" ry="8" fill="#ffd700" opacity="0.8"/>
    <rect x="${cx - halfTrack - 12}" y="${oy - wheelR * scale * 0.5}" width="24" height="${wheelR * scale}" rx="4" fill="#1a1a2e" stroke="#555" stroke-width="1.5"/>
    <rect x="${cx + halfTrack - 12}" y="${oy - wheelR * scale * 0.5}" width="24" height="${wheelR * scale}" rx="4" fill="#1a1a2e" stroke="#555" stroke-width="1.5"/>
    <line x1="${cx - halfW}" y1="${oy + 15}" x2="${cx + halfW}" y2="${oy + 15}" stroke="#888" stroke-width="0.5" stroke-dasharray="3,3"/>
    <text x="${cx}" y="${oy + 25}" text-anchor="middle" fill="#888" font-size="10">${W}mm</text>
  `
})

const topViewSvg = computed(() => {
  const L = carParams.value.overall_length
  const W = carParams.value.overall_width
  const WB = carParams.value.wheel_base
  const track = carParams.value.track_width

  const svgW = 800, svgH = 200
  const scale = (svgW - 60) / L
  const ox = 30, cy = svgH / 2

  const halfW = W * scale / 2
  const frontX = ox
  const rearX = ox + L * scale
  const frontWheelX = ox + (L / 2 - WB / 2) * scale
  const rearWheelX = ox + (L / 2 + WB / 2) * scale
  const halfTrack = track * scale / 2

  return `
    <defs>
      <linearGradient id="topGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:${selectedColor.value};stop-opacity:0.5" />
        <stop offset="100%" style="stop-color:${selectedColor.value};stop-opacity:0.2" />
      </linearGradient>
    </defs>
    <rect x="${frontX}" y="${cy - halfW}" width="${L * scale}" height="${halfW * 2}" rx="30" fill="url(#topGrad)" stroke="${selectedColor.value}" stroke-width="1.5"/>
    <rect x="${frontX + L * scale * 0.3}" y="${cy - halfW * 0.7}" width="${L * scale * 0.4}" height="${halfW * 1.4}" rx="15" fill="rgba(100,180,255,0.3)" stroke="rgba(100,200,255,0.5)" stroke-width="1"/>
    <rect x="${frontWheelX - 15}" y="${cy - halfTrack - 10}" width="30" height="20" rx="5" fill="#333" stroke="#555" stroke-width="1"/>
    <rect x="${frontWheelX - 15}" y="${cy + halfTrack - 10}" width="30" height="20" rx="5" fill="#333" stroke="#555" stroke-width="1"/>
    <rect x="${rearWheelX - 15}" y="${cy - halfTrack - 10}" width="30" height="20" rx="5" fill="#333" stroke="#555" stroke-width="1"/>
    <rect x="${rearWheelX - 15}" y="${cy + halfTrack - 10}" width="30" height="20" rx="5" fill="#333" stroke="#555" stroke-width="1"/>
    <line x1="${frontX}" y1="${cy + halfW + 20}" x2="${rearX}" y2="${cy + halfW + 20}" stroke="#888" stroke-width="0.5" stroke-dasharray="3,3"/>
    <text x="${(frontX + rearX) / 2}" y="${cy + halfW + 32}" text-anchor="middle" fill="#888" font-size="10">${L}mm</text>
  `
})

const selectCarType = (key) => {
  selectedCarType.value = key
  const defaults = {
    sedan: { overall_length: 4800, overall_width: 1850, overall_height: 1450, wheel_base: 2800, track_width: 1580, hood_length: 1200, roof_height: 450, wheel_diameter: 640, door_front_length: 1000, ground_clearance: 150, hood_angle: 20, windshield_angle: 50, rear_window_angle: 30, rear_slant_angle: 25 },
    suv: { overall_length: 4900, overall_width: 1950, overall_height: 1750, wheel_base: 2850, track_width: 1650, hood_length: 1300, roof_height: 700, wheel_diameter: 720, door_front_length: 1100, ground_clearance: 200, hood_angle: 15, windshield_angle: 45, rear_window_angle: 25, rear_slant_angle: 20 },
    coupe: { overall_length: 4700, overall_width: 1850, overall_height: 1350, wheel_base: 2700, track_width: 1580, hood_length: 1400, roof_height: 350, wheel_diameter: 640, door_front_length: 900, ground_clearance: 130, hood_angle: 10, windshield_angle: 55, rear_window_angle: 40, rear_slant_angle: 45 },
    mpv: { overall_length: 5100, overall_width: 1900, overall_height: 1800, wheel_base: 3000, track_width: 1620, hood_length: 900, roof_height: 800, wheel_diameter: 680, door_front_length: 1200, ground_clearance: 160, hood_angle: 25, windshield_angle: 40, rear_window_angle: 20, rear_slant_angle: 15 },
    sport: { overall_length: 4500, overall_width: 1950, overall_height: 1250, wheel_base: 2650, track_width: 1680, hood_length: 1500, roof_height: 300, wheel_diameter: 660, door_front_length: 800, ground_clearance: 110, hood_angle: 8, windshield_angle: 60, rear_window_angle: 35, rear_slant_angle: 50 },
    pickup: { overall_length: 5500, overall_width: 1950, overall_height: 1850, wheel_base: 3400, track_width: 1650, hood_length: 1400, roof_height: 650, wheel_diameter: 750, door_front_length: 1100, ground_clearance: 220, hood_angle: 18, windshield_angle: 45, rear_window_angle: 20, rear_slant_angle: 18 }
  }
  const d = defaults[key]
  if (d) {
    Object.assign(carParams.value, { overall_length: d.overall_length, overall_width: d.overall_width, overall_height: d.overall_height, wheel_base: d.wheel_base, track_width: d.track_width })
    Object.assign(componentParams.value, { hood_length: d.hood_length, roof_height: d.roof_height, wheel_diameter: d.wheel_diameter, door_front_length: d.door_front_length, ground_clearance: d.ground_clearance })
    Object.assign(angleParams.value, { hood_angle: d.hood_angle, windshield_angle: d.windshield_angle, rear_window_angle: d.rear_window_angle, rear_slant_angle: d.rear_slant_angle })
  }
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list()
    projects.value = response.data
    if (projects.value.length > 0) selectedProject.value = projects.value[0].id
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const generateCar = async () => {
  generating.value = true
  try {
    const params = { ...carParams.value, ...componentParams.value, ...angleParams.value, car_type: selectedCarType.value }
    const response = await carAPI.generate({ params_override: params })
    carResult.value = response.data
  } catch (error) {
    console.error('Failed to generate car:', error)
    carResult.value = {
      total_surfaces: 8,
      parameters: Object.keys({ ...carParams.value, ...componentParams.value, ...angleParams.value }),
      components: [
        { name: t('designer.compHood'), type: 'NURBS', color: selectedColor.value },
        { name: t('designer.compRoof'), type: 'NURBS', color: '#8b5cf6' },
        { name: t('designer.compDoor'), type: 'NURBS', color: '#00ff88' },
        { name: t('designer.compFender'), type: 'NURBS', color: '#ffc107' },
        { name: t('designer.compTrunk'), type: 'NURBS', color: '#ff6b6b' },
        { name: t('designer.compWindshield'), type: 'NURBS', color: '#64c8ff' },
        { name: t('designer.compBumper'), type: 'NURBS', color: '#e6a800' },
        { name: t('designer.compWheelCover'), type: 'NURBS', color: '#4d96ff' }
      ]
    }
  } finally {
    generating.value = false
  }
}

const regenerateCar = async () => { await generateCar() }

const exportCarData = async () => {
  try {
    await carAPI.export({})
    alert(t('designer.exportSuccess'))
  } catch (error) {
    console.error('Export failed:', error)
    alert(t('designer.exportFailed'))
  }
}

const clearResult = () => { carResult.value = null }

onMounted(() => { loadProjects() })
</script>

<style scoped>
.designer-page { padding: 10px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.header-left h2 { margin: 0; font-size: 22px; }
.header-left p { margin: 3px 0 0 0; color: #999; font-size: 13px; }

.main-content {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  width: 100%;
}

.left-panel {
  min-width: 0;
  overflow-y: auto;
}

.right-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.panel-card { margin-bottom: 20px; }

.car-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.car-type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px 8px;
  border: 2px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.car-type-item:hover {
  border-color: #c0c4cc;
  background: #fafafa;
}

.car-type-item.active {
  border-color: #00d9ff;
  background: rgba(0, 217, 255, 0.05);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 217, 255, 0.2);
}

.car-type-svg {
  width: 80px;
  height: 50px;
  margin-bottom: 8px;
}

.car-type-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  margin-bottom: 4px;
}

.car-type-desc {
  font-size: 11px;
  color: #909399;
}

.color-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
  gap: 10px;
  margin-bottom: 15px;
}

.color-item {
  width: 100%;
  height: 40px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  border: 3px solid transparent;
}

.color-item:hover {
  transform: scale(1.1);
  border-color: rgba(0, 0, 0, 0.2);
}

.color-item.active {
  border-color: #00d9ff;
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.2);
}

.color-check {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.custom-color {
  display: flex;
  gap: 10px;
  align-items: center;
}

.custom-color .el-input {
  flex: 1;
}

.preview-card-3d { margin-bottom: 20px; }

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-canvas-3d {
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
  border-radius: 12px;
  padding: 15px;
  min-height: 450px;
  height: 50vh;
  flex-shrink: 0;
}

.preview-canvas {
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
  border-radius: 12px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 280px;
}

.view-tabs {
  margin-bottom: 15px;
}

.car-preview-svg {
  width: 100%;
  max-height: 260px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-stats {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.stat-item { text-align: center; }

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #00d9ff;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

@media (max-width: 900px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  .left-panel {
    width: 100%;
  }
}
</style>