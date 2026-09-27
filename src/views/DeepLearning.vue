<template>
  <div class="deep-learning-page">
    <div class="page-hero">
      <h1 class="hero-title">{{ t('deepLearning.title') }}</h1>
      <p class="hero-subtitle">{{ t('deepLearning.subtitle') }}</p>
    </div>

    <!-- ============ PyTorch 训练控制台 ============ -->
    <el-card class="console-card">
      <div class="console-head">
        <div class="console-head-left">
          <div class="console-icon"><Cpu /></div>
          <div>
            <h2 class="console-title">{{ t('deepLearning.consoleTitle') }}</h2>
            <p class="console-desc">{{ t('deepLearning.consoleDesc') }}</p>
          </div>
        </div>
        <div class="cap-badges" v-if="cap">
          <el-tag size="small" effect="dark" type="success">{{ t('deepLearning.capBackend') }}:
            {{ cap.backend }}</el-tag>
          <el-tag size="small" effect="dark" type="info" v-if="cap.torch_version">
            PyTorch {{ cap.torch_version }}</el-tag>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="console-tabs">
        <!-- 训练监控 -->
        <el-tab-pane :label="t('deepLearning.tabMonitor')" name="monitor">
          <div class="monitor-layout">
            <!-- 配置 -->
            <div class="config-panel">
              <h3 class="panel-title">{{ t('deepLearning.configTitle') }}</h3>
              <el-form label-position="top" class="config-form">
                <el-form-item :label="t('deepLearning.samples')">
                  <el-input-number v-model="cfg.samples" :min="60" :max="10000"
                    :step="100" size="small" controls-position="right" class="full" />
                </el-form-item>
                <el-form-item :label="t('deepLearning.epochs')">
                  <el-input-number v-model="cfg.epochs" :min="1" :max="100"
                    size="small" controls-position="right" class="full" />
                </el-form-item>
                <el-form-item :label="t('deepLearning.batchSize')">
                  <el-input-number v-model="cfg.batch_size" :min="4" :max="512"
                    :step="8" size="small" controls-position="right" class="full" />
                </el-form-item>
                <el-form-item :label="t('deepLearning.learningRate')">
                  <el-input-number v-model="cfg.learning_rate" :min="0.0001"
                    :max="1" :step="0.005" :precision="4" size="small"
                    controls-position="right" class="full" />
                </el-form-item>
                <el-form-item :label="t('deepLearning.seed')">
                  <el-input-number v-model="cfg.seed" :min="0" size="small"
                    controls-position="right" class="full" />
                </el-form-item>
              </el-form>

              <div class="config-actions">
                <el-button
                  type="primary" class="start-btn"
                  :disabled="isRunning"
                  :loading="starting"
                  @click="startTrain"
                >
                  <el-icon><VideoPlay /></el-icon>
                  {{ t('deepLearning.startTrain') }}
                </el-button>
                <el-button
                  type="danger" plain
                  :disabled="!isRunning"
                  @click="cancelTrain"
                >{{ t('deepLearning.cancelTrain') }}</el-button>
              </div>
            </div>

            <!-- 曲线与状态 -->
            <div class="chart-panel">
              <div class="task-status-row">
                <el-tag :type="statusTagType" effect="dark" size="default">
                  {{ statusLabel }}
                </el-tag>
                <span class="elapsed" v-if="currentTask">
                  {{ t('deepLearning.elapsed') }}: {{ elapsedText }}
                </span>
              </div>

              <div class="progress-row">
                <span class="progress-label">{{ t('deepLearning.progress') }}</span>
                <el-progress
                  :percentage="currentTask?.progress || 0"
                  :stroke-width="14"
                  :status="progressStatus"
                  striped
                  striped-flow
                />
              </div>

              <h3 class="panel-title chart-title">{{ t('deepLearning.lossCurve') }}</h3>
              <svg class="loss-chart" viewBox="0 0 560 250" preserveAspectRatio="none">
                <!-- 网格与左轴刻度（loss） -->
                <g v-for="(g, i) in chart.gridYs" :key="'g'+i">
                  <line :x1="chart.padL" :x2="chart.W - chart.padR"
                    :y1="g.y" :y2="g.y" stroke="rgba(255,255,255,0.07)" />
                  <text :x="chart.padL - 6" :y="g.y + 3" text-anchor="end"
                    class="axis-text">{{ g.lossLabel }}</text>
                  <text :x="chart.W - chart.padR + 6" :y="g.y + 3"
                    class="axis-text">{{ g.accLabel }}</text>
                </g>
                <!-- loss 曲线 -->
                <polyline :points="chart.lossPoints" fill="none"
                  stroke="#f87171" stroke-width="2" stroke-linejoin="round"
                  vector-effect="non-scaling-stroke" />
                <!-- 训练准确率 -->
                <polyline :points="chart.trainAccPoints" fill="none"
                  stroke="rgba(74,222,128,0.45)" stroke-width="1.5"
                  stroke-dasharray="4 3" vector-effect="non-scaling-stroke" />
                <!-- 验证准确率 -->
                <polyline :points="chart.valAccPoints" fill="none"
                  stroke="#4ade80" stroke-width="2" stroke-linejoin="round"
                  vector-effect="non-scaling-stroke" />
              </svg>

              <div class="chart-legend">
                <span class="legend-item"><i class="sw loss"></i>
                  {{ t('deepLearning.legendLoss') }}</span>
                <span class="legend-item"><i class="sw val"></i>
                  {{ t('deepLearning.legendValAcc') }}</span>
                <span class="legend-item"><i class="sw train"></i>
                  {{ t('deepLearning.legendTrainAcc') }}</span>
              </div>

              <div class="metric-chips" v-if="(currentTask?.metrics?.length)">
                <div class="metric-chip">
                  <span class="mc-label">{{ t('deepLearning.finalLoss') }}</span>
                  <span class="mc-value">{{ currentTask.metrics.at(-1).loss }}</span>
                </div>
                <div class="metric-chip">
                  <span class="mc-label">{{ t('deepLearning.bestValAcc') }}</span>
                  <span class="mc-value accent">{{ bestValAcc }}</span>
                </div>
              </div>

              <div class="task-error" v-if="currentTask?.error_message">
                <el-icon><WarningFilled /></el-icon>
                {{ currentTask.error_message }}
              </div>

              <!-- 训练产出已接入预设审核工作流的状态横幅 -->
              <div class="review-banner" v-if="reviewWf">
                <el-icon><ArrowRight /></el-icon>
                <span class="rb-text">{{ t('deepLearning.reviewBanner') }} #{{ reviewWf.id }}</span>
                <el-button size="small" text type="primary"
                  @click="router.push(`/projects/${reviewWf.project_id}`)">
                  {{ t('deepLearning.reviewView') }}
                </el-button>
              </div>

              <!-- 审核流接入失败：提供重试入口 -->
              <div class="review-banner review-banner--warn" v-else-if="reviewFailed && currentTask?.status === 'completed'">
                <el-icon><WarningFilled /></el-icon>
                <span class="rb-text">{{ t('deepLearning.reviewFailed') }}</span>
                <el-button size="small" text type="primary" @click="submitTrainingReview(currentTask)">
                  {{ t('deepLearning.reviewRetry') }}
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 训练日志 -->
        <el-tab-pane :label="t('deepLearning.tabLogs')" name="logs">
          <pre class="logs-box">{{ currentTask?.logs || t('deepLearning.logsEmpty') }}</pre>
        </el-tab-pane>

        <!-- 历史任务 -->
        <el-tab-pane :label="t('deepLearning.tabHistory')" name="history">
          <el-table :data="history" size="small" class="history-table" stripe>
            <el-table-column prop="name" :label="t('deepLearning.colName')" min-width="220" />
            <el-table-column :label="t('deepLearning.colStatus')" width="110">
              <template #default="{ row }">
                <el-tag size="small" effect="dark"
                  :type="statusTypeOf(row.status)">
                  {{ statusTextOf(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('deepLearning.colProgress')" width="160">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :stroke-width="8"
                  :status="row.status === 'failed' ? 'exception'
                    : row.status === 'completed' ? 'success' : undefined" />
              </template>
            </el-table-column>
            <el-table-column prop="best_val_acc" :label="t('deepLearning.colBestVal')"
              width="140" />
            <el-table-column :label="t('deepLearning.colCompletedAt')" width="120">
              <template #default="{ row }">
                {{ formatDate(row.completed_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!history.length" :description="t('deepLearning.historyEmpty')" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ============ AI 创意工具（保留原有功能卡片） ============ -->
    <div class="features-section">
      <h2 class="features-heading">{{ t('deepLearning.featuresTitle') }}</h2>
      <div class="features-grid">
        <el-card class="feature-card" v-for="feature in features" :key="feature.id">
          <div class="feature-icon" :class="feature.key">
            <el-icon :size="30"><component :is="feature.icon" /></el-icon>
          </div>
          <h3 class="feature-title">{{ t(feature.titleKey) }}</h3>
          <p class="feature-desc">{{ t(feature.descKey) }}</p>
          <el-button type="primary" class="feature-btn" @click="startFeature(feature.key)">
            <span>{{ t('deepLearning.start') }}</span>
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Brush, MagicStick, Sunny, ArrowRight, VideoPlay, Cpu, WarningFilled
} from '@element-plus/icons-vue'
import { aiAPI, workflowAPI, projectAPI } from '../api'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const auth = useAuthStore()

// ── 训练配置与状态 ──
const cap = ref(null)
const cfg = reactive({
  samples: 600, epochs: 20, batch_size: 32, learning_rate: 0.01, seed: 42
})
const activeTab = ref('monitor')
const currentTask = ref(null)
const history = ref([])
const starting = ref(false)
const pollTimer = ref(null)
const nowTs = ref(Date.now())

const features = [
  { id: 1, key: 'style-transfer', icon: Brush,
    titleKey: 'deepLearning.styleTransferTitle',
    descKey: 'deepLearning.styleTransferDesc' },
  { id: 2, key: 'sketch-to-3d', icon: MagicStick,
    titleKey: 'deepLearning.sketchTo3dTitle',
    descKey: 'deepLearning.sketchTo3dDesc' },
  { id: 3, key: 'dream-design', icon: Sunny,
    titleKey: 'deepLearning.dreamDesignTitle',
    descKey: 'deepLearning.dreamDesignDesc' }
]

const isRunning = computed(() =>
  ['pending', 'running'].includes(currentTask.value?.status))

// ── 状态文本/标签类型 ──
const statusTextOf = (s) => t(`deepLearning.status${s[0].toUpperCase()}${s.slice(1)}`)
const statusTypeOf = (s) => ({
  pending: 'info', running: 'primary', completed: 'success',
  failed: 'danger', cancelled: 'info'
}[s])

const statusLabel = computed(() =>
  currentTask.value ? statusTextOf(currentTask.value.status) : '—')
const statusTagType = computed(() =>
  currentTask.value ? statusTypeOf(currentTask.value.status) : 'info')

const progressStatus = computed(() => {
  const s = currentTask.value?.status
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'exception'
  return undefined
})

const bestValAcc = computed(() => {
  const m = currentTask.value?.metrics || []
  return m.length ? Math.max(...m.map(x => x.val_acc)).toFixed(3) : '—'
})

// ── 耗时 ──
const elapsedText = computed(() => {
  const t0 = currentTask.value?.started_at
  if (!t0) return '0s'
  const t1 = currentTask.value.completed_at
    ? new Date(currentTask.value.completed_at).getTime()
    : nowTs.value
  let sec = Math.max(0, Math.round((t1 - new Date(t0).getTime()) / 1000))
  if (sec >= 60) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  return `${sec}s`
})

// ── SVG 曲线图几何 ──
const chart = computed(() => {
  const W = 560
  const H = 250
  const padL = 44, padR = 48, padT = 14, padB = 30
  const metrics = currentTask.value?.metrics || []
  const n = metrics.length
  const innerW = W - padL - padR
  const innerH = H - padT - padB

  const maxLoss = Math.max(0.1, ...metrics.map(m => m.loss))

  const xAt = (i) => n <= 1 ? padL + innerW / 2
    : padL + innerW * i / (n - 1)
  const yLoss = (v) => padT + innerH * (1 - v / maxLoss)
  const yAcc = (v) => padT + innerH * (1 - v)

  const lossPoints = metrics.map((m, i) =>
    `${xAt(i)},${yLoss(m.loss)}`).join(' ')
  const valAccPoints = metrics.map((m, i) =>
    `${xAt(i)},${yAcc(m.val_acc)}`).join(' ')
  const trainAccPoints = metrics.map((m, i) =>
    `${xAt(i)},${yAcc(m.train_acc)}`).join(' ')

  // 5 条水平网格的刻度
  const gridYs = Array.from({ length: 5 }, (_, i) => {
    const y = padT + innerH * i / 4
    return {
      y,
      lossLabel: (maxLoss * (1 - i / 4)).toFixed(2),
      accLabel: (1 - i / 4).toFixed(1)
    }
  })

  return { W, H, padL, padR, padT, padB, lossPoints, valAccPoints,
    trainAccPoints, gridYs }
})

// ── 训练启动 / 轮询 / 取消 ──
const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

const pollTask = async () => {
  if (!currentTask.value) return
  nowTs.value = Date.now()
  try {
    const { data } = await aiAPI.getTask(currentTask.value.id)
    currentTask.value = data
    if (['completed', 'failed', 'cancelled'].includes(data.status)) {
      stopPolling()
      await loadHistory()
      if (data.status === 'completed') {
        ElMessage.success(t('deepLearning.statusCompleted'))
        // 训练产出 → 预设工作流审核（合规性 + 质量），自动接入
        await submitTrainingReview(data)
      }
    }
  } catch {
    stopPolling()
  }
}

// ── 训练产出接入工作流审核 ──
// 调用 POST /workflows/training-review（需登录 Token）：归属校验后
// 在项目下创建 training_review 工作流并预置"合规性审核→质量审核"两道人工步骤
const reviewWf = ref(null)
const reviewFailed = ref(false)
const submitTrainingReview = async (task) => {
  reviewFailed.value = false
  try {
    const { data: projects } = await projectAPI.list()
    if (!projects.length) {
      console.warn('[review] 无可用项目，训练产出未接入审核流')
      reviewFailed.value = true
      return
    }
    const { data: wf } = await workflowAPI.createTrainingReview({
      project_id: projects[0].id, task_id: task.id
    })
    reviewWf.value = wf
    ElMessage.success(t('deepLearning.reviewSubmitted', { id: wf.id }))
  } catch (e) {
    console.warn('[review] 审核流接入失败', e?.response?.data?.detail || e)
    reviewFailed.value = true
  }
}

const startTrain = async () => {
  // 身份验证闸口：后端 /ai/train 强制 JWT 校验，未登录时引导登录并回跳本页
  if (!auth.isAuthenticated) {
    try {
      await ElMessageBox.confirm(
        t('deepLearning.loginRequired'), t('deepLearning.loginRequiredTitle'),
        { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' }
      )
    } catch { return }
    router.push({ path: '/login', query: { redirect: '/deep-learning' } })
    return
  }
  starting.value = true
  try {
    const { data } = await aiAPI.train({
      samples: cfg.samples, epochs: cfg.epochs, batch_size: cfg.batch_size,
      learning_rate: cfg.learning_rate, seed: cfg.seed
    })
    currentTask.value = data
    activeTab.value = 'monitor'
    stopPolling()
    pollTimer.value = setInterval(pollTask, 1000)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('deepLearning.trainFailed'))
  } finally {
    starting.value = false
  }
}

const cancelTrain = async () => {
  if (!currentTask.value) return
  try {
    const { data } = await aiAPI.cancelTask(currentTask.value.id)
    currentTask.value = data
    stopPolling()
    await loadHistory()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('common.error'))
  }
}

// ── 历史任务 ──
const loadHistory = async () => {
  try {
    const { data } = await aiAPI.listTasks()
    history.value = (data.tasks || []).map(t => ({
      ...t,
      best_val_acc: t.metrics?.length
        ? Math.max(...t.metrics.map(m => m.val_acc)).toFixed(3)
        : '—'
    }))
  } catch { /* 未登录等场景静默 */ }
}

const formatDate = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()).padStart(2, '0')}`
}

const startFeature = (key) => {
  const feature = features.find(f => f.key === key)
  const name = feature ? t(feature.titleKey) : key
  ElMessage.info(t('deepLearning.starting', { name }))
}

onMounted(async () => {
  try {
    cap.value = (await aiAPI.getTrainingCapabilities()).data
  } catch { /* 能力端点不可用时忽略 */ }
  await loadHistory()
})

onUnmounted(stopPolling)
</script>

<style scoped>
.deep-learning-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 12px 0;
}

.page-hero { text-align: center; padding: 24px 20px 4px; }

.hero-title {
  margin: 0 0 10px;
  font-size: 34px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.hero-subtitle {
  margin: 0 auto;
  max-width: 560px;
  font-size: 15px;
  color: var(--text-muted);
  line-height: 1.6;
}

/* ===== 控制台卡片 ===== */
.console-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.console-card :deep(.el-card__body) { padding: 22px 24px; }

.console-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.console-head-left { display: flex; align-items: center; gap: 14px; }

.console-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: var(--accent);
  background: var(--accent-bg);
  border: 1px solid rgba(74, 222, 128, 0.2);
}

.console-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.console-desc {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.cap-badges { display: flex; gap: 8px; }

.console-tabs { margin-top: 10px; }
.console-tabs :deep(.el-tabs__item) { font-weight: 600; font-size: 14px; }
.console-tabs :deep(.el-tabs__item.is-active) { color: var(--accent); }
.console-tabs :deep(.el-tabs__active-bar) { background-color: var(--accent); }

/* ===== 监控布局 ===== */
.monitor-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 24px;
}

.config-panel {
  border-right: 1px solid var(--border-color);
  padding-right: 24px;
}

.panel-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 14px;
}

.config-form :deep(.el-form-item) { margin-bottom: 12px; }
.config-form :deep(.el-form-item__label) {
  font-size: 11px;
  color: var(--text-muted);
  padding-bottom: 3px;
  line-height: 1.4;
}
.full { width: 100%; }

.config-actions { display: flex; flex-direction: column; gap: 10px; margin-top: 6px; }

.start-btn {
  background: var(--accent);
  border-color: var(--accent);
  color: #06120a;
  font-weight: 700;
}

.start-btn:hover {
  background: #22c55e;
  border-color: #22c55e;
}

.chart-panel { min-width: 0; }

.task-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.elapsed { font-size: 12px; color: var(--text-muted); }

.progress-row { margin-bottom: 18px; }

.progress-label {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.chart-title { margin-top: 6px; margin-bottom: 8px; }

.loss-chart {
  width: 100%;
  height: 250px;
  display: block;
}

.axis-text {
  fill: rgba(255, 255, 255, 0.35);
  font-size: 10px;
}

.chart-legend {
  display: flex;
  gap: 18px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-item { display: flex; align-items: center; gap: 6px; }

.sw { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
.sw.loss { background: #f87171; }
.sw.val { background: #4ade80; }
.sw.train { background: rgba(74, 222, 128, 0.5); }

.metric-chips { display: flex; gap: 12px; margin-top: 16px; }

.metric-chip {
  flex: 1;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mc-label { font-size: 12px; color: var(--text-muted); }
.mc-value { font-size: 18px; font-weight: 800; color: var(--text-primary); }
.mc-value.accent { color: var(--accent); }

.task-error {
  margin-top: 14px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #f87171;
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 8px;
}

/* 审核工作流接入横幅 */
.review-banner {
  margin-top: 14px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.08);
  border: 1px solid rgba(74, 222, 128, 0.25);
  border-radius: 8px;
}
.review-banner .rb-text { flex: 1; }
.review-banner--warn {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.3);
}

/* ===== 日志 ===== */
.logs-box {
  background: #0a0a10;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.75);
  max-height: 460px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ===== 历史表格 ===== */
.history-table { border-radius: 8px; }
.history-table :deep(.el-table__empty-block) { min-height: 120px; }

/* ===== 功能卡片 ===== */
.features-section { max-width: 1200px; width: 100%; margin: 0 auto; }

.features-heading {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 18px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.feature-card:hover {
  border-color: rgba(74, 222, 128, 0.3);
  transform: translateY(-3px);
}

.feature-card :deep(.el-card__body) {
  padding: 26px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-icon.style-transfer {
  background: var(--accent-bg);
  color: var(--accent);
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
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.feature-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.65;
}

.feature-btn {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
  margin-top: 6px;
  align-self: flex-start;
}

.feature-btn:hover {
  background: var(--accent);
  border-color: var(--accent);
}

@media (max-width: 900px) {
  .monitor-layout { grid-template-columns: 1fr; }
  .config-panel { border-right: none; padding-right: 0; }
  .features-grid { grid-template-columns: 1fr; }
}
</style>
