<template>
  <div class="dashboard">
    <div class="hero-section">
      <div class="hero-video-container">
        <video
          v-if="!videoError"
          ref="heroVideo"
          class="hero-video"
          autoplay
          muted
          loop
          playsinline
          poster="/hero-poster.svg"
          @error="handleVideoError"
          @loadeddata="handleVideoLoaded"
        >
          <source src="/demo-animation.mp4" type="video/mp4" />
        </video>
        <div v-else class="hero-video-fallback">
          <div class="fallback-gradient"></div>
          <div class="fallback-particles">
            <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></span>
          </div>
        </div>
        <div class="video-overlay"></div>
      </div>
      <div class="hero-content">
        <div class="hero-badge">{{ t('app.subtitle') }}</div>
        <h1 class="hero-title">{{ t('app.title') }}</h1>
        <p class="hero-subtitle">{{ t('dashboard.heroSubtitle') }}</p>
        <div class="hero-stats">
          <div class="hero-stat">
            <span class="stat-number">22</span>
            <span class="stat-unit">{{ t('dashboard.heroDimensions') }}</span>
          </div>
          <div class="hero-stat">
            <span class="stat-number">19</span>
            <span class="stat-unit">{{ t('dashboard.statModels') }}</span>
          </div>
          <div class="hero-stat">
            <span class="stat-number">5</span>
            <span class="stat-unit">{{ t('dashboard.heroBrands') }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/designer')">
            {{ t('dashboard.startDesigning') }}
          </el-button>
          <el-button size="large" @click="$router.push('/demo')">
            {{ t('dashboard.viewDemo') }}
          </el-button>
        </div>
      </div>
    </div>

    <div class="stats-grid">
      <el-card class="stat-card" v-for="stat in statCards" :key="stat.key">
        <div class="stat-icon" :class="stat.key">
          <el-icon :size="24"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </el-card>
    </div>

    <div class="content-grid">
      <el-card class="content-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">{{ t('dashboard.recentProjects') }}</span>
            <el-button type="primary" text @click="$router.push('/projects')">{{ t('dashboard.viewAll') }}</el-button>
          </div>
        </template>
        <el-table :data="recentProjects" style="width: 100%" :row-style="{ background: 'transparent' }">
          <el-table-column prop="name" :label="t('dashboard.projectName')" />
          <el-table-column prop="status" :label="t('dashboard.status')" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" effect="dark" size="small">{{ getStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" :label="t('dashboard.createdAt')" width="160" />
        </el-table>
      </el-card>

      <el-card class="content-card">
        <template #header>
          <span class="card-title">{{ t('dashboard.workflowStatus') }}</span>
        </template>
        <div class="workflow-list">
          <div class="workflow-item" v-for="item in workflowItems" :key="item.id">
            <div class="workflow-header">
              <span class="workflow-name">{{ item.name }}</span>
              <span class="workflow-percent">{{ item.progress }}%</span>
            </div>
            <el-progress :percentage="item.progress" :stroke-width="8" :show-text="false" :color="'#4ade80'" />
            <div class="workflow-status">
              <span class="status-dot" :class="item.status"></span>
              <span class="status-text">{{ t('dashboard.' + item.statusText) }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { FolderOpened, Picture, CircleCheck, Download } from '@element-plus/icons-vue'

const { t } = useI18n({ useScope: 'global' })

const heroVideo = ref(null)
const videoError = ref(false)
const videoLoaded = ref(false)

const handleVideoError = () => {
  videoError.value = true
}
const handleVideoLoaded = () => {
  videoLoaded.value = true
}

const particleStyle = (i) => {
  const size = 2 + Math.random() * 6
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDelay: `${Math.random() * 4}s`,
    animationDuration: `${4 + Math.random() * 4}s`
  }
}

onMounted(() => {
  if (heroVideo.value) {
    heroVideo.value.play().catch(() => {})
    setTimeout(() => {
      if (!videoLoaded.value) videoError.value = true
    }, 4000)
  }
})

const statCards = computed(() => [
  { key: 'projects', icon: FolderOpened, value: '24', label: t('dashboard.statProjects') },
  { key: 'models', icon: Picture, value: '156', label: t('dashboard.statModels') },
  { key: 'quality', icon: CircleCheck, value: '94.2%', label: t('dashboard.qualityScore') },
  { key: 'exported', icon: Download, value: '89', label: t('dashboard.exportedFiles') }
])

const recentProjects = computed(() => [
  { id: 1, name: t('dashboard.recentProject1'), status: 'Active', createdAt: '2026-07-10' },
  { id: 2, name: t('dashboard.recentProject2'), status: 'Completed', createdAt: '2026-07-08' },
  { id: 3, name: t('dashboard.recentProject3'), status: 'Active', createdAt: '2026-07-05' },
  { id: 4, name: t('dashboard.recentProject4'), status: 'Draft', createdAt: '2026-07-02' },
  { id: 5, name: t('dashboard.recentProject5'), status: 'Completed', createdAt: '2026-06-28' }
])

const workflowItems = computed(() => [
  { id: 1, name: t('dashboard.workflowName1'), progress: 75, status: 'running', statusText: 'inProgress' },
  { id: 2, name: t('dashboard.workflowName2'), progress: 100, status: 'completed', statusText: 'completed' },
  { id: 3, name: t('dashboard.workflowName3'), progress: 45, status: 'running', statusText: 'inProgress' },
  { id: 4, name: t('dashboard.workflowName4'), progress: 0, status: 'pending', statusText: 'pending' }
])

const getStatusType = (status) => {
  const types = { Active: 'success', Completed: 'info', Draft: 'warning' }
  return types[status] || 'info'
}

// 原始状态值（Active/Completed/Draft）→ i18n 文案
const statusLabelMap = { Active: 'inProgress', Completed: 'completed', Draft: 'draft' }
const getStatusLabel = (status) =>
  t(`dashboard.${statusLabelMap[status] || 'draft'}`)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-section {
  position: relative;
  height: 480px;
  border-radius: 12px;
  overflow: hidden;
  margin: -16px;
  margin-bottom: 20px;
}

.hero-video-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.hero-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-video-fallback {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.fallback-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(16, 185, 129, 0.15) 0%,
    rgba(59, 130, 246, 0.12) 25%,
    rgba(139, 92, 246, 0.12) 50%,
    rgba(59, 130, 246, 0.12) 75%,
    rgba(16, 185, 129, 0.15) 100%
  );
  background-size: 400% 400%;
  animation: gradientShift 15s ease infinite;
}

