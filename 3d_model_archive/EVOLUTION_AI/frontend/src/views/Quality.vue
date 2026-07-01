<template>
  <div class="quality-page">
    <div class="page-header">
      <div class="header-left">
        <h2>质量检查</h2>
        <p>执行A级曲面质量检查（F5/F6/F7）</p>
      </div>
      <el-button type="primary" @click="showCheckDialog = true">
        <el-icon><CheckCircle /></el-icon>
        开始检查
      </el-button>
    </div>

    <div class="check-types">
      <div class="check-card zebra">
        <div class="check-icon">F5</div>
        <div class="check-info">
          <h3>斑马纹检查</h3>
          <p>检查曲面连续性，识别斑马纹断裂区域</p>
        </div>
      </div>
      <div class="check-card highlight">
        <div class="check-icon">F6</div>
        <div class="check-info">
          <h3>高光线检查</h3>
          <p>检查曲面光顺度，评估高光质量</p>
        </div>
      </div>
      <div class="check-card curvature">
        <div class="check-icon">F7</div>
        <div class="check-info">
          <h3>曲率梳检查</h3>
          <p>检查曲率变化，定位曲率突变点</p>
        </div>
      </div>
    </div>

    <div class="recent-reports">
      <h3>最近检查报告</h3>
      <el-table :data="recentReports" style="width: 100%" stripe>
        <el-table-column prop="id" label="报告ID" width="80" />
        <el-table-column prop="model_id" label="模型ID" width="80" />
        <el-table-column prop="overall_score" label="评分" width="100">
          <template #default="{ row }">
            <span :class="row.overall_score >= 80 ? 'score-pass' : 'score-fail'">
              {{ row.overall_score }}/100
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="passed" label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.passed ? 'success' : 'danger'">
              {{ row.passed ? '通过' : '未通过' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="检查时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewReport(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showCheckDialog" title="执行质量检查" width="500px">
      <el-form :model="checkForm" label-width="80px">
        <el-form-item label="选择模型" required>
          <el-select v-model="checkForm.model_id" placeholder="请选择模型">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="生成报告">
          <el-checkbox v-model="checkForm.generate_html">生成HTML报告</el-checkbox>
          <el-checkbox v-model="checkForm.generate_json">生成JSON报告</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCheckDialog = false">取消</el-button>
        <el-button type="primary" @click="runCheck">开始检查</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReportDialog" title="质量检查报告" width="800px">
      <div v-if="currentReport" class="report-content">
        <div class="report-header">
          <div class="score-display" :class="currentReport.passed ? 'passed' : 'failed'">
            {{ currentReport.overall_score }}/100
          </div>
          <div class="result-text">{{ currentReport.passed ? '✓ 检查通过' : '✗ 检查未通过' }}</div>
        </div>
        <el-divider />
        <h4>检查项详情</h4>
        <el-table :data="reportDetails" style="width: 100%">
          <el-table-column prop="check_type" label="检查类型" />
          <el-table-column prop="score" label="评分" />
          <el-table-column prop="passed" label="结果">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'">
                {{ row.passed ? '通过' : '未通过' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="currentReport.report_path" class="report-links">
          <el-button type="success" @click="downloadReport(currentReport.report_path)">下载报告</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CheckCircle, Search } from '@element-plus/icons-vue'
import { qualityAPI, modelAPI } from '../services/api'

const models = ref([])
const recentReports = ref([])
const showCheckDialog = ref(false)
const showReportDialog = ref(false)
const currentReport = ref(null)

const checkForm = ref({
  model_id: '',
  generate_html: true,
  generate_json: true
})

const formatDateTime = (date) => {
  return new Date(date).toLocaleString('zh-CN')
}

const reportDetails = ref([])

const loadModels = async () => {
  try {
    const response = await modelAPI.list()
    models.value = response.data
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const loadReports = async () => {
  try {
    const response = await qualityAPI.list()
    recentReports.value = response.data.slice(0, 10)
  } catch (error) {
    console.error('Failed to load reports:', error)
  }
}

const runCheck = async () => {
  if (!checkForm.value.model_id) {
    alert('请选择模型')
    return
  }

  try {
    showCheckDialog.value = false
    const response = await qualityAPI.check(checkForm.value)
    currentReport.value = response.data
    reportDetails.value = response.data.report_data ? JSON.parse(response.data.report_data).check_results || [] : []
    showReportDialog.value = true
    loadReports()
  } catch (error) {
    console.error('Quality check failed:', error)
    alert('质量检查失败')
  }
}

const viewReport = async (report) => {
  try {
    const response = await qualityAPI.get(report.id)
    currentReport.value = response.data
    reportDetails.value = response.data.report_data ? JSON.parse(response.data.report_data).check_results || [] : []
    showReportDialog.value = true
  } catch (error) {
    console.error('Failed to load report:', error)
  }
}

const downloadReport = (path) => {
  window.open(`/api/v1/reports/${path.split('/').pop()}`)
}

loadModels()
loadReports()
</script>

<style>
.quality-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.check-types {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.check-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 25px;
  border-radius: 12px;
}

.check-card.zebra { background: linear-gradient(135deg, rgba(0, 217, 255, 0.1), rgba(0, 153, 204, 0.1)); border: 1px solid rgba(0, 217, 255, 0.3); }
.check-card.highlight { background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(238, 90, 90, 0.1)); border: 1px solid rgba(255, 107, 107, 0.3); }
.check-card.curvature { background: linear-gradient(135deg, rgba(255, 217, 61, 0.1), rgba(240, 196, 25, 0.1)); border: 1px solid rgba(255, 217, 61, 0.3); }

.check-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
}

.check-card.zebra .check-icon { background: linear-gradient(135deg, #00d9ff, #0099cc); color: white; }
.check-card.highlight .check-icon { background: linear-gradient(135deg, #ff6b6b, #ee5a5a); color: white; }
.check-card.curvature .check-icon { background: linear-gradient(135deg, #ffd93d, #f0c419); color: white; }

.check-info h3 { margin: 0; font-size: 18px; }
.check-info p { margin: 5px 0 0 0; font-size: 14px; color: #666; }

.recent-reports h3 { margin-bottom: 15px; }

.score-pass { color: #00ff88; font-weight: bold; }
.score-fail { color: #ff4757; font-weight: bold; }

.report-content { padding: 10px; }

.report-header { text-align: center; margin-bottom: 20px; }

.score-display {
  font-size: 64px;
  font-weight: bold;
  margin-bottom: 10px;
}

.score-display.passed { color: #00ff88; }
.score-display.failed { color: #ff4757; }

.result-text { font-size: 20px; font-weight: bold; }

.report-links { margin-top: 20px; text-align: center; }
</style>