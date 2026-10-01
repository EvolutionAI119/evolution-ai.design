<template>
  <div class="evidence-panel" v-loading="loading">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">{{ t('analytics.granularity') }}</span>
        <el-radio-group v-model="granularity" size="small">
          <el-radio-button value="day">{{ t('analytics.day') }}</el-radio-button>
          <el-radio-button value="week">{{ t('analytics.week') }}</el-radio-button>
          <el-radio-button value="month">{{ t('analytics.month') }}</el-radio-button>
        </el-radio-group>
      </div>
      <div class="filter-group">
        <span class="filter-label">{{ t('analytics.range') }}</span>
        <el-radio-group v-model="days" size="small">
          <el-radio-button :value="7">7{{ t('analytics.daysUnit') }}</el-radio-button>
          <el-radio-button :value="30">30{{ t('analytics.daysUnit') }}</el-radio-button>
          <el-radio-button :value="60">60{{ t('analytics.daysUnit') }}</el-radio-button>
          <el-radio-button :value="90">90{{ t('analytics.daysUnit') }}</el-radio-button>
        </el-radio-group>
      </div>
      <span class="gen-time" v-if="summary">
        {{ t('analytics.generatedAt') }} {{ formatTime(summary.generated_at) }}
      </span>
    </div>

    <!-- KPI 卡片 -->
    <div class="kpi-grid">
      <div class="kpi-card" v-for="kpi in kpiCards" :key="kpi.key">
        <div class="kpi-icon" :style="{ background: kpi.bg, color: kpi.color }">
          <el-icon :size="18"><component :is="kpi.icon" /></el-icon>
        </div>
        <div class="kpi-meta">
          <span class="kpi-value">{{ kpi.value }}</span>
          <span class="kpi-label">{{ kpi.label }}</span>
        </div>
      </div>
    </div>

    <!-- 主趋势图 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('analytics.trendTitle') }}</span>
          <el-radio-group v-model="trendMetric" size="small">
            <el-radio-button value="visits">{{ t('analytics.metricVisits') }}</el-radio-button>
            <el-radio-button value="registrations">{{ t('analytics.metricRegs') }}</el-radio-button>
            <el-radio-button value="interactions">{{ t('analytics.metricInteractions') }}</el-radio-button>
            <el-radio-button value="references">{{ t('analytics.metricRefs') }}</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="trendChartRef" class="chart-box tall"></div>
    </el-card>

    <!-- 分布图表 -->
    <div class="dist-grid">
      <el-card class="chart-card">
        <template #header>
          <span class="card-title">{{ t('analytics.topPages') }}</span>
        </template>
        <div ref="pagesChartRef" class="chart-box"></div>
      </el-card>
      <el-card class="chart-card">
        <template #header>
          <span class="card-title">{{ t('analytics.topPlatforms') }}</span>
        </template>
        <div ref="platformsChartRef" class="chart-box"></div>
      </el-card>
    </div>

    <!-- 外部引用核验 -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('analytics.refsTitle') }}</span>
          <el-button size="small" text @click="showRefSubmit = !showRefSubmit">
            <el-icon><Plus /></el-icon>{{ t('analytics.submitRef') }}
          </el-button>
        </div>
      </template>

      <el-form v-if="showRefSubmit" class="ref-submit" inline @submit.prevent>
        <el-form-item>
          <el-input v-model="refForm.source_url" :placeholder="t('analytics.refUrl')" class="ref-input" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="refForm.source_platform" :placeholder="t('analytics.refPlatform')" class="ref-input-sm" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="small" @click="submitRef">
            {{ t('analytics.submitForVerify') }}
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="pendingRefs.length" class="pending-section">
        <div class="section-sub-title">
          <el-icon><WarningFilled /></el-icon>
          {{ t('analytics.pendingQueue') }} ({{ pendingRefs.length }})
        </div>
        <div class="ref-row pending" v-for="r in pendingRefs" :key="'p'+r.id">
          <div class="ref-info">
            <el-tag size="small" type="info">{{ r.source_platform }}</el-tag>
            <a :href="r.source_url" target="_blank" rel="noopener" class="ref-url">
              {{ r.source_url }}
            </a>
          </div>
          <div class="ref-actions">
            <el-button size="small" type="success" @click="verifyRef(r)">
              {{ t('analytics.verify') }}
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="verifiedRefs.length === 0 && pendingRefs.length === 0"
        :description="t('analytics.noRefs')" :image-size="70" />

      <div class="ref-row" v-for="r in verifiedRefs" :key="r.id">
        <div class="ref-info">
          <el-tag size="small" type="success" effect="dark">{{ r.source_platform }}</el-tag>
          <a :href="r.source_url" target="_blank" rel="noopener" class="ref-url">
            {{ r.title || r.source_url }}
          </a>
          <span class="ref-time">{{ formatTime(r.verified_at || r.created_at) }}</span>
        </div>
      </div>
    </el-card>

    <!-- 数据导出 -->
    <el-card class="chart-card">
      <template #header>
        <span class="card-title">{{ t('analytics.exportTitle') }}</span>
      </template>
      <div class="export-grid">
        <div class="export-item" v-for="d in exportDatasets" :key="d.key">
          <span class="export-name">{{ d.label }}</span>
          <div class="export-btns">
            <el-button size="small" @click="doExport(d.key, 'csv')">CSV</el-button>
            <el-button size="small" @click="doExport(d.key, 'json')">JSON</el-button>
          </div>
        </div>
      </div>
      <p class="export-note">{{ t('analytics.exportNote') }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import {
  View, User, Timer, UserFilled, ChatDotRound, Link, Promotion,
  Plus, WarningFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api, { analyticsAPI } from '../api'

const { t } = useI18n({ useScope: 'global' })

// ── 筛选状态 ──
const granularity = ref('day')
const days = ref(30)
const trendMetric = ref('visits')
const loading = ref(false)
const summary = ref(null)

// ── 图表 DOM / 实例 ──
const trendChartRef = ref(null)
const pagesChartRef = ref(null)
const platformsChartRef = ref(null)
const charts = {}

// ── 引用状态 ──
const verifiedRefs = ref([])
const pendingRefs = ref([])
const showRefSubmit = ref(false)
const refForm = reactive({ source_url: '', source_platform: '' })

const exportDatasets = computed(() => [
  { key: 'visits', label: t('analytics.metricVisits') },
  { key: 'registrations', label: t('analytics.metricRegs') },
  { key: 'messages', label: t('analytics.metricInteractions') },
  { key: 'references', label: t('analytics.metricRefs') },
])

// ───────────────────────────────────────────
// 工具函数
// ───────────────────────────────────────────

function formatTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function getChart(refEl, key) {
  if (!charts[key] && refEl) {
    charts[key] = echarts.init(refEl)
  }
  return charts[key]
}

function axisCommon() {
  const dark = !document.documentElement.classList.contains('light-theme')
  return {
    axisLine: { lineStyle: { color: dark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.3)' } },
    axisLabel: { color: dark ? 'rgba(255,255,255,0.55)' : 'rgba(0,0,0,0.6)', fontSize: 11 },
    splitLine: { lineStyle: { color: dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)' } },
  }
}

// ───────────────────────────────────────────
// 图表渲染
// ───────────────────────────────────────────

function renderTrend() {
  if (!summary.value) return
  const chart = getChart(trendChartRef.value, 'trend')
  const s = summary.value.series
  let series = []
  let legend = []
  if (trendMetric.value === 'visits') {
    legend = [t('analytics.legendPV'), t('analytics.legendUV')]
    series = [
      { name: legend[0], type: 'line', smooth: true, showSymbol: false,
        data: s.visits.map(x => x.pv),
        areaStyle: { opacity: 0.18 }, lineStyle: { width: 2.5 },
        itemStyle: { color: '#4ade80' } },
      { name: legend[1], type: 'line', smooth: true, showSymbol: false,
        data: s.visits.map(x => x.uv),
        lineStyle: { width: 2 }, itemStyle: { color: '#93c5fd' } },
    ]
  } else if (trendMetric.value === 'registrations') {
    legend = [t('analytics.legendRegs')]
    series = [{ name: legend[0], type: 'bar', data: s.registrations.map(x => x.value),
      barMaxWidth: 26, itemStyle: { color: '#4ade80', borderRadius: [4, 4, 0, 0] } }]
  } else if (trendMetric.value === 'interactions') {
    legend = [t('analytics.legendMsgs'), t('analytics.legendReplies')]
    series = [
      { name: legend[0], type: 'line', smooth: true, showSymbol: false,
        data: s.messages.map(x => x.value),
        areaStyle: { opacity: 0.15 }, itemStyle: { color: '#c084fc' } },
      { name: legend[1], type: 'line', smooth: true, showSymbol: false,
        data: s.messages.map(x => x.replies ?? 0),
        lineStyle: { width: 2 }, itemStyle: { color: '#fbbf24' } },
    ]
  } else {
    legend = [t('analytics.legendRefs')]
    series = [{ name: legend[0], type: 'bar', data: s.references.map(x => x.value),
      barMaxWidth: 26, itemStyle: { color: '#38bdf8', borderRadius: [4, 4, 0, 0] } }]
  }
  const buckets = s.visits.map(x => x.bucket)
  const ax = axisCommon()
  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,20,30,0.92)',
      borderColor: 'rgba(74,222,128,0.3)', textStyle: { color: '#fff', fontSize: 12 } },
    legend: { data: legend, textStyle: { color: ax.axisLabel.color }, top: 0 },
    grid: { left: 48, right: 20, top: 38, bottom: 48 },
    xAxis: { type: 'category', data: buckets, boundaryGap: trendMetric.value !== 'visits',
      axisLine: ax.axisLine, axisLabel: { ...ax.axisLabel, rotate: buckets.length > 20 ? 35 : 0 } },
    yAxis: { type: 'value', axisLine: ax.axisLine, axisLabel: ax.axisLabel,
      splitLine: ax.splitLine },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10,
      borderColor: 'rgba(255,255,255,0.1)', textStyle: { fontSize: 10 } }],
    series,
  }, true)
}

