<template>
  <div class="demo-container">
    <!-- 粒子背景 -->
    <div class="particle-container">
      <div v-for="i in 50" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>

    <!-- 录制指示器 -->
    <div class="recording-indicator" v-if="isRecording">
      <div class="recording-dot"></div>
      <span>{{ $t('demo.recording') }} {{ recordingTime }}</span>
    </div>

    <!-- 横幅 -->
    <div class="banner">
      <h1>⚡ EVOLUTION AI</h1>
      <p class="subtitle">{{ $t('demo.subtitle') }}</p>
      <div class="tagline">◈ {{ $t('demo.nurbsSurface') }} ◈ {{ $t('demo.topologyOpt') }} ◈ {{ $t('demo.qualityCheck') }} ◈ {{ $t('demo.dataHandover') }} ◈</div>
    </div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <el-button type="primary" size="large" @click="startDemo" :disabled="isRunning">
        <el-icon><VideoPlay /></el-icon>
        {{ $t('demo.startDemo') }}
      </el-button>
      <el-button type="success" size="large" @click="startRecording" v-if="!isRecording">
        <el-icon><VideoCamera /></el-icon>
        {{ $t('demo.recordVideo') }}
      </el-button>
      <el-button type="danger" size="large" @click="stopRecording" v-else>
        <el-icon><VideoPause /></el-icon>
        {{ $t('demo.stopRecording') }}
      </el-button>
      <el-button size="large" @click="resetDemo">
        <el-icon><RefreshRight /></el-icon>
        {{ $t('demo.reset') }}
      </el-button>
      <el-button type="warning" size="large" @click="downloadVideo" v-if="hasRecording">
        <el-icon><Download /></el-icon>
        {{ $t('demo.downloadVideo') }}
      </el-button>
    </div>

    <!-- 主进度条 -->
    <el-card class="progress-card">
      <div class="progress-header">
        <div class="progress-title">
          <el-icon><DataLine /></el-icon>
          <span>{{ $t('demo.overallProgress') }}</span>
        </div>
        <div class="progress-stats">
          <div class="stat-item">
            <el-icon><Timer /></el-icon>
            <span>{{ $t('demo.elapsedTime') }}:</span>
            <span class="stat-value">{{ elapsedTime }}</span>
          </div>
          <div class="stat-item">
            <el-icon><Clock /></el-icon>
            <span>{{ $t('demo.estimatedRemaining') }}:</span>
            <span class="stat-value">{{ remainingTime }}</span>
          </div>
        </div>
      </div>
      <el-progress
        :percentage="overallProgress"
        :stroke-width="25"
        :format="progressFormat"
        class="main-progress"
        :color="progressColors"
      />
      <div class="progress-info">
        <span>{{ currentTask }}</span>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <div class="stats-panel">
      <el-card class="stat-card">
        <div class="stat-icon">🎨</div>
        <div class="stat-value">{{ stats.surfaces }}</div>
        <div class="stat-label">{{ $t('demo.surfacesCreated') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{{ stats.qualityScore || '--' }}</div>
        <div class="stat-label">{{ $t('demo.qualityScore') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">{{ stats.optimizationRate || '--' }}</div>
        <div class="stat-label">{{ $t('demo.optimizationRate') }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">📤</div>
        <div class="stat-value">{{ stats.handoverFormats }}</div>
        <div class="stat-label">{{ $t('demo.handoverFormats') }}</div>
      </el-card>
    </div>

    <!-- 场景卡片 -->
    <div class="scenes-grid">
      <el-card
        v-for="(scene, index) in scenes"
        :key="scene.id"
        class="scene-card"
        :class="{ active: scene.status === 'running', completed: scene.status === 'completed' }"
      >
        <div class="scene-header">
          <div class="scene-title">
            <span class="scene-icon">{{ scene.icon }}</span>
            <span>{{ getSceneName(index) }}</span>
          </div>
          <el-tag :type="getSceneTagType(scene.status)" effect="dark">
            {{ getSceneStatusText(scene.status) }}
          </el-tag>
        </div>
        <p class="scene-description">{{ getSceneDescription(index) }}</p>
        <el-progress
          :percentage="scene.progress"
          :stroke-width="8"
          :show-text="false"
          :color="scene.status === 'completed' ? '#00ff88' : '#00d4ff'"
        />
        <div class="scene-metrics">
          <div class="metric" v-for="(metric, key) in scene.metrics" :key="key">
            <span>{{ getMetricLabel(index, key) }}:</span>
            <span class="metric-value">{{ metric.value }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 车与曲面生成过程区 -->
    <el-card class="car-model-card">
      <div class="car-model-header">
        <span class="car-model-title">🚗 {{ $t('demo.carModel') }}</span>
        <el-tag type="success">{{ currentCarModel }}</el-tag>
      </div>
      <div class="car-surface-layout">
        <!-- 左侧：车型侧面轮廓 + 曲面逐步生成 -->
        <div class="car-surface-visual">
          <svg viewBox="0 0 520 280" class="car-surface-svg">
            <defs>
              <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#00d4ff;stop-opacity:0.9" />
                <stop offset="50%" style="stop-color:#8b5cf6;stop-opacity:0.9" />
                <stop offset="100%" style="stop-color:#00ff88;stop-opacity:0.9" />
              </linearGradient>
              <linearGradient id="hoodGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#00d4ff;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#0099cc;stop-opacity:0.7" />
              </linearGradient>
              <linearGradient id="roofGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#6d28d9;stop-opacity:0.7" />
              </linearGradient>
              <linearGradient id="doorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#00ff88;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#00cc6a;stop-opacity:0.7" />
              </linearGradient>
              <linearGradient id="fenderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#ffc107;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#e6a800;stop-opacity:0.7" />
              </linearGradient>
              <linearGradient id="trunkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#ff6b6b;stop-opacity:0.7" />
                <stop offset="100%" style="stop-color:#e63946;stop-opacity:0.7" />
              </linearGradient>
              <linearGradient id="winGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:rgba(100,200,255,0.5);stop-opacity:1" />
                <stop offset="100%" style="stop-color:rgba(60,120,200,0.3);stop-opacity:1" />
              </linearGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
              <filter id="surfaceGlow">
                <feGaussianBlur stdDeviation="2" result="blur"/>
                <feMerge>
                  <feMergeNode in="blur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>

            <!-- 地面阴影 -->
            <ellipse cx="260" cy="240" rx="220" ry="20" fill="rgba(0,0,0,0.3)"/>

            <!-- 车身轮廓线（始终显示） -->
            <path d="M60,155 L60,130 Q60,105 80,95 L140,80 Q160,75 175,60 L195,45 Q210,38 230,38 L310,38 Q340,38 360,55 L380,75 Q400,80 420,95 Q450,105 450,130 L450,155 Q450,170 440,175 L400,185 Q380,195 370,195 L320,195 Q310,195 310,195 L200,195 Q190,195 170,195 L120,195 Q100,195 90,185 L70,175 Q60,170 60,155 Z"
              fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="1" stroke-dasharray="4,4"/>

            <!-- 曲面1：发动机盖 -->
            <g v-if="carSurfaces.hood" class="surface-appear">
              <path d="M60,130 Q60,105 80,95 L140,80 Q160,75 175,60 L195,45 Q210,42 230,42 L230,130 Z"
                fill="url(#hoodGrad)" stroke="#00d4ff" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="120" y="100" fill="#00d4ff" font-size="11" font-weight="bold">{{ $t('demo.hood') }}</text>
              <!-- 控制点 -->
              <circle cx="80" cy="95" r="3" fill="#00d4ff" opacity="0.8"/>
              <circle cx="140" cy="80" r="3" fill="#00d4ff" opacity="0.8"/>
              <circle cx="175" cy="60" r="3" fill="#00d4ff" opacity="0.8"/>
              <circle cx="195" cy="45" r="3" fill="#00d4ff" opacity="0.8"/>
              <!-- 控制网格线 -->
              <line x1="80" y1="95" x2="140" y2="80" stroke="#00d4ff" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
              <line x1="140" y1="80" x2="195" y2="45" stroke="#00d4ff" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 曲面2：车顶 -->
            <g v-if="carSurfaces.roof" class="surface-appear">
              <path d="M230,42 L310,42 Q340,42 360,55 L360,130 L230,130 Z"
                fill="url(#roofGrad)" stroke="#8b5cf6" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="265" y="75" fill="#8b5cf6" font-size="11" font-weight="bold">{{ $t('demo.roof') }}</text>
              <circle cx="230" cy="42" r="3" fill="#8b5cf6" opacity="0.8"/>
              <circle cx="310" cy="42" r="3" fill="#8b5cf6" opacity="0.8"/>
              <circle cx="360" cy="55" r="3" fill="#8b5cf6" opacity="0.8"/>
              <line x1="230" y1="42" x2="310" y2="42" stroke="#8b5cf6" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
              <line x1="310" y1="42" x2="360" y2="55" stroke="#8b5cf6" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 曲面3：前挡风玻璃 -->
            <g v-if="carSurfaces.roof" class="surface-appear">
              <path d="M195,45 Q210,38 230,38 L230,42 L195,45 Z M175,60 L195,45 L230,42 L230,130 L175,130 Z"
                fill="url(#winGrad)" stroke="rgba(100,200,255,0.6)" stroke-width="1" filter="url(#surfaceGlow)"/>
            </g>

            <!-- 曲面4：后挡风玻璃 -->
            <g v-if="carSurfaces.roof" class="surface-appear">
              <path d="M360,55 L380,75 Q400,80 420,95 L420,130 L360,130 Z"
                fill="url(#winGrad)" stroke="rgba(100,200,255,0.6)" stroke-width="1" filter="url(#surfaceGlow)"/>
            </g>

            <!-- 曲面5：车门 -->
            <g v-if="carSurfaces.door" class="surface-appear">
              <path d="M175,130 L175,60 Q190,50 210,42 L230,42 L360,55 L360,130 Z"
                fill="none" stroke="none"/>
              <path d="M175,130 L175,80 L360,80 L360,130 Z"
                fill="url(#doorGrad)" stroke="#00ff88" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="240" y="110" fill="#00ff88" font-size="11" font-weight="bold">{{ $t('demo.door') }}</text>
              <!-- 门缝线 -->
              <line x1="268" y1="80" x2="268" y2="130" stroke="rgba(255,255,255,0.3)" stroke-width="1"/>
              <circle cx="255" cy="105" r="2" fill="#fff" opacity="0.8"/>
              <circle cx="280" cy="105" r="2" fill="#fff" opacity="0.8"/>
              <line x1="255" y1="105" x2="268" y2="80" stroke="#00ff88" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
              <line x1="280" y1="105" x2="268" y2="80" stroke="#00ff88" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 曲面6：前翼子板 -->
            <g v-if="carSurfaces.fender" class="surface-appear">
              <path d="M60,130 Q60,155 70,175 L120,195 L170,195 L170,130 Z"
                fill="url(#fenderGrad)" stroke="#ffc107" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="85" y="170" fill="#ffc107" font-size="10" font-weight="bold">{{ $t('demo.frontFender') }}</text>
              <circle cx="70" cy="175" r="3" fill="#ffc107" opacity="0.8"/>
              <circle cx="120" cy="195" r="3" fill="#ffc107" opacity="0.8"/>
              <circle cx="170" cy="195" r="3" fill="#ffc107" opacity="0.8"/>
              <line x1="70" y1="175" x2="120" y2="195" stroke="#ffc107" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
              <line x1="120" y1="195" x2="170" y2="195" stroke="#ffc107" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 曲面7：后翼子板 -->
            <g v-if="carSurfaces.fender" class="surface-appear">
              <path d="M360,130 L360,195 L400,195 Q430,195 440,175 L450,155 Q450,130 450,130 Z"
                fill="url(#fenderGrad)" stroke="#ffc107" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="375" y="170" fill="#ffc107" font-size="10" font-weight="bold">{{ $t('demo.rearFender') }}</text>
              <circle cx="400" cy="195" r="3" fill="#ffc107" opacity="0.8"/>
              <circle cx="440" cy="175" r="3" fill="#ffc107" opacity="0.8"/>
              <line x1="360" y1="195" x2="400" y2="195" stroke="#ffc107" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
              <line x1="400" y1="195" x2="440" y2="175" stroke="#ffc107" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 曲面8：后备箱 -->
            <g v-if="carSurfaces.trunk" class="surface-appear">
              <path d="M360,80 L380,75 Q400,80 420,95 L450,130 L450,130 L360,130 Z"
                fill="url(#trunkGrad)" stroke="#ff6b6b" stroke-width="1.5" filter="url(#surfaceGlow)"/>
              <text x="380" y="110" fill="#ff6b6b" font-size="10" font-weight="bold">{{ $t('demo.trunk') }}</text>
              <circle cx="380" cy="75" r="3" fill="#ff6b6b" opacity="0.8"/>
              <circle cx="420" cy="95" r="3" fill="#ff6b6b" opacity="0.8"/>
              <line x1="380" y1="75" x2="420" y2="95" stroke="#ff6b6b" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.5"/>
            </g>

            <!-- 前轮（始终显示） -->
            <g>
              <circle cx="125" cy="210" r="28" fill="#1a1a2e" stroke="#444" stroke-width="3"/>
              <circle cx="125" cy="210" r="20" fill="#222" stroke="#555" stroke-width="2"/>
              <circle cx="125" cy="210" r="10" fill="#333" stroke="#00d4ff" stroke-width="2"/>
              <circle cx="125" cy="210" r="4" fill="#00d4ff"/>
              <!-- 轮辐 -->
              <line x1="125" y1="192" x2="125" y2="200" stroke="#555" stroke-width="1.5"/>
              <line x1="125" y1="220" x2="125" y2="228" stroke="#555" stroke-width="1.5"/>
              <line x1="107" y1="210" x2="115" y2="210" stroke="#555" stroke-width="1.5"/>
              <line x1="135" y1="210" x2="143" y2="210" stroke="#555" stroke-width="1.5"/>
            </g>

            <!-- 后轮（始终显示） -->
            <g>
              <circle cx="395" cy="210" r="28" fill="#1a1a2e" stroke="#444" stroke-width="3"/>
              <circle cx="395" cy="210" r="20" fill="#222" stroke="#555" stroke-width="2"/>
              <circle cx="395" cy="210" r="10" fill="#333" stroke="#8b5cf6" stroke-width="2"/>
              <circle cx="395" cy="210" r="4" fill="#8b5cf6"/>
              <line x1="395" y1="192" x2="395" y2="200" stroke="#555" stroke-width="1.5"/>
              <line x1="395" y1="220" x2="395" y2="228" stroke="#555" stroke-width="1.5"/>
              <line x1="377" y1="210" x2="385" y2="210" stroke="#555" stroke-width="1.5"/>
              <line x1="405" y1="210" x2="413" y2="210" stroke="#555" stroke-width="1.5"/>
            </g>

            <!-- 前灯 -->
            <ellipse cx="65" cy="120" rx="10" ry="6" fill="#ffd700" filter="url(#glow)" v-if="carSurfaces.hood"/>
            <!-- 尾灯 -->
            <ellipse cx="450" cy="120" rx="8" ry="6" fill="#ff4444" filter="url(#glow)" v-if="carSurfaces.trunk"/>

            <!-- 当前生成曲面高亮指示 -->
            <g v-if="generatingSurface">
              <rect :x="generatingSurface.x" :y="generatingSurface.y" :width="generatingSurface.w" :height="generatingSurface.h"
                fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="5,3" opacity="0.8">
                <animate attributeName="stroke-dashoffset" from="0" to="16" dur="1s" repeatCount="indefinite"/>
              </rect>
            </g>
          </svg>
        </div>

        <!-- 右侧：曲面生成列表 -->
        <div class="surface-list">
          <div class="surface-list-title">{{ $t('demo.surfaceGenerationSequence') }}</div>
          <div
            v-for="(surf, idx) in surfaceList"
            :key="idx"
            class="surface-item"
            :class="{ active: surf.generating, done: surf.done }"
          >
            <span class="surface-dot" :style="{ background: surf.color }"></span>
            <span class="surface-name">{{ getSurfaceName(idx) }}</span>
            <span class="surface-status">{{ surf.done ? '✓' : surf.generating ? '⏳' : '○' }}</span>
          </div>
          <div class="surface-summary">
            <span>{{ $t('demo.completedCount') }}: {{ completedSurfaceCount }} / {{ surfaceList.length }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 可视化区域 -->
    <el-card class="visualization-card">
      <div class="visualization-header">
        <span class="visualization-title">🎬 {{ $t('demo.realTimeVisualization') }}</span>
        <span>{{ visualizationStatus }}</span>
      </div>
      <div class="visualization-content">
        <canvas ref="canvasRef" class="canvas-3d"></canvas>
      </div>
    </el-card>

    <!-- 日志面板 -->
    <el-card class="log-card">
      <template #header>
        <div class="log-header">
          <el-icon><Document /></el-icon>
          <span>{{ $t('demo.operationLog') }}</span>
        </div>
      </template>
      <div class="log-entries">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-entry"
          :class="log.type"
        >
          <span class="log-time">[{{ log.time }}]</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>

    <!-- 完成模态框 -->
    <el-dialog v-model="showCompleteModal" :title="$t('demo.demoComplete')" width="500px" center>
      <div class="modal-content">
        <h2>🎉 {{ $t('demo.demoFinished') }}</h2>
        <p>{{ $t('demo.demoCompleteMsg') }}</p>
        <div class="modal-stats">
          <div class="modal-stat">
            <span class="modal-stat-label">{{ $t('demo.surfacesCreated') }}</span>
            <span class="modal-stat-value">{{ stats.surfaces }} {{ $t('common.other') }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">{{ $t('demo.qualityScore') }}</span>
            <span class="modal-stat-value">{{ stats.qualityScore }} {{ $t('common.other') }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">{{ $t('demo.optimizationRate') }}</span>
            <span class="modal-stat-value">{{ stats.optimizationRate }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCompleteModal = false">{{ $t('demo.close') }}</el-button>
        <el-button type="success" @click="downloadVideo" v-if="hasRecording">{{ $t('demo.downloadVideo') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  VideoPlay, VideoCamera, VideoPause, RefreshRight, Download,
  DataLine, Timer, Clock, Document
} from '@element-plus/icons-vue'

const { t } = useI18n()

// 状态
const isRunning = ref(false)
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingTime = ref('00:00')
const elapsedTime = ref('00:00')
const remainingTime = ref('--:--')
const overallProgress = ref(0)
const currentTask = ref('')
const etaEstimate = ref('')
const visualizationStatus = ref('')
const showCompleteModal = ref(false)

const currentCarModel = ref('EV-A7 Concept')

// 车型曲面状态
const carSurfaces = reactive({
  hood: false,
  roof: false,
  door: false,
  fender: false,
  trunk: false
})

const generatingSurface = ref(null)

// 曲面生成列表
const surfaceList = reactive([
  { name: '', color: '#00d4ff', key: 'hood', done: false, generating: false, x: 55, y: 35, w: 185, h: 100 },
  { name: '', color: '#8b5cf6', key: 'roof', done: false, generating: false, x: 225, y: 30, w: 145, h: 105 },
  { name: '', color: '#64c8ff', key: 'roof', done: false, generating: false, x: 170, y: 35, w: 65, h: 100 },
  { name: '', color: '#64c8ff', key: 'roof', done: false, generating: false, x: 355, y: 50, w: 70, h: 85 },
  { name: '', color: '#00ff88', key: 'door', done: false, generating: false, x: 170, y: 75, w: 195, h: 60 },
  { name: '', color: '#ffc107', key: 'fender', done: false, generating: false, x: 55, y: 125, w: 120, h: 75 },
  { name: '', color: '#ffc107', key: 'fender', done: false, generating: false, x: 355, y: 125, w: 100, h: 75 },
  { name: '', color: '#ff6b6b', key: 'trunk', done: false, generating: false, x: 355, y: 70, w: 100, h: 65 }
])

const completedSurfaceCount = computed(() => surfaceList.filter(s => s.done).length)

const canvasRef = ref(null)
let canvasCtx = null
let animationId = null
let mediaRecorder = null
let recordedChunks = []
let recordingStartTime = null
let demoStartTime = null

// 统计数据
const stats = reactive({
  surfaces: 0,
  qualityScore: null,
  optimizationRate: null,
  handoverFormats: 0
})

// 进度条颜色
const progressColors = [
  { color: '#00d4ff', percentage: 20 },
  { color: '#8b5cf6', percentage: 40 },
  { color: '#00ff88', percentage: 60 },
  { color: '#ffc107', percentage: 80 },
  { color: '#ff6b6b', percentage: 100 }
]

// 场景数据
const scenes = reactive([
  { id: 1, name: '', icon: '⚙️', description: '', totalSteps: 36, progress: 0, status: 'pending', metrics: { time: { label: '', value: t('demo.zeroSeconds') } } },
  { id: 2, name: '', icon: '📦', description: '', totalSteps: 12, progress: 0, status: 'pending', metrics: { params: { label: '', value: '0' } } },
  { id: 3, name: '', icon: '🎨', description: '', totalSteps: 170, progress: 0, status: 'pending', metrics: { surfaces: { label: '', value: '0' } } },
  { id: 4, name: '', icon: '🔍', description: '', totalSteps: 118, progress: 0, status: 'pending', metrics: { score: { label: '', value: '--' } } },
  { id: 5, name: '', icon: '⚡', description: '', totalSteps: 90, progress: 0, status: 'pending', metrics: { opt: { label: '', value: '--' } } },
  { id: 6, name: '', icon: '📤', description: '', totalSteps: 51, progress: 0, status: 'pending', metrics: { formats: { label: '', value: '0' } } }
])

// 日志数据
const logs = ref([])

// 曲面可视化数据
const surfaces = ref([])

// 粒子样式生成
const getParticleStyle = (index) => {
  const colors = ['#00d4ff', '#8b5cf6', '#00ff88', '#ffc107', '#ff6b6b']
  return {
    left: `${Math.random() * 100}%`,
    width: `${Math.random() * 10 + 5}px`,
    height: `${Math.random() * 10 + 5}px`,
    background: colors[Math.floor(Math.random() * colors.length)],
    animationDelay: `${Math.random() * 20}s`,
    animationDuration: `${Math.random() * 20 + 15}s`
  }
}

// 场景状态标签类型
const getSceneTagType = (status) => {
  const types = { pending: 'info', running: 'primary', completed: 'success' }
  return types[status] || 'info'
}

const getSceneStatusText = (status) => {
  const texts = { pending: '', running: '', completed: '' }
  return texts[status] || status
}

const getSceneName = (index) => {
  const names = ['systemInit', 'paramLoading', 'surfaceCreation', 'qualityInspection', 'topologyOptimization', 'dataTransfer']
  return t('demo.' + names[index])
}

const getSceneDescription = (index) => {
  const descs = ['sceneDesc1', 'sceneDesc2', 'sceneDesc3', 'sceneDesc4', 'sceneDesc5', 'sceneDesc6']
  return t('demo.' + descs[index])
}

const getMetricLabel = (sceneIndex, key) => {
  const labels = [
    { time: 'time' },
    { params: 'params' },
    { surfaces: 'surfaces' },
    { score: 'score' },
    { opt: 'opt' },
    { formats: 'formats' }
  ]
  return t('demo.' + labels[sceneIndex][key])
}

const getSurfaceName = (index) => {
  const names = ['hood', 'roof', 'frontWindshield', 'rearWindshield', 'door', 'frontFender', 'rearFender', 'trunk']
  return t('demo.' + names[index])
}

// 进度格式化
const progressFormat = (percentage) => {
  return `${percentage.toFixed(1)}%`
}

// 时间格式化
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 添加日志
const addLog = (message, type = 'info') => {
  const time = new Date().toLocaleTimeString([], { hour12: false })
  logs.value.unshift({ time, message, type })
  if (logs.value.length > 50) logs.value.pop()
}

// 初始化画布
const initCanvas = () => {
  if (!canvasRef.value) return
  canvasCtx = canvasRef.value.getContext('2d')
  canvasRef.value.width = canvasRef.value.offsetWidth
  canvasRef.value.height = canvasRef.value.offsetHeight
  startVisualization()
}

// 可视化动画
const startVisualization = () => {
  const draw = () => {
    if (!canvasCtx) return
    const w = canvasRef.value.width
    const h = canvasRef.value.height

    // 清空画布
    canvasCtx.fillStyle = 'rgba(10, 10, 26, 1)'
    canvasCtx.fillRect(0, 0, w, h)

    // 绘制网格
    canvasCtx.strokeStyle = 'rgba(0, 212, 255, 0.1)'
    canvasCtx.lineWidth = 1
    for (let i = 0; i < 20; i++) {
      canvasCtx.beginPath()
      canvasCtx.moveTo(0, i * h / 20)
      canvasCtx.lineTo(w, i * h / 20)
      canvasCtx.stroke()
      canvasCtx.beginPath()
      canvasCtx.moveTo(i * w / 20, 0)
      canvasCtx.lineTo(i * w / 20, h)
      canvasCtx.stroke()
    }

    // 绘制曲面
    const time = Date.now() / 1000
    surfaces.value.forEach((surface, idx) => {
      const points = surface.points
      const offsetY = idx * 90
      const color = surface.color
      const rowCount = points.length
      const colCount = points[0].length

      // 绘制填充曲面
      for (let i = 0; i < rowCount - 1; i++) {
        for (let j = 0; j < colCount - 1; j++) {
          const x1 = (i / rowCount) * w * 0.8 + w * 0.1
          const y1 = (j / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i) * 10
          const z1 = points[i][j].z || 0

          const x2 = ((i + 1) / rowCount) * w * 0.8 + w * 0.1
          const y2 = (j / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i + 1) * 10
          const z2 = points[i + 1][j].z || 0

          const x3 = ((i + 1) / rowCount) * w * 0.8 + w * 0.1
          const y3 = ((j + 1) / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i + 1) * 10
          const z3 = points[i + 1][j + 1].z || 0

          const x4 = (i / rowCount) * w * 0.8 + w * 0.1
          const y4 = ((j + 1) / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i) * 10
          const z4 = points[i][j + 1].z || 0

          canvasCtx.beginPath()
          canvasCtx.moveTo(x1 + z1, y1)
          canvasCtx.lineTo(x2 + z2, y2)
          canvasCtx.lineTo(x3 + z3, y3)
          canvasCtx.lineTo(x4 + z4, y4)
          canvasCtx.closePath()
          canvasCtx.fillStyle = color.replace(')', ', 0.3)').replace('hsl', 'hsla')
          canvasCtx.fill()
        }
      }

      canvasCtx.strokeStyle = color
      canvasCtx.lineWidth = 2

      // 绘制控制网格线（横向）
      for (let i = 0; i < rowCount; i++) {
        canvasCtx.beginPath()
        for (let j = 0; j < colCount; j++) {
          const x = (i / rowCount) * w * 0.8 + w * 0.1
          const y = (j / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i) * 10
          const z = points[i][j].z || 0

          if (j === 0) canvasCtx.moveTo(x + z, y)
          else canvasCtx.lineTo(x + z, y)
        }
        canvasCtx.stroke()
      }

      // 绘制控制网格线（纵向）
      for (let j = 0; j < colCount; j++) {
        canvasCtx.beginPath()
        for (let i = 0; i < rowCount; i++) {
          const x = (i / rowCount) * w * 0.8 + w * 0.1
          const y = (j / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i) * 10
          const z = points[i][j].z || 0

          if (i === 0) canvasCtx.moveTo(x + z, y)
          else canvasCtx.lineTo(x + z, y)
        }
        canvasCtx.stroke()
      }

      // 绘制控制点
      for (let i = 0; i < rowCount; i++) {
        for (let j = 0; j < colCount; j++) {
          const x = (i / rowCount) * w * 0.8 + w * 0.1
          const y = (j / colCount) * h * 0.4 + offsetY + 60 + Math.sin(time + i) * 10
          const z = points[i][j].z || 0
          
          canvasCtx.beginPath()
          canvasCtx.arc(x + z, y, 4, 0, Math.PI * 2)
          canvasCtx.fillStyle = '#fff'
          canvasCtx.fill()
          canvasCtx.beginPath()
          canvasCtx.arc(x + z, y, 2, 0, Math.PI * 2)
          canvasCtx.fillStyle = color
          canvasCtx.fill()
        }
      }

      // 绘制标签
      canvasCtx.fillStyle = color
      canvasCtx.font = 'bold 14px Arial'
      canvasCtx.fillText(surface.name, 20, offsetY + 35)
    })

    // 绘制标题
    canvasCtx.fillStyle = '#00d4ff'
    canvasCtx.font = 'bold 18px Arial'
    canvasCtx.fillText(t('demo.nurbsVisualizationCanvas'), w / 2 - 120, 30)

    animationId = requestAnimationFrame(draw)
  }
  draw()
}

// 添加曲面
const addSurface = (name) => {
  const points = []
  for (let u = 0; u < 6; u++) {
    const row = []
    for (let v = 0; v < 5; v++) {
      row.push({
        x: u * 20,
        y: v * 20,
        z: Math.sin(u * 0.5) * Math.cos(v * 0.5) * 30
      })
    }
    points.push(row)
  }
  surfaces.value.push({
    name,
    points,
    color: `hsl(${Math.random() * 360}, 70%, 60%)`
  })
}

// 执行场景
const runScene = async (sceneIndex) => {
  const scene = scenes[sceneIndex]
  const stepsPerUpdate = Math.ceil(scene.totalSteps / 40)

  scene.status = 'running'
  currentTask.value = getSceneName(sceneIndex)
  addLog(t('common.start') + ': ' + getSceneName(sceneIndex), 'info')

  const startTime = Date.now()
  let progress = 0

  while (progress < scene.totalSteps && isRunning.value) {
    await new Promise(resolve => setTimeout(resolve, 30))

    progress = Math.min(progress + stepsPerUpdate, scene.totalSteps)
    scene.progress = Math.round((progress / scene.totalSteps) * 100)

    // 更新整体进度
    const totalProgress = scenes.reduce((a, s) => a + s.progress, 0)
    overallProgress.value = totalProgress / scenes.length

    // 更新统计数据
    if (sceneIndex === 2 && progress > 0) {
      stats.surfaces = Math.ceil((progress / scene.totalSteps) * 8)
      scene.metrics.surfaces.value = stats.surfaces.toString()

      // 逐步生成车型曲面
      const surfaceProgress = progress / scene.totalSteps
      if (surfaceProgress >= 0.05 && !carSurfaces.hood) {
        carSurfaces.hood = true
        generatingSurface.value = surfaceList[0]
        surfaceList[0].generating = true
        addLog(t('demo.creatingSurface') + ': ' + t('demo.hood'), 'info')
        await nextTick()
        setTimeout(() => { surfaceList[0].generating = false; surfaceList[0].done = true; generatingSurface.value = null }, 800)
      }
      if (surfaceProgress >= 0.2 && !carSurfaces.roof) {
        carSurfaces.roof = true
        generatingSurface.value = surfaceList[1]
        surfaceList[1].generating = true
        surfaceList[2].generating = true
        surfaceList[3].generating = true
        addLog(t('demo.creatingSurface') + ': ' + t('demo.roof') + ' + ' + t('demo.frontWindshield'), 'info')
        await nextTick()
        setTimeout(() => {
          surfaceList[1].generating = false; surfaceList[1].done = true
          surfaceList[2].generating = false; surfaceList[2].done = true
          surfaceList[3].generating = false; surfaceList[3].done = true
          generatingSurface.value = null
        }, 800)
      }
      if (surfaceProgress >= 0.4 && !carSurfaces.door) {
        carSurfaces.door = true
        generatingSurface.value = surfaceList[4]
        surfaceList[4].generating = true
        addLog(t('demo.creatingSurface') + ': ' + t('demo.door'), 'info')
        await nextTick()
        setTimeout(() => { surfaceList[4].generating = false; surfaceList[4].done = true; generatingSurface.value = null }, 800)
      }
      if (surfaceProgress >= 0.6 && !carSurfaces.fender) {
        carSurfaces.fender = true
        generatingSurface.value = surfaceList[5]
        surfaceList[5].generating = true
        surfaceList[6].generating = true
        addLog(t('demo.creatingSurface') + ': ' + t('demo.frontFender') + ' ' + t('demo.rearFender'), 'info')
        await nextTick()
        setTimeout(() => {
          surfaceList[5].generating = false; surfaceList[5].done = true
          surfaceList[6].generating = false; surfaceList[6].done = true
          generatingSurface.value = null
        }, 800)
      }
      if (surfaceProgress >= 0.85 && !carSurfaces.trunk) {
        carSurfaces.trunk = true
        generatingSurface.value = surfaceList[7]
        surfaceList[7].generating = true
        addLog(t('demo.creatingSurface') + ': ' + t('demo.trunk'), 'info')
        await nextTick()
        setTimeout(() => { surfaceList[7].generating = false; surfaceList[7].done = true; generatingSurface.value = null }, 800)
      }
    }

    if (sceneIndex === 3 && progress > scene.totalSteps * 0.8) {
      stats.qualityScore = Math.round(85 + Math.random() * 14)
      scene.metrics.score.value = stats.qualityScore.toString()
    }

    if (sceneIndex === 4) {
      stats.optimizationRate = `+${Math.round(5 + Math.random() * 15)}%`
      scene.metrics.opt.value = stats.optimizationRate
    }

    if (sceneIndex === 5 && progress > scene.totalSteps * 0.5) {
      stats.handoverFormats = 4
      scene.metrics.formats.value = '4'
    }
  }

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
  scene.status = 'completed'
  scene.progress = 100

  if (sceneIndex === 1) {
    scene.metrics.params.value = '12'
  }
  if (sceneIndex === 3) {
    stats.qualityScore = 95.2
    scene.metrics.score.value = '95.2'
  }
  if (sceneIndex === 4) {
    stats.optimizationRate = '+12%'
    scene.metrics.opt.value = '+12%'
  }
  if (sceneIndex === 5) {
    stats.handoverFormats = 4
    scene.metrics.formats.value = '4'
  }

  addLog(t('common.completed') + ': ' + getSceneName(sceneIndex), 'success')

  // 添加曲面到可视化
  if (sceneIndex === 2) {
    const names = [t('demo.hood'), t('demo.roof'), t('demo.door'), t('demo.sideMirror')]
    for (let i = 0; i < 4; i++) {
      addSurface(names[i])
    }
    visualizationStatus.value = t('demo.realTimeRendering')
  }
}

// 运行演示
const startDemo = async () => {
  if (isRunning.value) return

  isRunning.value = true
  demoStartTime = Date.now()
  surfaces.value = []
  stats.surfaces = 0
  stats.qualityScore = null
  stats.optimizationRate = null
  stats.handoverFormats = 0

  addLog('='.repeat(50), 'info')
  addLog(t('demo.demoStarted'), 'success')

  // 时间更新定时器
  const timeInterval = setInterval(() => {
    if (!isRunning.value) {
      clearInterval(timeInterval)
      return
    }
    const elapsed = (Date.now() - demoStartTime) / 1000
    elapsedTime.value = formatTime(elapsed)

    if (overallProgress.value > 0) {
      const totalEstimate = elapsed / (overallProgress.value / 100)
      const remaining = totalEstimate - elapsed
      remainingTime.value = formatTime(remaining)
    }
  }, 1000)

  for (let i = 0; i < scenes.length; i++) {
    if (!isRunning.value) break
    await runScene(i)
    await new Promise(resolve => setTimeout(resolve, 500))
  }

  clearInterval(timeInterval)
  overallProgress.value = 100
  currentTask.value = t('demo.demoComplete')

  addLog(t('demo.demoFinished'), 'success')
  addLog('='.repeat(50), 'info')

  isRunning.value = false

  if (isRecording.value) {
    setTimeout(() => {
      showCompleteModal.value = true
    }, 1000)
  }
}

// 开始录制
const startRecording = () => {
  if (!canvasRef.value) return

  const stream = canvasRef.value.captureStream(30)
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
  recordedChunks = []

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) recordedChunks.push(e.data)
  }

  mediaRecorder.start()
  isRecording.value = true
  hasRecording.value = false
  recordingStartTime = Date.now()

  const updateRecordingTime = () => {
    if (!isRecording.value) return
    const elapsed = (Date.now() - recordingStartTime) / 1000
    recordingTime.value = formatTime(elapsed)
    setTimeout(updateRecordingTime, 1000)
  }
  updateRecordingTime()

  addLog(t('demo.recordingStarted'), 'info')
}

// 停止录制
const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }

  isRecording.value = false
  hasRecording.value = true

  addLog(t('demo.recordingStopped'), 'info')
}

// 下载视频
const downloadVideo = () => {
  if (recordedChunks.length === 0) return

  const blob = new Blob(recordedChunks, { type: 'video/webm' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `EVOLUTION_AI_DEMO_${new Date().toISOString().slice(0, 10)}.webm`
  a.click()
  URL.revokeObjectURL(url)

  addLog(t('demo.videoDownloaded'), 'success')
}

// 重置
const resetDemo = () => {
  isRunning.value = false
  overallProgress.value = 0
  surfaces.value = []
  stats.surfaces = 0
  stats.qualityScore = null
  stats.optimizationRate = null
  stats.handoverFormats = 0
  elapsedTime.value = '00:00'
  remainingTime.value = '--:--'
  currentTask.value = t('demo.waitingStart')
  visualizationStatus.value = t('demo.waitingData')
  logs.value = []

  carSurfaces.hood = false
  carSurfaces.roof = false
  carSurfaces.door = false
  carSurfaces.fender = false
  carSurfaces.trunk = false
  generatingSurface.value = null
  surfaceList.forEach(s => { s.done = false; s.generating = false })

  scenes.forEach(scene => {
    scene.progress = 0
    scene.status = 'pending'
    Object.keys(scene.metrics).forEach(key => {
      if (key === 'time') scene.metrics[key].value = t('demo.zeroSeconds')
      else if (key === 'params' || key === 'surfaces' || key === 'formats') scene.metrics[key].value = '0'
      else scene.metrics[key].value = '--'
    })
  })

  addLog(t('demo.systemReset'), 'info')
}

onMounted(() => {
  initCanvas()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
})
</script>

<style scoped>
.demo-container {
  padding: 30px;
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0f0f2a 100%);
  position: relative;
  font-size: 16px;
}

.particle-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.particle {
  position: absolute;
  border-radius: 50%;
  animation: float 20s infinite;
  opacity: 0.6;
}

@keyframes float {
  0%, 100% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { transform: translateY(-100vh) rotate(720deg); opacity: 0; }
}

.recording-indicator {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 10px 20px;
  background: rgba(255, 71, 87, 0.9);
  border-radius: 25px;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: recording-blink 1s infinite;
  z-index: 1000;
  color: white;
}

@keyframes recording-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.recording-dot {
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  animation: dot-pulse 1s infinite;
}

@keyframes dot-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

.banner {
  text-align: center;
  padding: 40px 20px;
  margin-bottom: 30px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-radius: 20px;
  border: 1px solid rgba(0, 212, 255, 0.3);
  position: relative;
  overflow: hidden;
}

.banner h1 {
  font-size: 4em;
  font-weight: 900;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 15px;
}

.banner .subtitle {
  font-size: 1.5em;
  color: #8b9dc3;
  margin-top: 15px;
}

.banner .tagline {
  display: inline-block;
  margin-top: 20px;
  padding: 12px 30px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2), rgba(139, 92, 246, 0.2));
  border-radius: 30px;
  font-size: 1.1em;
  color: #00d4ff;
}

.control-panel {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.progress-card {
  margin-bottom: 30px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.progress-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #00d4ff;
}

.progress-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #8b9dc3;
}

.stat-value {
  color: #fff;
  font-weight: 600;
}

.main-progress {
  margin-bottom: 10px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  color: #8b9dc3;
}

.time-estimate {
  color: #00ff88;
}

.stats-panel {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-icon {
  font-size: 3em;
  margin-bottom: 15px;
}

.stat-value {
  font-size: 2.5em;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  color: #8b9dc3;
  font-size: 1.1em;
  margin-top: 8px;
}

.scenes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.scene-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.scene-card.active {
  border-color: #00d4ff;
  box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
}

.scene-card.completed {
  border-color: #00ff88;
}

.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.scene-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.scene-icon {
  font-size: 1.8em;
}

.scene-description {
  color: #8b9dc3;
  font-size: 1em;
  margin-bottom: 18px;
}

.scene-metrics {
  display: flex;
  gap: 20px;
  margin-top: 18px;
  font-size: 0.95em;
}

.metric {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #8b9dc3;
}

.metric-value {
  color: #fff;
  font-weight: 600;
}

.car-model-card {
  margin-bottom: 30px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.car-model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.car-model-title {
  font-size: 1.4em;
  color: #00d4ff;
}

.car-surface-layout {
  display: flex;
  gap: 25px;
  align-items: flex-start;
}

.car-surface-visual {
  flex: 2;
  min-width: 0;
}

.car-surface-svg {
  width: 100%;
  height: auto;
}

.surface-appear {
  animation: surfaceFadeIn 0.6s ease-out;
}

@keyframes surfaceFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.surface-list {
  flex: 1;
  min-width: 200px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.surface-list-title {
  color: #00d4ff;
  font-size: 1.1em;
  font-weight: bold;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.surface-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: 6px;
  font-size: 0.95em;
  color: #8b9dc3;
  transition: all 0.3s ease;
}

.surface-item.active {
  background: rgba(0, 212, 255, 0.15);
  color: #fff;
}

.surface-item.done {
  color: #00ff88;
}

.surface-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.surface-name {
  flex: 1;
}

.surface-status {
  font-size: 1.1em;
}

.surface-summary {
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: #8b9dc3;
  font-size: 0.95em;
  text-align: center;
}

.visualization-card {
  margin-bottom: 30px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.visualization-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.visualization-title {
  font-size: 1.4em;
  color: #00d4ff;
}

.canvas-3d {
  width: 100%;
  min-height: 350px;
  height: 45vh;
  border-radius: 10px;
  background: radial-gradient(ellipse at center, #1a1a3e 0%, #0a0a1a 100%);
}

.log-card {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.log-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #00d4ff;
}

.log-entries {
  max-height: 350px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 1em;
}

.log-entry {
  padding: 8px 12px;
  margin-bottom: 5px;
  border-radius: 5px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.log-entry.info {
  background: rgba(0, 212, 255, 0.1);
  border-left: 3px solid #00d4ff;
}

.log-entry.success {
  background: rgba(0, 255, 136, 0.1);
  border-left: 3px solid #00ff88;
}

.log-time {
  color: #8b9dc3;
  flex-shrink: 0;
}

.log-message {
  color: #fff;
}

.modal-content {
  text-align: center;
}

.modal-content h2 {
  font-size: 2em;
  margin-bottom: 20px;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.modal-stats {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-top: 20px;
}

.modal-stat {
  text-align: center;
}

.modal-stat-label {
  color: #8b9dc3;
}

.modal-stat-value {
  font-size: 1.5em;
  font-weight: 700;
  color: #00d4ff;
}

@media (max-width: 768px) {
  .banner h1 {
    font-size: 2em;
  }

  .scenes-grid {
    grid-template-columns: 1fr;
  }

  .stats-panel {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>