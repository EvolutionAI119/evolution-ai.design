<template>
  <div class="workflow-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('workflow.title') }}</h2>
        <p>{{ $t('workflow.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        {{ $t('workflow.createWorkflow') }}
      </el-button>
    </div>

    <div class="workflow-stages">
      <div class="stage-card">
        <div class="stage-icon">1</div>
        <div class="stage-info">
          <h3>{{ $t('workflow.concept') }}</h3>
          <p>{{ $t('workflow.conceptDesc') }}</p>
        </div>
        <el-progress :percentage="85" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">2</div>
        <div class="stage-info">
          <h3>{{ $t('workflow.topology') }}</h3>
          <p>{{ $t('workflow.topologyDesc') }}</p>
        </div>
        <el-progress :percentage="60" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">3</div>
        <div class="stage-info">
          <h3>{{ $t('workflow.surface') }}</h3>
          <p>{{ $t('workflow.surfaceDesc') }}</p>
        </div>
        <el-progress :percentage="40" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">4</div>
        <div class="stage-info">
          <h3>{{ $t('workflow.quality') }}</h3>
          <p>{{ $t('workflow.qualityDesc') }}</p>
        </div>
        <el-progress :percentage="20" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">5</div>
        <div class="stage-info">
          <h3>{{ $t('workflow.handover') }}</h3>
          <p>{{ $t('workflow.handoverDesc') }}</p>
        </div>
        <el-progress :percentage="5" :stroke-width="8" />
      </div>
    </div>

    <div class="workflow-list">
      <h3>{{ $t('workflow.workflowList') }}</h3>
      <div class="workflow-grid">
        <el-card
          v-for="workflow in workflows"
          :key="workflow.id"
          class="workflow-card"
          @click="viewWorkflow(workflow)"
        >
          <div class="workflow-header">
            <div class="workflow-info">
              <h4 class="workflow-name">{{ workflow.name }}</h4>
              <div class="workflow-tags">
                <el-tag size="small" type="info">{{ getWorkflowTypeName(workflow.type) }}</el-tag>
                <el-tag size="small" type="info">{{ $t('workflow.projectId') }} {{ workflow.project_id }}</el-tag>
              </div>
            </div>
            <el-tag :type="getStatusType(workflow.status)" size="small" class="workflow-status">
              {{ getStatusText(workflow.status) }}
            </el-tag>
          </div>
          <div class="workflow-meta">
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ formatDateTime(workflow.created_at) }}
            </span>
          </div>
          <div class="workflow-actions">
            <el-button type="primary" size="small" @click.stop="viewWorkflow(workflow)">
              <el-icon><View /></el-icon>
              {{ $t('workflow.detail') }}
            </el-button>
            <el-button type="success" size="small" @click.stop="runWorkflow(workflow)">
              <el-icon><Play /></el-icon>
              {{ $t('workflow.execute') }}
            </el-button>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" :title="$t('workflow.createWorkflow')" width="500px">
      <el-form :model="workflowForm" label-width="80px">
        <el-form-item :label="$t('workflow.name')" required>
          <el-input v-model="workflowForm.name" :placeholder="$t('common.pleaseInput')" />
        </el-form-item>
        <el-form-item :label="$t('workflow.type')" required>
          <el-select v-model="workflowForm.type">
            <el-option :label="$t('workflow.topologyOpt')" value="topology" />
            <el-option :label="$t('workflow.qualityCheck')" value="quality" />
            <el-option :label="$t('workflow.dataHandover')" value="handover" />
            <el-option :label="$t('workflow.fullProcess')" value="full" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('models.project')" required>
          <el-select v-model="workflowForm.project_id" :placeholder="$t('common.pleaseSelect')">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="createWorkflow">{{ $t('common.create') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Clock, View, Play } from '@element-plus/icons-vue'
import { workflowAPI, projectAPI } from '../services/api'

const { t } = useI18n()

const workflows = ref([])
const projects = ref([])
const showCreateDialog = ref(false)

const workflowForm = ref({
  name: '',
  type: '',
  project_id: ''
})

const mockWorkflows = [
  { id: 1, name: t('workflow.mockName1'), type: 'full', project_id: 1, status: 'completed', created_at: '2026-06-28 14:30:00' },
  { id: 2, name: t('workflow.mockName2'), type: 'quality', project_id: 2, status: 'running', created_at: '2026-06-30 09:15:00' },
  { id: 3, name: t('workflow.mockName3'), type: 'topology', project_id: 3, status: 'pending', created_at: '2026-07-01 16:45:00' },
  { id: 4, name: t('workflow.mockName4'), type: 'handover', project_id: 1, status: 'completed', created_at: '2026-06-25 11:20:00' },
  { id: 5, name: t('workflow.mockName5'), type: 'full', project_id: 4, status: 'failed', created_at: '2026-06-29 08:00:00' },
  { id: 6, name: t('workflow.mockName6'), type: 'quality', project_id: 5, status: 'pending', created_at: '2026-07-02 10:30:00' }
]

const mockProjects = [
  { id: 1, name: t('workflow.mockProject1') },
  { id: 2, name: t('workflow.mockProject2') },
  { id: 3, name: t('workflow.mockProject3') },
  { id: 4, name: t('workflow.mockProject4') },
  { id: 5, name: t('workflow.mockProject5') }
]

const getWorkflowTypeName = (type) => {
  const typeMap = {
    full: t('workflow.typeFull'),
    quality: t('workflow.typeQuality'),
    topology: t('workflow.typeTopology'),
    handover: t('workflow.typeHandover')
  }
  return typeMap[type] || type
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    running: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: t('workflow.pending'),
    running: t('workflow.running'),
    completed: t('workflow.completed'),
    failed: t('workflow.failed')
  }
  return texts[status] || status
}

const formatDateTime = (date) => {
  return new Date(date).toLocaleString()
}

const loadWorkflows = async () => {
  try {
    const response = await workflowAPI.list()
    workflows.value = response.data || mockWorkflows
  } catch (error) {
    console.error('Failed to load workflows:', error)
    workflows.value = mockWorkflows
  }
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list()
    projects.value = response.data || mockProjects
  } catch (error) {
    console.error('Failed to load projects:', error)
    projects.value = mockProjects
  }
}

