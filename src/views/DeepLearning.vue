<template>
  <div class="deep-learning-page">
    <div class="page-hero">
      <h1 class="hero-title">Deep Learning Designer</h1>
      <p class="hero-subtitle">AI-powered design tools that transform your creative workflow</p>
    </div>

    <div class="features-grid">
      <el-card class="feature-card" v-for="feature in features" :key="feature.id">
        <div class="feature-icon" :class="feature.key">
          <el-icon :size="32"><component :is="feature.icon" /></el-icon>
        </div>
        <h3 class="feature-title">{{ feature.title }}</h3>
        <p class="feature-desc">{{ feature.description }}</p>
        <el-button type="primary" class="feature-btn" @click="startFeature(feature.key)">
          <span>Start</span>
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { Brush, MagicStick, MoonNight, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const features = [
  {
    id: 1,
    key: 'style-transfer',
    icon: Brush,
    title: 'Style Transfer',
    description: 'Apply artistic styles and design languages to your 3D models. Transform concepts with AI-powered style migration.'
  },
  {
    id: 2,
    key: 'sketch-to-3d',
    icon: MagicStick,
    title: 'Sketch to 3D',
    description: 'Convert 2D sketches and drawings into detailed 3D surface models. Bring your ideas to life instantly.'
  },
  {
    id: 3,
    key: 'dream-design',
    icon: Sunny,
    title: 'Dream Design',
    description: 'Generate innovative design variations using dream-based AI exploration. Discover unexpected creative directions.'
  }
]

const startFeature = (key) => {
  ElMessage.info(`Starting ${key.replace(/-/g, ' ')}...`)
}
</script>

<style scoped>
.deep-learning-page {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 20px 0;
}

.page-hero {
  text-align: center;
  padding: 40px 20px;
}

.hero-title {
  margin: 0 0 12px 0;
  font-size: 36px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  margin: 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.6);
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.6;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.feature-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  transform: translateY(-4px);
}

.feature-card :deep(.el-card__body) {
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
}

.feature-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.feature-icon.style-transfer {
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.2), rgba(74, 222, 128, 0.05));
  color: #4ade80;
}

.feature-icon.sketch-to-3d {
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.2), rgba(96, 165, 250, 0.05));
  color: #60a5fa;
}

.feature-icon.dream-design {
  background: linear-gradient(135deg, rgba(192, 132, 252, 0.2), rgba(192, 132, 252, 0.05));
  color: #c084fc;
}

.feature-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.feature-desc {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.6;
  flex: 1;
}

.feature-btn {
  background: #4ade80;
  border-color: #4ade80;
  color: #0a0a0f;
  font-weight: 600;
  margin-top: 8px;
}

.feature-btn:hover {
  background: #22c55e;
  border-color: #22c55e;
  color: #0a0a0f;
}
</style>
