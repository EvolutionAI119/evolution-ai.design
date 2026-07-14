<template>
  <div class="quality-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">Quality Check</h2>
        <p class="page-subtitle">Comprehensive surface quality analysis and validation</p>
      </div>
      <div class="header-actions">
        <el-select v-model="selectedModel" placeholder="Select model" class="model-select">
          <el-option v-for="model in models" :key="model.id" :label="model.name" :value="model.id" />
        </el-select>
        <el-button type="primary" class="btn-primary" :disabled="!selectedModel" @click="startCheck">
          <el-icon><VideoPlay /></el-icon>
          <span>Start Check</span>
        </el-button>
      </div>
    </div>

    <div class="check-cards">
      <el-card class="check-card" v-for="check in checkTypes" :key="check.key">
        <div class="check-header">
          <div class="check-icon" :class="check.key">
            <el-icon :size="24"><component :is="check.icon" /></el-icon>
          </div>
          <el-tag :type="check.statusType" effect="dark" size="small">{{ check.statusText }}</el-tag>
        </div>
        <h3 class="check-title">{{ check.title }}</h3>
        <p class="check-desc">{{ check.description }}</p>
        <div class="check-progress" v-if="check.status === 'running'">
          <el-progress :percentage="check.progress" :stroke-width="6" :show-text="false" :color="'#4ade80'" />
        </div>
        <div class="check-score" v-if="check.status === 'completed'">
          <span class="score-label">Score</span>
          <span class="score-value">{{ check.score }}/100</span>
        </div>
      </el-card>
    </div>

    <el-card class="reports-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">Recent Reports</span>
          <el-button type="primary" text>View All</el-button>
        </div>
      </template>
      <el-table :data="recentReports" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="modelName" label="Model" />
        <el-table-column prop="checkType" label="Check Type" width="140" />
        <el-table-column prop="score" label="Score" width="120">
          <template #default="{ row }">
            <span :class="row.score >= 80 ? 'score-pass' : 'score-fail'">{{ row.score }}/100</span>
          </template>
        </el-table-column>
        <el-table-column prop="result" label="Result" width="100">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'" effect="dark" size="small">{{ row.passed ? 'Pass' : 'Fail' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="Date" width="160" />
        <el-table-column label="Actions" width="100">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewReport(row)">View</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, Grid, Sunny, TrendCharts } from '@element-plus/icons-vue'

const selectedModel = ref('')

const models = ref([
  { id: 1, name: 'EV-Sedan Concept v1' },
  { id: 2, name: 'SUV-A Platform' },
  { id: 3, name: 'Sports Coupe V2' },
  { id: 4, name: 'Hatchback Design' }
])

const checkTypes = reactive([
  {
    key: 'zebra',
    icon: Grid,
    title: 'Zebra Analysis',
    description: 'Analyze surface continuity and reflection lines using zebra striping technique.',
    status: 'completed',
    statusType: 'success',
    statusText: 'Completed',
    progress: 100,
    score: 92
  },
  {
    key: 'highlight',
    icon: Sunny,
    title: 'Highlight Analysis',
    description: 'Evaluate highlight reflections and surface smoothness across curvature transitions.',
    status: 'running',
    statusType: 'primary',
    statusText: 'Running',
    progress: 65,
    score: null
  },
  {
    key: 'curvature',
    icon: TrendCharts,
    title: 'Curvature Analysis',
    description: 'Detailed curvature comb analysis for precise surface quality measurement.',
    status: 'not-started',
    statusType: 'info',
    statusText: 'Not Started',
    progress: 0,
    score: null
  }
])

const recentReports = ref([
  { id: 'R-001', modelName: 'EV-Sedan Concept v1', checkType: 'Full Analysis', score: 94, passed: true, date: '2026-07-12 14:30' },
  { id: 'R-002', modelName: 'SUV-A Platform', checkType: 'Zebra Analysis', score: 88, passed: true, date: '2026-07-11 10:15' },
  { id: 'R-003', modelName: 'Sports Coupe V2', checkType: 'Curvature Analysis', score: 76, passed: false, date: '2026-07-10 16:45' },
  { id: 'R-004', modelName: 'Hatchback Design', checkType: 'Full Analysis', score: 91, passed: true, date: '2026-07-09 09:20' },
  { id: 'R-005', modelName: 'EV-Sedan Concept v1', checkType: 'Highlight Analysis', score: 85, passed: true, date: '2026-07-08 11:50' }
])

const startCheck = () => {
  if (!selectedModel.value) {
    ElMessage.warning('Please select a model first')
    return
  }
  ElMessage.success('Quality check started')
  checkTypes[2].status = 'running'
  checkTypes[2].statusType = 'primary'
  checkTypes[2].statusText = 'Running'
  checkTypes[2].progress = 0
}

const viewReport = (row) => {
  ElMessage.info(`Viewing report ${row.id}`)
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
  color: #fff;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
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
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  box-shadow: none;
}

.model-select :deep(.el-select__wrapper:hover) {
  border-color: rgba(74, 222, 128, 0.3);
}

.model-select :deep(.el-select__wrapper.is-focused) {
  border-color: #4ade80;
}

.model-select :deep(.el-select__placeholder) {
  color: rgba(255, 255, 255, 0.35);
}

.model-select :deep(.el-select__input-inner) {
  color: rgba(255, 255, 255, 0.8);
}

.btn-primary {
  background: #4ade80;
  border-color: #4ade80;
  color: #0a0a0f;
  font-weight: 600;
}

.btn-primary:hover {
  background: #22c55e;
  border-color: #22c55e;
  color: #0a0a0f;
}

.check-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.check-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
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
  color: #fff;
}

.check-desc {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
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
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.score-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.score-value {
  font-size: 18px;
  font-weight: 700;
  color: #4ade80;
}

.reports-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.reports-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
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
  color: #fff;
}

.reports-card :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.03);
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
}

.reports-card :deep(.el-table th) {
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.reports-card :deep(.el-table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.score-pass {
  color: #4ade80;
  font-weight: 600;
}

.score-fail {
  color: #f87171;
  font-weight: 600;
}
</style>
