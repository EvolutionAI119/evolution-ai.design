<template>
  <div class="reports-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('reports.title') }}</h2>
        <p>{{ $t('reports.subtitle') }}</p>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterProject" :placeholder="$t('reports.projectFilter')">
        <el-option :label="$t('projects.all')" value="" />
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterStatus" :placeholder="$t('reports.resultFilter')">
        <el-option :label="$t('projects.all')" value="" />
        <el-option :label="$t('reports.passed')" :value="true" />
        <el-option :label="$t('reports.failed')" :value="false" />
      </el-select>
      <el-input
        v-model="searchQuery"
        :placeholder="$t('reports.search')"
        clearable
        prefix-icon="Search"
      />
    </div>

    <div class="reports-grid">
      <el-card
        v-for="report in filteredReports"
        :key="report.id"
        class="report-card"
        :class="report.passed ? 'passed' : 'failed'"
      >
        <div class="report-header">
          <div class="report-id">{{ $t('reports.report') }} #{{ report.id }}</div>
          <el-tag :type="report.passed ? 'success' : 'danger'">
            {{ report.passed ? $t('reports.passed') : $t('reports.failed') }}
          </el-tag>
        </div>
        <div class="report-score">
          <span class="score">{{ report.overall_score }}</span>
          <span class="max">/100</span>
        </div>
        <div class="report-info">
          <div class="info-item">
            <span class="label">{{ $t('reports.modelId') }}:</span>
            <span class="value">{{ report.model_id }}</span>
          </div>
          <div class="info-item">
            <span class="label">{{ $t('reports.projectId') }}:</span>
            <span class="value">{{ report.project_id }}</span>
          </div>
          <div class="info-item">
            <span class="label">{{ $t('reports.checkTime') }}:</span>
            <span class="value">{{ formatDateTime(report.created_at) }}</span>
          </div>
        </div>
        <div class="report-actions">
          <el-button type="primary" @click="viewReport(report)">{{ $t('reports.viewDetail') }}</el-button>
          <el-button @click="downloadReport(report)">{{ $t('reports.downloadReport') }}</el-button>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="showReportDialog" :title="$t('reports.reportDetail')" width="900px">
      <div v-if="currentReport" class="report-detail">
        <div class="detail-header">
          <div class="detail-score" :class="currentReport.passed ? 'passed' : 'failed'">
            {{ currentReport.overall_score }}/100
          </div>
          <div class="detail-badge">
            <el-tag :type="currentReport.passed ? 'success' : 'danger'" size="large">
              {{ currentReport.passed ? $t('reports.passText') : $t('reports.failText') }}
            </el-tag>
          </div>
        </div>
        <el-divider />
        <div class="detail-content">
          <h4>{{ $t('reports.checkSummary') }}</h4>
          <div class="summary-grid">
            <div class="summary-card">
              <div class="summary-value">{{ getTotalChecks() }}</div>
              <div class="summary-label">{{ $t('reports.totalChecks') }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-value">{{ getPassedChecks() }}</div>
              <div class="summary-label">{{ $t('reports.passedChecks') }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-value">{{ getFailedChecks() }}</div>
              <div class="summary-label">{{ $t('reports.failedChecks') }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-value">{{ getTotalIssues() }}</div>
              <div class="summary-label">{{ $t('reports.totalIssues') }}</div>
            </div>
          </div>
          <h4>{{ $t('reports.detailedResults') }}</h4>
          <div class="check-results">
            <div
              v-for="(result, index) in getCheckResults()"
              :key="index"
              class="check-result"
              :class="result.passed ? 'passed' : 'failed'"
            >
              <div class="result-header">
                <span class="result-name">{{ result.check_type }}</span>
                <span class="result-score">{{ result.score }}/100</span>
              </div>
              <div v-if="result.issues && result.issues.length > 0" class="result-issues">
                <h5>{{ $t('reports.foundIssues') }}:</h5>
                <el-table :data="result.issues" style="width: 100%">
                  <el-table-column prop="location" :label="$t('reports.location')" />
                  <el-table-column prop="issue_type" :label="$t('reports.issueType')" />
                  <el-table-column prop="severity" :label="$t('reports.severity')">
                    <template #default="{ row }">
                      <el-tag :type="getSeverityType(row.severity)" size="small">
                        {{ $t(`reports.${row.severity}`) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="suggestion" :label="$t('reports.suggestion')" show-overflow-tooltip />
                </el-table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { qualityAPI, projectAPI } from '../services/api'

const { t } = useI18n()

const reports = ref([])
const projects = ref([])
const filterProject = ref('')
const filterStatus = ref('')
const searchQuery = ref('')
const showReportDialog = ref(false)
const currentReport = ref(null)

const filteredReports = computed(() => {
  return reports.value.filter(report => {
    const matchProject = !filterProject.value || report.project_id === filterProject.value
    const matchStatus = filterStatus.value === '' || report.passed === filterStatus.value
    return matchProject && matchStatus
  })
})

const formatDateTime = (date) => {
  return new Date(date).toLocaleString()
}

const getSeverityType = (severity) => {
  const types = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'success'
  }
  return types[severity] || 'info'
}

const loadReports = async () => {
  try {
    const response = await qualityAPI.list()
    reports.value = response.data
  } catch (error) {
    console.error('Failed to load reports:', error)
  }
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list()
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const viewReport = async (report) => {
  try {
    const response = await qualityAPI.get(report.id)
    currentReport.value = response.data
    showReportDialog.value = true
  } catch (error) {
    console.error('Failed to load report:', error)
  }
}

const downloadReport = (report) => {
  if (report.report_path) {
    window.open(`/api/v1/reports/${report.report_path.split('/').pop()}`)
  }
}

const getCheckResults = () => {
  if (!currentReport.value?.report_data) return []
  try {
    const data = JSON.parse(currentReport.value.report_data)
    return data.check_results || []
  } catch {
    return []
  }
}

const getTotalChecks = () => {
  return getCheckResults().length
}

const getPassedChecks = () => {
  return getCheckResults().filter(r => r.passed).length
}

const getFailedChecks = () => {
  return getCheckResults().filter(r => !r.passed).length
}

const getTotalIssues = () => {
  return getCheckResults().reduce((sum, r) => sum + (r.issues?.length || 0), 0)
}

loadReports()
loadProjects()
</script>

<style>
.reports-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.report-card {
  padding: 20px;
  border-left: 4px solid;
}

.report-card.passed { border-color: #00ff88; }
.report-card.failed { border-color: #ff4757; }

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.report-id { font-weight: bold; }

.report-score {
  text-align: center;
  margin-bottom: 15px;
}

.report-score .score {
  font-size: 48px;
  font-weight: bold;
  color: #333;
}

.report-score .max { font-size: 24px; color: #999; }

.report-info { margin-bottom: 15px; }

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.info-item .label { color: #999; }
.info-item .value { font-weight: bold; }

.report-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.report-detail { padding: 10px; }

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.detail-score {
  font-size: 72px;
  font-weight: bold;
}

.detail-score.passed { color: #00ff88; }
.detail-score.failed { color: #ff4757; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.summary-card {
  text-align: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.summary-value { font-size: 28px; font-weight: bold; color: #007bff; }
.summary-label { font-size: 14px; color: #666; margin-top: 5px; }

.check-results {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.check-result {
  padding: 15px;
  border-radius: 8px;
}

.check-result.passed { background: rgba(0, 255, 136, 0.1); }
.check-result.failed { background: rgba(255, 71, 87, 0.1); }

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-name { font-weight: bold; }
.result-score { font-weight: bold; font-size: 18px; }
</style>