function renderPages() {
  if (!summary.value) return
  const chart = getChart(pagesChartRef.value, 'pages')
  const rows = [...summary.value.top_pages].reverse()
  const ax = axisCommon()
  chart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(20,20,30,0.92)',
      textStyle: { color: '#fff', fontSize: 12 } },
    grid: { left: 90, right: 24, top: 12, bottom: 20 },
    xAxis: { type: 'value', axisLine: ax.axisLine, axisLabel: ax.axisLabel,
      splitLine: ax.splitLine },
    yAxis: { type: 'category', data: rows.map(x => x.path),
      axisLine: ax.axisLine, axisLabel: ax.axisLabel },
    series: [{ type: 'bar', data: rows.map(x => x.count), barMaxWidth: 16,
      itemStyle: { color: '#4ade80', borderRadius: [0, 4, 4, 0] } }],
  }, true)
}

function renderPlatforms() {
  if (!summary.value) return
  const chart = getChart(platformsChartRef.value, 'platforms')
  const colors = ['#4ade80', '#38bdf8', '#c084fc', '#fbbf24', '#fb7185',
    '#34d399', '#60a5fa', '#f472b6']
  chart.setOption({
    tooltip: { trigger: 'item', backgroundColor: 'rgba(20,20,30,0.92)',
      textStyle: { color: '#fff', fontSize: 12 } },
    legend: { bottom: 0, textStyle: { color: axisCommon().axisLabel.color, fontSize: 11 },
      type: 'scroll' },
    series: [{
      type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'],
      data: summary.value.top_platforms.map((x, i) => ({
        name: x.platform, value: x.count,
        itemStyle: { color: colors[i % colors.length] } })),
      label: { color: axisCommon().axisLabel.color, fontSize: 11 },
      itemStyle: { borderColor: '#16161f', borderWidth: 2 },
    }],
  }, true)
}