.fallback-particles {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.4);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
  animation: particleFloat 6s ease-in-out infinite;
}

@keyframes gradientShift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

@keyframes particleFloat {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
  50% { transform: translateY(-12px) scale(1.3); opacity: 0.8; }
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.85) 0%, rgba(10, 10, 15, 0.6) 50%, rgba(10, 10, 15, 0.85) 100%);
}

.hero-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  text-align: center;
}

.hero-badge {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 6px 16px;
  border-radius: 20px;
  margin-bottom: 16px;
}

.hero-title {
  font-size: 48px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-muted);
  margin: 12px 0 24px;
  max-width: 600px;
}

.hero-stats {
  display: flex;
  gap: 48px;
  margin-bottom: 32px;
}

.hero-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--accent);
}

.stat-unit {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.hero-actions {
  display: flex;
  gap: 16px;
}

.hero-actions :deep(.el-button) {
  border-radius: 8px;
  font-weight: 600;
}

.hero-actions :deep(.el-button--primary) {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
}

.hero-actions :deep(.el-button--primary:hover) {
  background: var(--accent);
  border-color: var(--accent);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon.projects {
  background: var(--accent-bg);
  color: var(--accent);
}

.stat-icon.models {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.stat-icon.quality {
  background: rgba(250, 204, 21, 0.15);
  color: #facc15;
}

.stat-icon.exported {
  background: rgba(244, 114, 182, 0.15);
  color: #f472b6;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.content-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.content-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 20px;
}

.content-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.content-card :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: var(--hover-bg);
  background: transparent;
  color: var(--text-secondary);
}

.content-card :deep(.el-table th) {
  background: transparent;
  color: var(--text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border-color);
}

.content-card :deep(.el-table td) {
  border-bottom: 1px solid var(--border-color);
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workflow-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.workflow-percent {
  font-size: 13px;
  color: var(--text-muted);
}

.workflow-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.running {
  background: var(--accent);
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
}

.status-dot.completed {
  background: #60a5fa;
}

.status-dot.pending {
  background: var(--text-faint);
}

.status-text {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
