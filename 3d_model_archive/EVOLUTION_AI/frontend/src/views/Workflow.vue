<template>
  <div class="workflow-page">
    <div class="page-header">
      <div class="header-left">
        <h2>工作流管理</h2>
        <p>管理A级曲面开发工作流</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建工作流
      </el-button>
    </div>

    <div class="workflow-stages">
      <div class="stage-card">
        <div class="stage-icon">1</div>
        <div class="stage-info">
          <h3>概念探索</h3>
          <p>AI生成概念模型</p>
        </div>
        <el-progress :percentage="85" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">2</div>
        <div class="stage-info">
          <h3>拓扑优化</h3>
          <p>网格重构与优化</p>
        </div>
        <el-progress :percentage="60" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">3</div>
        <div class="stage-info">
          <h3>A级曲面</h3>
          <p>G2连续曲面构建</p>
        </div>
        <el-progress :percentage="40" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">4</div>
        <div class="stage-info">
          <h3>质量检查</h3>
          <p>F5/F6/F7检查</p>
        </div>
        <el-progress :percentage="20" :stroke-width="8" />
      </div>
      <div class="stage-card">
        <div class="stage-icon">5</div>
        <div class="stage-info">
          <h3>工程交接</h3>
          <p>数据交付</p>
        </div>
        <el-progress :percentage="5" :stroke-width="8" />
      </div>
    </div>

    <div class="workflow-list">
      <h3>工作流列表</h3>
      <el-table :data="workflows" style="width: 100%" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column prop="project_id" label="项目ID" width="80" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewWorkflow(row)">详情</el-button>
            <el-button type="success" link @click="runWorkflow(row)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showCreateDialog" title="创建工作流" width="500px">
      <el-form :model="workflowForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="workflowForm.name" placeholder="请输入工作流名称" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="workflowForm.type">
            <el-option label="拓扑优化" value="topology" />
            <el-option label="质量检查" value="quality" />
            <el-option label="数据交接" value="handover" />
            <el-option label="完整流程" value="full" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目" required>
          <el-select v-model="workflowForm.project_id" placeholder="请选择项目">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createWorkflow">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { workflowAPI, projectAPI } from '../services/api'

const workflows = ref([])
const projects = ref([])
const showCreateDialog = ref(false)

const workflowForm = ref({
  name: '',
  type: '',
  project_id: ''
})

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
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '已失败'
  }
  return texts[status] || status
}

const formatDateTime = (date) => {
  return new Date(date).toLocaleString('zh-CN')
}

const loadWorkflows = async () => {
  try {
    const response = await workflowAPI.list()
    workflows.value = response.data
  } catch (error) {
    console.error('Failed to load workflows:', error)
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

const createWorkflow = async () => {
  if (!workflowForm.value.name || !workflowForm.value.type || !workflowForm.value.project_id) {
    alert('请填写完整信息')
    return
  }

  try {
    await workflowAPI.create(workflowForm.value)
    showCreateDialog.value = false
    workflowForm.value = { name: '', type: '', project_id: '' }
    loadWorkflows()
    alert('工作流创建成功')
  } catch (error) {
    console.error('Failed to create workflow:', error)
    alert('工作流创建失败')
  }
}

const viewWorkflow = (workflow) => {
  alert(`工作流详情: ${workflow.name}`)
}

const runWorkflow = (workflow) => {
  alert(`执行工作流: ${workflow.name}`)
}

loadWorkflows()
loadProjects()
</script>

<style>
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
  grid-template-columns: repeat(5, 1fr);
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
</style>