<template>
  <div class="demo-container">
    <!-- 粒子背景 -->
    <div class="particle-container">
      <div v-for="i in 50" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>

    <!-- 录制指示器 -->
    <div class="recording-indicator" v-if="isRecording">
      <div class="recording-dot"></div>
      <span>录制中 {{ recordingTime }}</span>
    </div>

    <!-- 横幅 -->
    <div class="banner">
      <h1>⚡ EVOLUTION AI</h1>
      <p class="subtitle">汽车A级曲面智能开发平台</p>
      <div class="tagline">◈ NURBS曲面 ◈ 拓扑优化 ◈ 质量检测 ◈ 工程交接 ◈</div>
    </div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <el-button type="primary" size="large" @click="startDemo" :disabled="isRunning">
        <el-icon><VideoPlay /></el-icon>
        开始演示
      </el-button>
      <el-button type="success" size="large" @click="startRecording" v-if="!isRecording">
        <el-icon><VideoCamera /></el-icon>
        录制视频
      </el-button>
      <el-button type="danger" size="large" @click="stopRecording" v-else>
        <el-icon><VideoPause /></el-icon>
        停止录制
      </el-button>
      <el-button size="large" @click="resetDemo">
        <el-icon><RefreshRight /></el-icon>
        重置
      </el-button>
      <el-button type="warning" size="large" @click="downloadVideo" v-if="hasRecording">
        <el-icon><Download /></el-icon>
        下载视频
      </el-button>
    </div>

    <!-- 主进度条 -->
    <el-card class="progress-card">
      <div class="progress-header">
        <div class="progress-title">
          <el-icon><DataLine /></el-icon>
          <span>整体进度</span>
        </div>
        <div class="progress-stats">
          <div class="stat-item">
            <el-icon><Timer /></el-icon>
            <span>已用时:</span>
            <span class="stat-value">{{ elapsedTime }}</span>
          </div>
          <div class="stat-item">
            <el-icon><Clock /></el-icon>
            <span>预计剩余:</span>
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
        <span class="time-estimate">{{ etaEstimate }}</span>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <div class="stats-panel">
      <el-card class="stat-card">
        <div class="stat-icon">🎨</div>
        <div class="stat-value">{{ stats.surfaces }}</div>
        <div class="stat-label">已创建曲面</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{{ stats.qualityScore || '--' }}</div>
        <div class="stat-label">质量评分</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">{{ stats.optimizationRate || '--' }}</div>
        <div class="stat-label">优化提升</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon">📤</div>
        <div class="stat-value">{{ stats.handoverFormats }}</div>
        <div class="stat-label">交接格式</div>
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
            <span>{{ scene.name }}</span>
          </div>
          <el-tag :type="getSceneTagType(scene.status)" effect="dark">
            {{ getSceneStatusText(scene.status) }}
          </el-tag>
        </div>
        <p class="scene-description">{{ scene.description }}</p>
        <el-progress
          :percentage="scene.progress"
          :stroke-width="8"
          :show-text="false"
          :color="scene.status === 'completed' ? '#00ff88' : '#00d4ff'"
        />
        <div class="scene-metrics">
          <div class="metric" v-for="(metric, key) in scene.metrics" :key="key">
            <span>{{ metric.label }}:</span>
            <span class="metric-value">{{ metric.value }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 可视化区域 -->
    <el-card class="visualization-card">
      <div class="visualization-header">
        <span class="visualization-title">🎬 实时可视化</span>
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
          <span>操作日志</span>
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
    <el-dialog v-model="showCompleteModal" title="演示完成" width="500px" center>
      <div class="modal-content">
        <h2>🎉 DEMO 演示完成!</h2>
        <p>EVOLUTION AI - 汽车A级曲面开发平台</p>
        <div class="modal-stats">
          <div class="modal-stat">
            <span class="modal-stat-label">曲面创建</span>
            <span class="modal-stat-value">{{ stats.surfaces }} 个</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">质量评分</span>
            <span class="modal-stat-value">{{ stats.qualityScore }} 分</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">优化提升</span>
            <span class="modal-stat-value">{{ stats.optimizationRate }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showCompleteModal = false">关闭</el-button>
        <el-button type="success" @click="downloadVideo" v-if="hasRecording">下载视频</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  VideoPlay, VideoCamera, VideoPause, RefreshRight, Download,
  DataLine, Timer, Clock, Document
} from '@element-plus/icons-vue'

// 状态
const isRunning = ref(false)
const isRecording = ref(false)
const hasRecording = ref(false)
const recordingTime = ref('00:00')
const elapsedTime = ref('00:00')
const remainingTime = ref('--:--')
const overallProgress = ref(0)
const currentTask = ref('等待开始...')
const etaEstimate = ref('')
const visualizationStatus = ref('等待数据...')
const showCompleteModal = ref(false)

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
  { id: 1, name: '系统初始化', icon: '⚙️', description: '加载模块、初始化数据库、配置参数库', totalSteps: 36, progress: 0, status: 'pending', metrics: { time: { label: '耗时', value: '0秒' } } },
  { id: 2, name: '参数加载', icon: '📦', description: '加载汽车参数库，包含整车尺寸、底盘参数等', totalSteps: 12, progress: 0, status: 'pending', metrics: { params: { label: '参数', value: '0' } } },
  { id: 3, name: '曲面创建', icon: '🎨', description: '创建NURBS曲面：发动机盖、车顶、车门等', totalSteps: 170, progress: 0, status: 'pending', metrics: { surfaces: { label: '曲面', value: '0' } } },
  { id: 4, name: '质量检测', icon: '🔍', description: 'A级曲面质量检测：连续性、斑马纹、曲率分析', totalSteps: 118, progress: 0, status: 'pending', metrics: { score: { label: '评分', value: '--' } } },
  { id: 5, name: '拓扑优化', icon: '⚡', description: '网格简化、光顺处理、特征保持优化', totalSteps: 90, progress: 0, status: 'pending', metrics: { opt: { label: '提升', value: '--' } } },
  { id: 6, name: '数据交接', icon: '📤', description: 'IGES/STEP/JT格式转换、精度验证、文档生成', totalSteps: 51, progress: 0, status: 'pending', metrics: { formats: { label: '格式', value: '0' } } }
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
  const texts = { pending: '待执行', running: '执行中', completed: '已完成' }
  return texts[status] || status
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
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
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
      const offsetY = idx * 80
      const color = surface.color

      canvasCtx.strokeStyle = color
      canvasCtx.lineWidth = 2

      // 绘制控制网格
      for (let i = 0; i < points.length; i++) {
        canvasCtx.beginPath()
        for (let j = 0; j < points[i].length; j++) {
          const x = (i / points.length) * w * 0.8 + w * 0.1
          const y = (j / points[i].length) * h * 0.4 + offsetY + 50 + Math.sin(time + i) * 10
          const z = points[i][j].z || 0

          if (j === 0) canvasCtx.moveTo(x + z, y)
          else canvasCtx.lineTo(x + z, y)
        }
        canvasCtx.stroke()
      }

      // 绘制标签
      canvasCtx.fillStyle = color
      canvasCtx.font = '12px Arial'
      canvasCtx.fillText(surface.name, 10, offsetY + 30)
    })

    // 绘制标题
    canvasCtx.fillStyle = '#00d4ff'
    canvasCtx.font = 'bold 16px Arial'
    canvasCtx.fillText('◈ NURBS 曲面实时可视化', w / 2 - 100, 25)

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
  currentTask.value = scene.name
  addLog(`开始执行: ${scene.name}`, 'info')

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
      stats.surfaces = Math.ceil((progress / scene.totalSteps) * 4)
      scene.metrics.surfaces.value = stats.surfaces.toString()
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

  addLog(`完成: ${scene.name}`, 'success')

  // 添加曲面到可视化
  if (sceneIndex === 2) {
    const names = ['发动机盖', '车顶', '车门', '后视镜']
    for (let i = 0; i < 4; i++) {
      addSurface(names[i])
    }
    visualizationStatus.value = '实时渲染中...'
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
  addLog('EVOLUTION AI DEMO 演示开始', 'success')

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
  currentTask.value = '演示完成'

  addLog('EVOLUTION AI DEMO 演示完成!', 'success')
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

  addLog('视频录制已开始', 'info')
}

