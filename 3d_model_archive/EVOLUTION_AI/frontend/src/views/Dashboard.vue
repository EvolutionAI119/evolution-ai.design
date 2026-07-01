<template>
  <div class="dashboard">
    <div class="stats-grid">
      <el-card class="stat-card">
        <div class="stat-icon projects">
          <el-icon><FolderOpened /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.projects }}</div>
          <div class="stat-label">项目总数</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon models">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.models }}</div>
          <div class="stat-label">模型数量</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon reports">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.reports }}</div>
          <div class="stat-label">检查报告</div>
        </div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-icon quality">
          <el-icon><CheckCircle /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.qualityRate }}%</div>
          <div class="stat-label">合格率</div>
        </div>
      </el-card>
    </div>

    <div class="charts-grid">
      <el-card class="chart-card">
        <template #header>
          <span>项目状态分布</span>
        </template>
        <div ref="statusChart" class="chart"></div>
      </el-card>
      <el-card class="chart-card">
        <template #header>
          <span>质量评分趋势</span>
        </template>
        <div ref="scoreChart" class="chart"></div>
      </el-card>
    </div>

    <div class="bottom-grid">
      <el-card class="list-card">
        <template #header>
          <span>最近项目</span>
          <el-button type="text" @click="$router.push('/projects')">查看全部</el-button>
        </template>
        <el-table :data="recentProjects" style="width: 100%">
          <el-table-column prop="name" label="项目名称" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card class="list-card">
        <template #header>
          <span>待处理任务</span>
        </template>
        <el-timeline>
          <el-timeline-item
            v-for="task in pendingTasks"
            :key="task.id"
            :timestamp="task.time"
            placement="top"
          >
            <el-card size="small">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-desc">{{ task.description }}</div>
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
import { FolderOpened, Picture, Document, CheckCircle } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { projectAPI, modelAPI, qualityAPI } from '../services/api'

const stats = ref({
  projects: 0,
  models: 0,
  reports: 0,
  qualityRate: 0
})

const recentProjects = ref([])
const pendingTasks = ref([
  { id: 1, title: '拓扑优化任务', description: '处理GLB模型拓扑优化', progress: 65, time: '10分钟前' },
  { id: 2, title: '质量检查任务', description: '执行F5/F6/F7质量检查', progress: 40, time: '30分钟前' },
  { id: 3, title: '数据交接任务', description: '准备工程数据交付', progress: 20, time: '1小时前' }
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

const formatDate = (date) => {
  return new Date(date).toLocaleDateString('zh-CN')
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
          { value: 12, name: '进行中', itemStyle: { color: '#00d9ff' } },
          { value: 8, name: '待处理', itemStyle: { color: '#ffc107' } },
          { value: 15, name: '已完成', itemStyle: { color: '#00ff88' } },
          { value: 3, name: '已失败', itemStyle: { color: '#ff4757' } }
        ]
      }]
    })
  }

  if (scoreChart.value) {
    const chart = echarts.init(scoreChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
      yAxis: { type: 'value', max: 100 },
      series: [{
        name: '质量评分',
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

<style>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
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
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.chart-card { height: 300px; }
.chart { height: calc(100% - 50px); }

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.list-card { flex: 1; }

.task-title { font-weight: bold; margin-bottom: 5px; }
.task-desc { font-size: 12px; color: #999; margin-bottom: 10px; }
</style>