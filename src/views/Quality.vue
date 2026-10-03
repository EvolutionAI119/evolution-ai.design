<template>
  <div class="quality-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">{{ t('quality.title') }}</h2>
        <p class="page-subtitle">{{ t('quality.pageSubtitle') }}</p>
      </div>
      <div class="header-actions">
        <el-select v-model="selectedModel" :placeholder="t('quality.selectModel')" class="model-select">
          <el-option v-for="model in models" :key="model.id" :label="model.name" :value="model.id" />
        </el-select>
        <el-button type="primary" class="btn-primary" :disabled="!selectedModel" @click="startCheck">
          <el-icon><VideoPlay /></el-icon>
          <span>{{ t('quality.startCheck') }}</span>
        </el-button>
      </div>
    </div>

    <div class="check-cards">
      <el-card class="check-card" v-for="check in checkTypes" :key="check.key">
        <div class="check-header">
          <div class="check-icon" :class="check.key">
            <el-icon :size="24"><component :is="check.icon" /></el-icon>
          </div>
          <el-tag :type="check.statusType" effect="dark" size="small">{{ checkStatusText(check.status) }}</el-tag>
        </div>
        <h3 class="check-title">{{ t(check.titleKey) }}</h3>
        <p class="check-desc">{{ t(check.descKey) }}</p>
        <div class="check-progress" v-if="check.status === 'running'">
          <el-progress :percentage="check.progress" :stroke-width="6" :show-text="false" :color="'#4ade80'" />
        </div>
        <div class="check-score" v-if="check.status === 'completed'">
          <span class="score-label">{{ t('quality.score') }}</span>
          <span class="score-value">{{ check.score }}/100</span>
        </div>
      </el-card>

      <!-- G2 曲率连续性检测卡片 -->
      <el-card class="check-card g2-card">
        <div class="check-header">
          <div class="check-icon g2">
            <el-icon :size="24"><Connection /></el-icon>
          </div>
          <el-tag
            :type="g2Result.overall_g2_pass === true ? 'success' : g2Result.overall_g2_pass === false ? 'danger' : 'info'"
            effect="dark" size="small"
          >{{ g2Result.overall_g2_pass === true ? t('quality.g2Pass') : g2Result.overall_g2_pass === false ? t('quality.g2Fail') : t('quality.statusNotStarted') }}</el-tag>
        </div>
        <h3 class="check-title">{{ t('quality.g2Check') }}</h3>
        <p class="check-desc">{{ t('quality.g2CheckDesc') }}</p>
        <div class="g2-actions">
          <el-button
            type="primary" size="small" :loading="g2Loading"
            :disabled="!selectedModel" @click="runG2Check"
          >
            {{ g2Loading ? t('quality.g2Checking') : t('quality.g2RunCheck') }}
          </el-button>
        </div>
        <div class="check-score" v-if="g2Result.overall_g2_pass !== null && g2Result.overall_g2_pass !== undefined">
          <span class="score-label">{{ t('quality.score') }}</span>
          <span class="score-value">{{ g2Result.pass_rate }}/100</span>
        </div>
      </el-card>
    </div>

    <!-- G2 接缝明细 -->
    <el-card v-if="g2Result.pairs && g2Result.pairs.length" class="g2-detail-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('quality.g2Pairs') }}</span>
          <span class="g2-standard">{{ t('quality.g2Standard') }}</span>
        </div>
      </template>
      <el-table :data="g2Result.pairs" style="width: 100%">
        <el-table-column prop="seam" :label="t('quality.g2Seam')" min-width="180" />
        <el-table-column :label="t('quality.g2Ratio')" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.curvature_ratio !== null && row.curvature_ratio !== undefined"
                  :class="row.g2_pass ? 'score-pass' : 'score-fail'">
              {{ row.curvature_ratio.toFixed(4) }}
            </span>
            <span v-else class="g2-na">—</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('quality.g2Status')" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'pass' ? 'success' : row.status === 'fail' ? 'danger' : 'info'"
              effect="dark" size="small"
            >
              {{ row.status === 'pass' ? t('quality.g2Pass') : row.status === 'fail' ? t('quality.g2Fail') : t('quality.g2NoData') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" :label="t('quality.g2Threshold')" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-card class="reports-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('quality.recentReports') }}</span>
          <el-button type="primary" text>{{ t('dashboard.viewAll') }}</el-button>
        </div>
      </template>
      <el-table :data="recentReports" style="width: 100%">
        <el-table-column prop="id" :label="t('projects.id')" width="80" />
        <el-table-column prop="modelName" :label="t('quality.colModel')" />
        <el-table-column prop="checkType" :label="t('quality.checkType')" width="140" />
        <el-table-column prop="score" :label="t('quality.score')" width="120">
          <template #default="{ row }">
            <span :class="row.score >= 80 ? 'score-pass' : 'score-fail'">{{ row.score }}/100</span>
          </template>
        </el-table-column>
        <el-table-column prop="result" :label="t('quality.result')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" effect="dark" size="small">{{ row.passed ? t('quality.passShort') : t('quality.failShort') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date" :label="t('quality.dateLabel')" width="160" />
        <el-table-column :label="t('common.actions')" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewReport(row)">{{ t('quality.view') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { VideoPlay, Grid, Sunny, TrendCharts, Connection } from '@element-plus/icons-vue'
import { qualityAPI, modelAPI } from '../api'

const { t, locale } = useI18n({ useScope: 'global' })

const selectedModel = ref('')

const models = computed(() => [
  { id: 1, name: t('quality.model1') },
  { id: 2, name: t('quality.model2') },
  { id: 3, name: t('quality.model3') },
  { id: 4, name: t('quality.model4') }
])

const checkTypes = ref([
  {
    key: 'zebra',
    icon: Grid,
    titleKey: 'quality.zebraAnalysis',
    descKey: 'quality.zebraAnalysisDesc',
    status: 'completed',
    statusType: 'success',
    progress: 100,
    score: 92
  },
  {
    key: 'highlight',
    icon: Sunny,
    titleKey: 'quality.highlightAnalysis',
    descKey: 'quality.highlightAnalysisDesc',
    status: 'running',
    statusType: 'primary',
    progress: 65,
    score: null
  },
  {
    key: 'curvature',
    icon: TrendCharts,
    titleKey: 'quality.curvatureAnalysis',
    descKey: 'quality.curvatureAnalysisDesc',
    status: 'not-started',
    statusType: 'info',
    progress: 0,
    score: null
  }
])

const checkStatusText = (status) => {
  const keys = {
    completed: 'quality.statusCompleted',
    running: 'quality.statusRunning',
    'not-started': 'quality.statusNotStarted'
  }
  return keys[status] ? t(keys[status]) : status
}

const recentReports = computed(() => [
  { id: 'R-001', modelName: t('quality.model1'), checkType: t('quality.fullAnalysis'), score: 94, passed: true, date: '2026-07-12 14:30' },
  { id: 'R-002', modelName: t('quality.model2'), checkType: t('quality.zebraAnalysis'), score: 88, passed: true, date: '2026-07-11 10:15' },
  { id: 'R-003', modelName: t('quality.model3'), checkType: t('quality.curvatureAnalysis'), score: 76, passed: false, date: '2026-07-10 16:45' },
  { id: 'R-004', modelName: t('quality.model4'), checkType: t('quality.fullAnalysis'), score: 91, passed: true, date: '2026-07-09 09:20' },
  { id: 'R-005', modelName: t('quality.model1'), checkType: t('quality.highlightAnalysis'), score: 85, passed: true, date: '2026-07-08 11:50' }
])

const startCheck = async () => {
  if (!selectedModel.value) {
    ElMessage.warning(t('quality.selectModelFirst'))
    return
  }
  try {
    checkTypes.value[2].status = 'running'
    checkTypes.value[2].statusType = 'primary'
    checkTypes.value[2].progress = 0

    const response = await qualityAPI.check({
      model_id: selectedModel.value,
      checks: ['zebra', 'highlight', 'curvature']
    })
    const result = response.data

    checkTypes.value[2].status = 'completed'
    checkTypes.value[2].statusType = 'success'
    checkTypes.value[2].progress = 100
    checkTypes.value[2].score = result.score || 95

    ElMessage.success(t('quality.checkCompleted'))
  } catch (error) {
    ElMessage.error(t('quality.checkFailed'))
    checkTypes.value[2].status = 'not-started'
    checkTypes.value[2].statusType = 'info'
  }
}

const viewReport = (row) => {
  ElMessage.info(t('quality.viewingReport', { id: row.id }))
}

// ---- G2 曲率连续性检测 ----
const g2Loading = ref(false)
const g2Result = ref({
  overall_g2_pass: null,
  n_pairs: 0, n_pass: 0, n_fail: 0, n_no_data: 0,
  pass_rate: 0,
  pairs: [],
})

const runG2Check = async () => {
  if (!selectedModel.value) {
    ElMessage.warning(t('quality.selectModelFirst'))
    return
  }
  g2Loading.value = true
  try {
    const res = await qualityAPI.g2Check({ model_id: selectedModel.value })
    const data = res.data
    if (data.error) {
      ElMessage.warning(data.error)
      g2Result.value = { overall_g2_pass: null, pairs: [] }
      return
    }
    g2Result.value = data
    if (data.overall_g2_pass === true) {
      ElMessage.success(`${t('quality.g2Check')}：${t('quality.g2Pass')}`)
    } else if (data.overall_g2_pass === false) {
      ElMessage.warning(`${t('quality.g2Check')}：${t('quality.g2Fail')}（${data.n_pass}/${data.n_pass + data.n_fail} 通过）`)
    }
  } catch (err) {
    ElMessage.error(t('quality.checkFailed'))
  } finally {
    g2Loading.value = false
  }
}
</script>

<style scoped>
.quality-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.model-select {
  width: 220px;
}

.model-select :deep(.el-select__wrapper) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: none;
}

.model-select :deep(.el-select__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.model-select :deep(.el-select__wrapper.is-focused) {
  border-color: var(--accent);
}

.model-select :deep(.el-select__placeholder) {
  color: var(--text-faint);
}

.model-select :deep(.el-select__input-inner) {
  color: var(--text-secondary);
}

.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
  font-weight: 600;
}

.btn-primary:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--bg-primary);
}

