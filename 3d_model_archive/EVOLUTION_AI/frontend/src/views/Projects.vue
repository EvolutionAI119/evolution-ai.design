<template>
  <div class="projects-page">
    <div class="page-header">
      <div class="header-left">
        <h2>项目管理</h2>
        <p>管理您的A级曲面开发项目</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建项目
      </el-button>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterStatus" placeholder="状态筛选" style="width: 150px">
        <el-option label="全部" value="" />
        <el-option label="进行中" value="active" />
        <el-option label="待处理" value="pending" />
        <el-option label="已完成" value="completed" />
        <el-option label="已失败" value="failed" />
      </el-select>
      <el-input
        v-model="searchQuery"
        placeholder="搜索项目..."
        style="width: 250px"
        clearable
        prefix-icon="Search"
      />
    </div>

    <el-table :data="filteredProjects" style="width: 100%" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="120">
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
      <el-table-column prop="updated_at" label="更新时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="$router.push(`/projects/${row.id}`)">详情</el-button>
          <el-button type="success" link @click="editProject(row)">编辑</el-button>
          <el-button type="danger" link @click="deleteProject(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="projects.length"
      layout="total, prev, pager, next, jumper"
      :page-sizes="[10, 20, 50]"
    />

    <el-dialog v-model="showCreateDialog" title="新建项目" width="500px">
      <el-form :model="projectForm" label-width="80px">
        <el-form-item label="项目名称" required>
          <el-input v-model="projectForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="projectForm.description" type="textarea" placeholder="请输入项目描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createProject">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Plus, Search } from '@element-plus/icons-vue'
import { projectAPI } from '../services/api'

const projects = ref([])
const filterStatus = ref('')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const showCreateDialog = ref(false)

const projectForm = ref({
  name: '',
  description: ''
})

const filteredProjects = computed(() => {
  return projects.value.filter(project => {
    const matchStatus = !filterStatus.value || project.status === filterStatus.value
    const matchSearch = !searchQuery.value ||
      project.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchStatus && matchSearch
  })
})

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
    active: '进行中',
    pending: '待处理',
    completed: '已完成',
    failed: '已失败'
  }
  return texts[status] || status
}

const formatDateTime = (date) => {
  return new Date(date).toLocaleString('zh-CN')
}

const loadProjects = async () => {
  try {
    const response = await projectAPI.list(filterStatus.value || null)
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const createProject = async () => {
  if (!projectForm.value.name) {
    alert('请输入项目名称')
    return
  }

  try {
    await projectAPI.create(projectForm.value)
    showCreateDialog.value = false
    projectForm.value = { name: '', description: '' }
    await loadProjects()
    alert('项目创建成功')
  } catch (error) {
    console.error('Failed to create project:', error)
    alert('项目创建失败')
  }
}

const editProject = (project) => {
  projectForm.value = { name: project.name, description: project.description }
  showCreateDialog.value = true
}

const deleteProject = async (id) => {
  if (!confirm('确定要删除这个项目吗？')) return

  try {
    await projectAPI.delete(id)
    await loadProjects()
    alert('项目删除成功')
  } catch (error) {
    console.error('Failed to delete project:', error)
    alert('项目删除失败')
  }
}

loadProjects()
</script>

<style>
.projects-page { padding: 20px; }

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
</style>