// ───────────────────────────────────────────
// 数据加载
// ───────────────────────────────────────────

async function loadSummary() {
  loading.value = true
  try {
    const { data } = await analyticsAPI.publicSummary(granularity.value, days.value)
    summary.value = data
    await nextTick()
    renderTrend()
    renderPages()
    renderPlatforms()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('analytics.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadRefs() {
  try {
    const { data } = await analyticsAPI.listReferences(50)
    verifiedRefs.value = data.items
  } catch {}
  try {
    const { data } = await analyticsAPI.listAllReferences(
      { verified: false, page_size: 50 })
    pendingRefs.value = data.items
  } catch {}
}

// ── 引用提交 / 核验 ──

async function submitRef() {
  if (!refForm.source_url.trim() || !refForm.source_platform.trim()) {
    ElMessage.warning(t('analytics.formRequired'))
    return
  }
  try {
    const { data } = await analyticsAPI.submitReference({
      source_url: refForm.source_url.trim(),
      source_platform: refForm.source_platform.trim() })
    if (data.duplicate) ElMessage.info(t('analytics.refDuplicate'))
    else ElMessage.success(t('analytics.refSubmitted'))
    refForm.source_url = ''
    refForm.source_platform = ''
    showRefSubmit.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('analytics.sendFailed'))
  }
}

async function verifyRef(r) {
  try {
    await analyticsAPI.verifyReference(r.id)
    ElMessage.success(t('analytics.verified'))
    await loadSummary()
    await loadRefs()
  } catch {}
}

// ── 数据导出 ──

async function doExport(dataset, fmt) {
  try {
    const res = await api.get(analyticsAPI.exportPath(
      dataset, granularity.value, days.value, fmt),
      { responseType: 'blob' })
    const disposition = res.headers['content-disposition'] || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `evidence_${dataset}.${fmt}`
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error(t('analytics.exportFailed'))
  }
}

// ───────────────────────────────────────────
// KPI 卡片
// ───────────────────────────────────────────

const kpiCards = computed(() => {
  const k = summary.value?.kpi
  if (!k) return []
  const durationMin = Math.round(k.avg_duration_seconds / 60)
  return [
    { key: 'pv', label: t('analytics.kpiPV'), value: k.total_pv,
      icon: View, bg: 'rgba(74,222,128,0.15)', color: '#4ade80' },
    { key: 'uv', label: t('analytics.kpiUV'), value: k.total_uv,
      icon: User, bg: 'rgba(56,189,248,0.15)', color: '#38bdf8' },
    { key: 'dur', label: t('analytics.kpiDuration'),
      value: `${durationMin} ${t('analytics.minutesUnit')}`,
      icon: Timer, bg: 'rgba(251,191,36,0.15)', color: '#fbbf24' },
    { key: 'reg', label: t('analytics.kpiRegs'), value: k.total_registrations,
      icon: UserFilled, bg: 'rgba(52,211,153,0.15)', color: '#34d399' },
    { key: 'msg', label: t('analytics.kpiMsgs'), value: k.total_messages,
      icon: ChatDotRound, bg: 'rgba(192,132,252,0.15)', color: '#c084fc' },
    { key: 'rate', label: t('analytics.kpiReplyRate'),
      value: `${Math.round(k.reply_rate * 100)}%`,
      icon: Promotion, bg: 'rgba(251,113,133,0.15)', color: '#fb7185' },
    { key: 'ref', label: t('analytics.kpiRefs'), value: k.total_references,
      icon: Link, bg: 'rgba(96,165,250,0.15)', color: '#60a5fa' },
  ]
})

// ───────────────────────────────────────────
// 生命周期
// ───────────────────────────────────────────

const onResize = () => Object.values(charts).forEach(c => c.resize())

onMounted(async () => {
  await loadSummary()
  await loadRefs()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  Object.values(charts).forEach(c => c.dispose())
})

watch([granularity, days], loadSummary)
watch(trendMetric, () => nextTick().then(renderTrend))
</script>

<style scoped>
.evidence-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.filter-group { display: flex; align-items: center; gap: 10px; }
.filter-label { font-size: 12px; color: var(--text-muted); }
.gen-time { margin-left: auto; font-size: 11px; color: var(--text-muted); }

.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

:deep(.el-card__body) { padding: 16px 18px; }
:deep(.el-card__header) { padding: 12px 18px; border-bottom: 1px solid var(--border-color); }

/* KPI 网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  transition: transform 0.22s ease, border-color 0.22s ease;
}

.kpi-card:hover { transform: translateY(-3px); border-color: rgba(74,222,128,0.4); }

.kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-meta { display: flex; flex-direction: column; min-width: 0; }
.kpi-value { font-size: 18px; font-weight: 800; color: var(--text-primary); line-height: 1.2; }
.kpi-label { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }

.chart-box { height: 260px; }
.chart-box.tall { height: 320px; }

.dist-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 16px;
}

/* 引用列表 */
.ref-submit { margin-bottom: 14px; }
.ref-input { width: 320px; }
.ref-input-sm { width: 180px; }

.pending-section {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(251, 191, 36, 0.06);
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 10px;
}

.section-sub-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #fbbf24;
  margin-bottom: 10px;
}

.ref-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.ref-row:last-child { border-bottom: none; }
.ref-info { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.ref-url {
  color: var(--text-secondary);
  font-size: 13px;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 480px;
}
.ref-url:hover { color: var(--accent); }
.ref-time { font-size: 11px; color: var(--text-muted); margin-left: auto; }

/* 导出 */
.export-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.export-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.export-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.export-btns { display: flex; gap: 8px; }
.export-note { margin: 12px 0 0; font-size: 11px; color: var(--text-muted); }

@media (max-width: 1100px) {
  .kpi-grid { grid-template-columns: repeat(4, 1fr); }
}

@media (max-width: 900px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .dist-grid { grid-template-columns: 1fr; }
  .gen-time { margin-left: 0; }
}
</style>
