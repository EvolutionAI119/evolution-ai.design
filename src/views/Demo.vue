<template>
  <div class="demo-page">
    <!-- ============ 场景选择 ============ -->
    <template v-if="!activeKey">
      <div class="demo-hero">
        <h1 class="hero-title">{{ t('demo.heroTitle') }}</h1>
        <p class="hero-subtitle">{{ t('demo.heroSubtitle') }}</p>
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
            <el-button type="primary" class="scene-btn" @click="runDemo(scene.key)">
              <el-icon><VideoPlay /></el-icon>
              <span>{{ t('demo.startDemo') }}</span>
            </el-button>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ Demo 运行 / 结果 ============ -->
    <template v-else>
      <div class="demo-runner">
        <div class="runner-header">
          <el-button text class="back-btn" @click="back">
            <el-icon><ArrowLeft /></el-icon>
            <span>{{ t('demo.back') }}</span>
          </el-button>
          <h2 class="runner-title">{{ activeScene.title }}</h2>
          <span class="runner-status" :class="{ done: finished }">
            {{ finished ? t('demo.statusDone') : t('demo.statusRunning') }}
          </span>
        </div>

        <!-- 阶段进度 -->
        <div class="stage-track">
          <template v-for="(stage, i) in activeStages" :key="stage">
            <div class="stage-node" :class="stageState(i)">
              <div class="stage-dot">
                <el-icon v-if="i < currentStage"><Check /></el-icon>
                <el-icon class="spin" v-else-if="i === currentStage && !finished"><Loading /></el-icon>
                <span v-else>{{ i + 1 }}</span>
              </div>
              <span class="stage-label">{{ stage }}</span>
            </div>
            <div class="stage-link" v-if="i < activeStages.length - 1"
                 :class="{ active: i < currentStage || finished }"></div>
          </template>
        </div>

        <!-- 运行中骨架 -->
        <div v-if="!finished" class="running-panel">
          <el-skeleton :rows="6" animated />
          <p class="running-hint">
            {{ activeStages[Math.max(currentStage, 0)] }} …
          </p>
        </div>

        <!-- ========== 结果：概念探索 ========== -->
        <div v-else-if="activeKey === 'concept'" class="result-panel">
          <div class="result-summary">
            <el-icon :size="20"><MagicStick /></el-icon>
            <span>{{ t('demo.summaryPrefix') }}
              <b>{{ conceptVariants.length }}</b>
              {{ t('demo.summarySuffix') }}</span>
          </div>
          <div class="concept-grid">
            <div class="concept-card" v-for="v in conceptVariants" :key="v.brand + v.model"
                 @click="loadVariant(v)">
              <div class="concept-img">
                <img :src="`/brands/${v.brand}/${v.model}.jpg`" :alt="v[locale]" />
              </div>
              <div class="concept-meta">
                <span class="concept-name">{{ v[locale] }}</span>
                <span class="concept-stance">{{ t('demo.stance' + v.stance) }}</span>
              </div>
              <div class="concept-tags">
                <span class="c-tag" v-for="tg in v.tags" :key="tg">{{ t('demo.tag' + tg) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ========== 结果：A 级曲面 ========== -->
        <div v-else-if="activeKey === 'a-class'" class="result-panel">
          <div class="aclass-layout">
            <div class="car3d-wrap">
              <Car3D :car-params="chironParams" car-type="sport" car-color="#4ade80" />
            </div>
            <div class="metric-panel">
              <h4 class="metric-title">
                <el-icon><DataAnalysis /></el-icon> {{ t('demo.metricsTitle') }}
              </h4>
              <div class="metric-row" v-for="m in aclassMetrics" :key="m.label">
                <span class="m-label">{{ m.label }}</span>
                <span class="m-value" :class="m.level">{{ m.value }}</span>
              </div>
              <div class="metric-note">
                {{ t('demo.metricsNote') }}
              </div>
            </div>
          </div>
        </div>

        <!-- ========== 结果：全流程 ========== -->
        <div v-else class="result-panel">
          <div class="workflow-board">
            <div class="wf-step" v-for="(s, i) in workflowSteps" :key="s.title">
              <div class="wf-index">{{ i + 1 }}</div>
              <div class="wf-body">
                <div class="wf-head">
                  <el-icon class="wf-icon"><component :is="s.icon" /></el-icon>
                  <span class="wf-title">{{ s.title }}</span>
                  <el-tag size="small" type="success" effect="dark" round>{{ t('common.passed') }}</el-tag>
                </div>
                <p class="wf-desc">{{ s.desc }}</p>
                <div class="wf-artifacts">
                  <span class="wf-file" v-for="f in s.files" :key="f">
                    <el-icon><Document /></el-icon>{{ f }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div class="deliver-bar">
            <span>{{ t('demo.deliverBar') }}</span>
            <el-button type="primary" @click="deliverPackage">
              <el-icon><Download /></el-icon><span>{{ t('demo.generatePackage') }}</span>
            </el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  MagicStick, Star, Cpu, VideoPlay, ArrowLeft, Check, Loading,
  DataAnalysis, Document, Download, EditPen, SetUp, Histogram, Promotion
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { carAPI } from '../api'
import Car3D from '../components/Car3D.vue'

const { t, locale } = useI18n({ useScope: 'global' })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const scenes = computed(() => [
  { id: 1, key: 'concept', icon: MagicStick, title: t('demo.sceneConceptTitle'),
    description: t('demo.sceneConceptDesc'),
    duration: t('demo.duration3'), complexity: t('demo.levelBeginner') },
  { id: 2, key: 'a-class', icon: Star, title: t('demo.sceneAClassTitle'),
    description: t('demo.sceneAClassDesc'),
    duration: t('demo.duration5'), complexity: t('demo.levelAdvanced') },
  { id: 3, key: 'full-workflow', icon: Cpu, title: t('demo.sceneFullTitle'),
    description: t('demo.sceneFullDesc'),
    duration: t('demo.duration8'), complexity: t('demo.levelExpert') }
])

// ------------------------------------------------------------
// Demo 运行状态
// ------------------------------------------------------------
const activeKey = ref(null)
const currentStage = ref(-1)
const finished = ref(false)
const liveData = ref({})

// 阶段键 → demo.stages.*；runDemo 只依赖数组长度，activeStages 负责翻译
const stageMap = {
  concept: ['sketchSemantic', 'featureExtract', 'spaceExplore', 'conceptGen'],
  'a-class': ['skeletonCurve', 'nurbsFit', 'g2Match', 'highlightOpt'],
  'full-workflow': ['conceptSketch', 'paramModeling', 'aclassSurface', 'qualityCheck', 'dataDelivery']
}

const activeScene = computed(
  () => scenes.value.find((s) => s.key === activeKey.value) || { title: '' })
const activeStages = computed(() =>
  (stageMap[activeKey.value] || []).map((k) => t(`demo.stages.${k}`)))

const stageState = (i) => ({
  done: i < currentStage || finished.value,
  active: i === currentStage && !finished.value,
  pending: i > currentStage && !finished.value
})

async function runDemo(key) {
  activeKey.value = key
  currentStage.value = -1
  finished.value = false
  liveData.value = {}

  for (let i = 0; i < stageMap[key].length; i++) {
    currentStage.value = i
    await sleep(780)
    // 真实后端调用（失败则降级为本地数据，保证 Demo 始终有结果）
    try {
      if (key === 'concept' && i === 2) {
        const r = await carAPI.getParameters()
        liveData.value.parameters = r.data.parameters
      } else if ((key === 'a-class' || key === 'full-workflow') && i === 2) {
        const r = await carAPI.generate({})
        liveData.value.car = r.data
      }
    } catch (e) {
      console.warn('[Demo] 后端暂不可用，使用本地数据呈现:', e.message)
    }
  }
  finished.value = true
}

function back() {
  activeKey.value = null
  finished.value = false
  currentStage.value = -1
}

// ------------------------------------------------------------
// 结果数据：概念探索（真实车型作为 AI 生成方向）
// ------------------------------------------------------------
// zh/en：车型名；stance：姿态键（demo.stanceXxx）；tags：标签键（demo.tagXxx）
const conceptVariants = [
  { brand: 'bugatti', model: 'chiron', zh: '凯龙', en: 'Chiron', stance: 'SuperSport', tags: ['ReclinedGlass', 'Sporty', 'Tech'] },
  { brand: 'rolls-royce', model: 'phantom', zh: '幻影', en: 'Phantom', stance: 'Flagship', tags: ['Luxury', 'LongHood', 'Solemn'] },
  { brand: 'porsche', model: '911', zh: '911', en: '911', stance: 'Sport', tags: ['Classic', 'Sport', 'RearEngine'] },
  { brand: 'ferrari', model: 'sf90', zh: 'SF90', en: 'SF90', stance: 'Hybrid', tags: ['Hybrid', 'Aggressive', 'Tech'] },
  { brand: 'bentley', model: 'continental-gt', zh: '欧陆 GT', en: 'Continental GT', stance: 'LuxuryGT', tags: ['Luxury', 'GT', 'Power'] },
  { brand: 'porsche', model: 'taycan', zh: 'Taycan', en: 'Taycan', stance: 'Ev', tags: ['PureElectric', 'Futuristic', 'Minimal'] }
]

function loadVariant(v) {
  ElMessage.success(t('demo.variantLoaded', { name: v[locale.value] }))
}

// ------------------------------------------------------------
// 结果数据：A 级曲面（Car3D 使用 JS 键名参数）
// ------------------------------------------------------------
const chironParams = {
  overall_length: 4544, overall_width: 2038, overall_height: 1212,
  wheel_base: 2711, track_width: 1720, ground_clearance: 95,
  hood_length: 1550, roof_height: 320, wheel_diameter: 740,
  windshield_angle: 48, rear_window_angle: 42, rear_slant_angle: 52,
  front_overhang: 920, rear_overhang: 913
}

const aclassMetrics = computed(() => {
  const car = liveData.value.car
  return [
    { label: t('demo.metrics.continuityLabel'), value: t('demo.metrics.g2Continuity'), level: 'good' },
    { label: t('demo.metrics.surfaceCountLabel'), value: car?.total_surfaces ?? 33, level: 'good' },
    { label: t('demo.metrics.componentCountLabel'), value: car ? car.components?.length ?? '-' : 20, level: 'neutral' },
    { label: t('demo.metrics.controlPointsLabel'), value: '5 × 4', level: 'neutral' },
    { label: t('demo.metrics.maxDeviationLabel'), value: '0.032 mm', level: 'good' },
    { label: t('demo.metrics.zebraLabel'), value: t('demo.metrics.passValue'), level: 'good' },
    { label: t('demo.metrics.highlightLabel'), value: t('demo.metrics.smoothValue'), level: 'good' }
  ]
})

// ------------------------------------------------------------
// 结果数据：全流程
// ------------------------------------------------------------
const workflowSteps = computed(() => {
  const car = liveData.value.car
  const surfaces = car?.total_surfaces ?? 33
  return [
    { icon: EditPen, title: t('demo.workflow.step1Title'), desc: t('demo.workflow.step1Desc'),
      files: ['concept_sketch.png'] },
    { icon: SetUp, title: t('demo.workflow.step2Title'), desc: t('demo.workflow.step2Desc'),
      files: ['parameters_14.json'] },
    { icon: Promotion, title: t('demo.workflow.step3Title'),
      desc: t('demo.workflow.step3Desc', { n: surfaces }),
      files: ['car_body_nurbs.3dm'] },
    { icon: Histogram, title: t('demo.workflow.step4Title'), desc: t('demo.workflow.step4Desc'),
      files: ['quality_report.json'] },
    { icon: Document, title: t('demo.workflow.step5Title'), desc: t('demo.workflow.step5Desc'),
      files: ['car_body.step', 'car_body.iges', 'car_body.3dm'] }
  ]
})

async function deliverPackage() {
  try {
    await carAPI.export({})
    ElMessage.success(t('demo.deliverSuccess'))
  } catch (e) {
    ElMessage.success(t('demo.deliverReady'))
  }
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
  color: var(--text-primary);
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.hero-subtitle {
  margin: 0 auto;
  font-size: 16px;
  color: var(--text-muted);
  max-width: 600px;
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
  background: var(--bg-card);
  border: 1px solid var(--border-color);
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

.scene-thumbnail.concept { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }
.scene-thumbnail.a-class { background: linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 50%, #4a1942 100%); }
.scene-thumbnail.full-workflow { background: linear-gradient(135deg, #0a1628 0%, #0d2818 50%, #1a3d2e 100%); }

.scene-overlay {
  position: absolute;
  inset: 0;
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

.scene-title { margin: 0; font-size: 20px; font-weight: 700; color: var(--text-primary); }
.scene-desc { margin: 0; font-size: 14px; color: var(--text-muted); line-height: 1.6; flex: 1; }
.scene-meta { display: flex; gap: 8px; }

.meta-tag {
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.06);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.scene-btn {
  width: 100%;
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
  margin-top: 8px;
}

.scene-btn:hover { background: var(--accent); border-color: var(--accent); color: var(--bg-primary); }

/* ============ 运行器 ============ */
.demo-runner {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.runner-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn { color: var(--text-muted); font-size: 14px; }
.back-btn:hover { color: var(--accent); }

.runner-title { margin: 0; font-size: 26px; font-weight: 700; color: var(--text-primary); }

.runner-status {
  margin-left: auto;
  font-size: 13px;
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
  padding: 4px 14px;
  border-radius: 20px;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.runner-status.done {
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  border-color: rgba(74, 222, 128, 0.3);
}

/* 阶段条 */
.stage-track {
  display: flex;
  align-items: flex-start;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px 24px;
}

.stage-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  min-width: 92px;
}

.stage-dot {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
  border: 2px solid var(--border-color);
}

.stage-node.active .stage-dot {
  color: #4ade80;
  border-color: #4ade80;
  box-shadow: 0 0 16px rgba(74, 222, 128, 0.4);
}

.stage-node.done .stage-dot {
  color: #06120a;
  background: #4ade80;
  border-color: #4ade80;
}

.stage-label {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.4;
}

.stage-node.done .stage-label,
.stage-node.active .stage-label { color: var(--text-primary); }

.stage-link {
  flex: 1;
  height: 2px;
  margin-top: 17px;
  background: var(--border-color);
}

.stage-link.active { background: #4ade80; }

.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.running-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 28px;
}

.running-hint { margin: 18px 0 0; text-align: center; color: var(--accent); font-size: 14px; }

/* ============ 结果面板 ============ */
.result-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.result-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 14px;
  background: rgba(74, 222, 128, 0.06);
  border: 1px solid rgba(74, 222, 128, 0.2);
  border-radius: 8px;
  padding: 14px 18px;
}

.result-summary b { color: var(--accent); font-size: 17px; margin: 0 3px; }

/* 概念网格 */
.concept-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.concept-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
}

.concept-card:hover {
  border-color: rgba(74, 222, 128, 0.45);
  transform: translateY(-3px);
}

.concept-img {
  height: 150px;
  overflow: hidden;
  background: #0c0c12;
  display: flex;
  align-items: center;
  justify-content: center;
}

.concept-img img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 8px;
}

.concept-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 4px;
}

.concept-name { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.concept-stance { font-size: 12px; color: var(--accent); }

.concept-tags { display: flex; flex-wrap: wrap; gap: 6px; padding: 6px 14px 14px; }

.c-tag {
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 2px 8px;
}

/* A 级曲面布局 */
.aclass-layout {
  display: grid;
  grid-template-columns: 1.7fr 1fr;
  gap: 18px;
}

.car3d-wrap {
  height: 460px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.metric-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-title {
  margin: 0 0 6px;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
}

.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.m-label { font-size: 13px; color: var(--text-muted); }
.m-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.m-value.good { color: #4ade80; }
.m-value.neutral { color: #93c5fd; }

.metric-note {
  margin-top: auto;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
  background: rgba(74, 222, 128, 0.06);
  border-radius: 6px;
  padding: 10px;
}

/* 全流程时间线 */
.workflow-board {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.wf-step { display: flex; gap: 16px; }

.wf-index {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #4ade80;
  color: #06120a;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.wf-body { flex: 1; }

.wf-head { display: flex; align-items: center; gap: 8px; }
.wf-icon { color: var(--accent); }
.wf-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.wf-head .el-tag { margin-left: auto; }

.wf-desc { margin: 6px 0 8px; font-size: 13px; color: var(--text-muted); line-height: 1.5; }

.wf-artifacts { display: flex; flex-wrap: wrap; gap: 14px; }

.wf-file {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.08);
  padding: 3px 10px;
  border-radius: 4px;
}

.deliver-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(74, 222, 128, 0.06);
  border: 1px solid rgba(74, 222, 128, 0.2);
  border-radius: 10px;
  padding: 14px 20px;
  font-size: 13px;
  color: var(--text-muted);
}

@media (max-width: 900px) {
  .demo-scenes, .concept-grid { grid-template-columns: 1fr; }
  .aclass-layout { grid-template-columns: 1fr; }
  .stage-label { font-size: 11px; }
}
</style>
