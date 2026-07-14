<template>
  <div class="dashboard">
    <div class="stats-grid">
      <el-card class="stat-card" v-for="stat in statCards" :key="stat.key">
        <div class="stat-icon" :class="stat.key">
          <el-icon :size="24"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </el-card>
    </div>

    <div class="content-grid">
      <el-card class="content-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">Recent Projects</span>
            <el-button type="primary" text @click="$router.push('/projects')">View All</el-button>
          </div>
        </template>
        <el-table :data="recentProjects" style="width: 100%" :row-style="{ background: 'transparent' }">
          <el-table-column prop="name" label="Project Name" />
          <el-table-column prop="status" label="Status" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" effect="dark" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="Created" width="160" />
        </el-table>
      </el-card>

      <el-card class="content-card">
        <template #header>
          <span class="card-title">Workflow Status</span>
        </template>
        <div class="workflow-list">
          <div class="workflow-item" v-for="item in workflowItems" :key="item.id">
            <div class="workflow-header">
              <span class="workflow-name">{{ item.name }}</span>
              <span class="workflow-percent">{{ item.progress }}%</span>
            </div>
            <el-progress :percentage="item.progress" :stroke-width="8" :show-text="false" :color="'#4ade80'" />
            <div class="workflow-status">
              <span class="status-dot" :class="item.status"></span>
              <span class="status-text">{{ item.statusText }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { FolderOpened, Picture, CircleCheck, Download } from '@element-plus/icons-vue'

const statCards = [
  { key: 'projects', icon: FolderOpened, value: '24', label: 'Projects' },
  { key: 'models', icon: Picture, value: '156', label: 'Models' },
  { key: 'quality', icon: CircleCheck, value: '94.2%', label: 'Quality Score' },
  { key: 'exported', icon: Download, value: '89', label: 'Exported Files' }
]

const recentProjects = [
  { id: 1, name: 'EV-Sedan Concept', status: 'Active', createdAt: '2026-07-10' },
  { id: 2, name: 'SUV-A Platform', status: 'Completed', createdAt: '2026-07-08' },
  { id: 3, name: 'Sports Coupe V2', status: 'Active', createdAt: '2026-07-05' },
  { id: 4, name: 'Hatchback Design', status: 'Draft', createdAt: '2026-07-02' },
  { id: 5, name: 'Crossover Study', status: 'Completed', createdAt: '2026-06-28' }
]

const workflowItems = [
  { id: 1, name: 'EV-Sedan Surface Generation', progress: 75, status: 'running', statusText: 'In Progress' },
  { id: 2, name: 'SUV-A Quality Check', progress: 100, status: 'completed', statusText: 'Completed' },
  { id: 3, name: 'Sports Coupe Optimization', progress: 45, status: 'running', statusText: 'In Progress' },
  { id: 4, name: 'Hatchback Export', progress: 0, status: 'pending', statusText: 'Pending' }
]

const getStatusType = (status) => {
  const types = { Active: 'success', Completed: 'info', Draft: 'warning' }
  return types[status] || 'info'
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon.projects {
  background: rgba(74, 222, 128, 0.15);
  color: #4ade80;
}

.stat-icon.models {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.stat-icon.quality {
  background: rgba(250, 204, 21, 0.15);
  color: #facc15;
}

.stat-icon.exported {
  background: rgba(244, 114, 182, 0.15);
  color: #f472b6;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.content-card {
  background: #16161f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

.content-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding: 16px 20px;
}

.content-card :deep(.el-card__body) {
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

.content-card :deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.03);
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
}

.content-card :deep(.el-table th) {
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.content-card :deep(.el-table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workflow-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.workflow-percent {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.workflow-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.running {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
}

.status-dot.completed {
  background: #60a5fa;
}

.status-dot.pending {
  background: rgba(255, 255, 255, 0.3);
}

.status-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