// 停止录制
const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }

  isRecording.value = false
  hasRecording.value = true

  addLog('视频录制已停止', 'info')
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

  addLog('视频已下载', 'success')
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
  currentTask.value = '等待开始...'
  visualizationStatus.value = '等待数据...'
  logs.value = []

  scenes.forEach(scene => {
    scene.progress = 0
    scene.status = 'pending'
    Object.keys(scene.metrics).forEach(key => {
      if (key === 'time') scene.metrics[key].value = '0秒'
      else if (key === 'params' || key === 'surfaces' || key === 'formats') scene.metrics[key].value = '0'
      else scene.metrics[key].value = '--'
    })
  })

  addLog('系统已重置', 'info')
}

onMounted(() => {
  initCanvas()
  addLog('EVOLUTION AI 系统已就绪', 'info')
  addLog('点击"开始演示"启动自动化演示', 'info')
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop()
})
</script>

<style scoped>
.demo-container {
  padding: 20px;
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0f0f2a 100%);
  position: relative;
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
  font-size: 3em;
  font-weight: 900;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 10px;
}

.banner .subtitle {
  font-size: 1.2em;
  color: #8b9dc3;
  margin-top: 10px;
}

.banner .tagline {
  display: inline-block;
  margin-top: 15px;
  padding: 8px 20px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2), rgba(139, 92, 246, 0.2));
  border-radius: 20px;
  font-size: 0.9em;
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
  font-size: 2.5em;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 2em;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  color: #8b9dc3;
  font-size: 0.9em;
  margin-top: 5px;
}

.scenes-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  font-size: 1.5em;
}

.scene-description {
  color: #8b9dc3;
  font-size: 0.9em;
  margin-bottom: 15px;
}

.scene-metrics {
  display: flex;
  gap: 15px;
  margin-top: 15px;
  font-size: 0.85em;
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
  font-size: 1.2em;
  color: #00d4ff;
}

.canvas-3d {
  width: 100%;
  height: 350px;
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
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9em;
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