const createWorkflow = async () => {
  if (!workflowForm.value.name || !workflowForm.value.type || !workflowForm.value.project_id) {
    alert(t('workflow.enterInfo'))
    return
  }

  try {
    await workflowAPI.create(workflowForm.value)
    showCreateDialog.value = false
    workflowForm.value = { name: '', type: '', project_id: '' }
    loadWorkflows()
    alert(t('workflow.createSuccess'))
  } catch (error) {
    console.error('Failed to create workflow:', error)
    alert(t('workflow.createFailed'))
  }
}

const viewWorkflow = (workflow) => {
  alert(`${t('workflow.detail')}: ${workflow.name}`)
}

const runWorkflow = (workflow) => {
  alert(`${t('workflow.execute')}: ${workflow.name}`)
}

onMounted(() => {
  loadWorkflows()
  loadProjects()
})
</script>

<style scoped>
.workflow-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.workflow-stages {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.stage-card {
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stage-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, #00d9ff, #0099cc);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 10px;
}

.stage-info h3 { margin: 0; font-size: 16px; }
.stage-info p { margin: 5px 0 10px 0; font-size: 12px; color: #999; }

.workflow-list h3 { margin-bottom: 15px; }

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.workflow-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #e4e7ed;
}

.workflow-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
  border-color: #00d9ff;
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.workflow-info { flex: 1; }

.workflow-name {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.workflow-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.workflow-status { flex-shrink: 0; margin-left: 10px; }

.workflow-meta {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #909399;
}

.workflow-actions {
  display: flex;
  gap: 10px;
}
</style>