.check-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.check-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.check-card :deep(.el-card__body) {
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.check-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.check-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.check-icon.zebra {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.check-icon.highlight {
  background: rgba(250, 204, 21, 0.15);
  color: #facc15;
}

.check-icon.curvature {
  background: rgba(244, 114, 182, 0.15);
  color: #f472b6;
}

.check-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.check-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
  flex: 1;
}

.check-progress {
  padding-top: 4px;
}

.check-score {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.score-label {
  font-size: 13px;
  color: var(--text-muted);
}

.score-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}

.reports-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.reports-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 20px;
}

.reports-card :deep(.el-card__body) {
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

.reports-card :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: var(--hover-bg);
  background: transparent;
  color: var(--text-secondary);
}

.reports-card :deep(.el-table th) {
  background: transparent;
  color: var(--text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border-color);
}

.reports-card :deep(.el-table td) {
  border-bottom: 1px solid var(--border-color);
}

.score-pass {
  color: var(--accent);
  font-weight: 600;
}

.score-fail {
  color: #f87171;
  font-weight: 600;
}

/* ---- G2 检测 ---- */
.check-icon.g2 {
  background: rgba(167, 139, 250, 0.15);
  color: #a78bfa;
}

.g2-actions {
  padding-top: 4px;
}

.g2-detail-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.g2-detail-card :deep(.el-card__header) {
  border-bottom: 1px solid var(--border-color);
  padding: 16px 20px;
}

.g2-detail-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.g2-standard {
  font-size: 12px;
  color: var(--text-faint);
}

.g2-na {
  color: var(--text-faint);
}

.g2-detail-card :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: var(--hover-bg);
  background: transparent;
  color: var(--text-secondary);
}

.g2-detail-card :deep(.el-table th) {
  background: transparent;
  color: var(--text-muted);
  font-weight: 500;
  border-bottom: 1px solid var(--border-color);
}

.g2-detail-card :deep(.el-table td) {
  border-bottom: 1px solid var(--border-color);
}
</style>
