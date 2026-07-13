<template>
  <div class="dashboard">
    <div class="stats-grid">
      <el-card class="stat-card">
        <div class="stat-icon projects">
          <el-icon><FolderOpened /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.projects }}</div>
          <div class="stat-label">{{ $t('dashboard.projects') }}</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon models">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.models }}</div>
          <div class="stat-label">{{ $t('dashboard.models') }}</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon reports">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.reports }}</div>
          <div class="stat-label">{{ $t('dashboard.reports') }}</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon quality">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.qualityRate }}%</div>
          <div class="stat-label">{{ $t('dashboard.qualityRate') }}</div>
        </div>
      </el-card>
    </div>

    <div class="charts-grid">
      <el-card class="chart-card">
        <template #header>
          <span>{{ $t('dashboard.projectStatus') }}</span>
        </template>
        <div ref="statusChart" class="chart"></div>
      </el-card>
      <el-card class="chart-card">
        <template #header>
          <span>{{ $t('dashboard.qualityTrend') }}</span>
        </template>
        <div ref="scoreChart" class="chart"></div>
      </el-card>
    </div>

    <div class="bottom-grid">
      <el-card class="list-card">
        <template #header>
          <span>{{ $t('dashboard.recentProjects') }}</span>
          <el-button type="text" @click="$router.push('/projects')">{{ $t('dashboard.viewAll') }}</el-button>
        </template>
        <el-table :data="recentProjects" style="width: 100%">
          <el-table-column prop="name" :label="$t('dashboard.projectName')" />
          <el-table-column prop="status" :label="$t('dashboard.status')">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="$t('dashboard.createdAt')">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card class="list-card">
        <template #header>
          <span>{{ $t('dashboard.pendingTasks') }}</span>
        </template>
        <el-timeline>
          <el-timeline-item
            v-for="task in pendingTasks"
            :key="task.id"
            :timestamp="task.time"
            placement="top"
          >
            <el-card size="small">
              <div class="task-title">{{ $t(task.title) }}</div>
              <div class="task-desc">{{ $t(task.description) }}</div>
              <el-progress :percentage="task.progress" :stroke-width="6" />
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { FolderOpened, Picture, Document, CircleCheck } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { projectAPI, modelAPI, qualityAPI } from '../services/api'

const { t } = useI18n()

const stats = ref({
  projects: 0,
  models: 0,
  reports: 0,
  qualityRate: 0
})

const recentProjects = ref([])
const pendingTasks = ref([
  { id: 1, title: 'dashboard.topology', description: 'dashboard.topologyDesc', progress: 65, time: '10分钟前' },
  { id: 2, title: 'dashboard.quality', description: 'dashboard.qualityDesc', progress: 40, time: '30分钟前' },
  { id: 3, title: 'dashboard.handover', description: 'dashboard.handoverDesc', progress: 20, time: '1小时前' }
])

const statusChart = ref(null)
const scoreChart = ref(null)

const getStatusType = (status) => {
  const types = {
    active: 'success',
    pending: 'warning',
    completed: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    active: t('dashboard.inProgress'),
    pending: t('dashboard.pending'),
    completed: t('dashboard.completed'),
    failed: t('dashboard.failed')
  }
  return texts[status] || status
}

const formatDate = (date) => {
  return new Date(date).toLocaleDateString(t('common.chinese') === '中文' ? 'zh-CN' : 'en-US')
}

const initCharts = () => {
  if (statusChart.value) {
    const chart = echarts.init(statusChart.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10 },
        data: [
          { value: 12, name: t('dashboard.inProgress'), itemStyle: { color: '#00d9ff' } },
          { value: 8, name: t('dashboard.pending'), itemStyle: { color: '#ffc107' } },
          { value: 15, name: t('dashboard.completed'), itemStyle: { color: '#00ff88' } },
          { value: 3, name: t('dashboard.failed'), itemStyle: { color: '#ff4757' } }
        ]
      }]
    })
  }

  if (scoreChart.value) {
    const chart = echarts.init(scoreChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: [t('dashboard.monday'), t('dashboard.tuesday'), t('dashboard.wednesday'), t('dashboard.thursday'), t('dashboard.friday'), t('dashboard.saturday'), t('dashboard.sunday')] },
      yAxis: { type: 'value', max: 100 },
      series: [{
        name: t('dashboard.qualityScore'),
        type: 'line',
        smooth: true,
        data: [85, 88, 92, 89, 95, 91, 93],
        lineStyle: { color: '#00d9ff', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 217, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 217, 255, 0.05)' }
          ])
        }
      }]
    })
  }
}

const loadData = async () => {
  try {
    const [projects, models, reports] = await Promise.all([
      projectAPI.list(),
      modelAPI.list(),
      qualityAPI.list()
    ])

    stats.value.projects = projects.data.length
    stats.value.models = models.data.length
    stats.value.reports = reports.data.length
    stats.value.qualityRate = reports.data.length > 0
      ? Math.round(reports.data.filter(r => r.passed).length / reports.data.length * 100)
      : 0

    recentProjects.value = projects.data.slice(0, 5)
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadData()
  initCharts()

  window.addEventListener('resize', () => {
    if (statusChart.value) echarts.init(statusChart.value).resize()
    if (scoreChart.value) echarts.init(scoreChart.value).resize()
  })
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.projects { background: linear-gradient(135deg, #00d9ff, #0099cc); color: white; }
.stat-icon.models { background: linear-gradient(135deg, #ff6b6b, #ee5a5a); color: white; }
.stat-icon.reports { background: linear-gradient(135deg, #ffd93d, #f0c419); color: white; }
.stat-icon.quality { background: linear-gradient(135deg, #6bcb77, #4daf50); color: white; }

.stat-info { flex: 1; }
.stat-value { font-size: 32px; font-weight: bold; color: #333; }
.stat-label { font-size: 14px; color: #999; margin-top: 5px; }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.chart-card { min-height: 280px; height: 300px; }
.chart { height: calc(100% - 50px); }

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.list-card { flex: 1; }

.task-title { font-weight: bold; margin-bottom: 5px; }
.task-desc { font-size: 12px; color: #999; margin-bottom: 10px; }
</style>