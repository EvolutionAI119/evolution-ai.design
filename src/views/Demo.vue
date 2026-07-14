<template>
  <div class="demo-page">
    <div class="demo-hero">
      <h1 class="hero-title">Experience the Future of Design</h1>
      <p class="hero-subtitle">Interactive demos showcasing the full power of Evolution AI's design automation platform</p>
    </div>

    <div class="demo-scenes">
      <div class="scene-card" v-for="scene in scenes" :key="scene.id">
        <div class="scene-thumbnail" :class="scene.key">
          <div class="scene-overlay"></div>
          <div class="scene-icon">
            <el-icon :size="48"><component :is="scene.icon" /></el-icon>
          </div>
        </div>
        <div class="scene-content">
          <h3 class="scene-title">{{ scene.title }}</h3>
          <p class="scene-desc">{{ scene.description }}</p>
          <div class="scene-meta">
            <span class="meta-tag">{{ scene.duration }}</span>
            <span class="meta-tag">{{ scene.complexity }}</span>
          </div>
          <el-button type="primary" class="scene-btn" @click="startDemo(scene.key)">
            <el-icon><VideoPlay /></el-icon>
            <span>Start Demo</span>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { MagicStick, Star, Cpu, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const scenes = [
  {
    id: 1,
    key: 'concept',
    icon: MagicStick,
    title: 'Concept Exploration',
    description: 'Watch AI generate and explore hundreds of design concepts from a single sketch in minutes.',
    duration: '~3 min',
    complexity: 'Beginner'
  },
  {
    id: 2,
    key: 'a-class',
    icon: Star,
    title: 'A-Class Surface',
    description: 'See how AI creates production-ready Class A surfaces with perfect curvature continuity.',
    duration: '~5 min',
    complexity: 'Advanced'
  },
  {
    id: 3,
    key: 'full-workflow',
    icon: Cpu,
    title: 'Full Workflow',
    description: 'Experience the complete design pipeline from concept to quality check to data delivery.',
    duration: '~8 min',
    complexity: 'Expert'
  }
]

const startDemo = (key) => {
  ElMessage.success(`Starting ${key} demo...`)
}
</script>

<style scoped>
.demo-page {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 20px 0;
}

.demo-hero {
  text-align: center;
  padding: 60px 20px 40px;
  background: linear-gradient(180deg, rgba(74, 222, 128, 0.08) 0%, transparent 100%);
  border-radius: 12px;
}

.hero-title {
  margin: 0 0 16px 0;
  font-size: 42px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.hero-subtitle {
  margin: 0;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.6);
  max-width: 600px;
  margin: 0 auto;
  line-height: 1.6;
}

.demo-scenes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.scene-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.scene-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

.scene-thumbnail {
  position: relative;
  height: 200px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scene-thumbnail.concept {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.scene-thumbnail.a-class {
  background: linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 50%, #4a1942 100%);
}

.scene-thumbnail.full-workflow {
  background: linear-gradient(135deg, #0a1628 0%, #0d2818 50%, #1a3d2e 100%);
}

.scene-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 30% 40%, rgba(74, 222, 128, 0.15) 0%, transparent 50%);
}

.scene-icon {
  position: relative;
  z-index: 1;
  color: #4ade80;
  opacity: 0.9;
  filter: drop-shadow(0 0 20px rgba(74, 222, 128, 0.5));
}

.scene-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scene-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.scene-desc {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
  line-height: 1.6;
  flex: 1;
}

.scene-meta {
  display: flex;
  gap: 8px;
}

.meta-tag {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.scene-btn {
  width: 100%;
  background: #4ade80;
  border-color: #4ade80;
  color: #0a0a0f;
  font-weight: 600;
  margin-top: 8px;
}

.scene-btn:hover {
  background: #22c55e;
  border-color: #22c55e;
  color: #0a0a0f;
}
</style>
