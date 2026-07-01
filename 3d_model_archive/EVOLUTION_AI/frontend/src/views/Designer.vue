<template>
  <div class="designer-page">
    <div class="page-header">
      <div class="header-left">
        <h2>模型生成</h2>
        <p>参数化车身生成与部件管理</p>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="generateCar">
          <el-icon><Play /></el-icon>
          生成完整车身
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="left-panel">
        <el-card class="panel-card">
          <template #header>
            <span>参数配置</span>
          </template>
          <el-tabs v-model="paramTab" type="border-card">
            <el-tab-pane label="整车尺寸" name="dimensions">
              <el-form :model="carParams" label-width="120px">
                <el-form-item label="整车长度 (mm)">
                  <el-input-number v-model="carParams.overall_length" :min="4000" :max="6000" />
                </el-form-item>
                <el-form-item label="整车宽度 (mm)">
                  <el-input-number v-model="carParams.overall_width" :min="1700" :max="2000" />
                </el-form-item>
                <el-form-item label="整车高度 (mm)">
                  <el-input-number v-model="carParams.overall_height" :min="1300" :max="1600" />
                </el-form-item>
                <el-form-item label="轴距 (mm)">
                  <el-input-number v-model="carParams.wheel_base" :min="2500" :max="3500" />
                </el-form-item>
              </el-form>
            </el-tab-pane>
            <el-tab-pane label="车身部件" name="components">
              <el-form :model="componentParams" label-width="120px">
                <el-form-item label="发动机盖长度 (mm)">
                  <el-input-number v-model="componentParams.hood_length" :min="800" :max="1500" />
                </el-form-item>
                <el-form-item label="车顶高度 (mm)">
                  <el-input-number v-model="componentParams.roof_height" :min="300" :max="600" />
                </el-form-item>
                <el-form-item label="车轮直径 (mm)">
                  <el-input-number v-model="componentParams.wheel_diameter" :min="400" :max="800" />
                </el-form-item>
                <el-form-item label="前车门长度 (mm)">
                  <el-input-number v-model="componentParams.door_front_length" :min="800" :max="1200" />
                </el-form-item>
              </el-form>
            </el-tab-pane>
            <el-tab-pane label="造型角度" name="angles">
              <el-form :model="angleParams" label-width="120px">
                <el-form-item label="发动机盖角度 (°)">
                  <el-input-number v-model="angleParams.hood_angle" :min="0" :max="45" />
                </el-form-item>
                <el-form-item label="前风挡角度 (°)">
                  <el-input-number v-model="angleParams.windshield_angle" :min="20" :max="70" />
                </el-form-item>
                <el-form-item label="后风挡角度 (°)">
                  <el-input-number v-model="angleParams.rear_window_angle" :min="10" :max="45" />
                </el-form-item>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </el-card>

        <el-card class="panel-card">
          <template #header>
            <span>部件生成</span>
          </template>
          <div class="component-grid">
            <div
              v-for="comp in componentList"
              :key="comp.key"
              class="component-item"
              @click="generateComponent(comp.key)"
            >
              <div class="comp-icon" :style="{ background: comp.color }">
                <el-icon><component :is="comp.icon" /></el-icon>
              </div>
              <div class="comp-name">{{ comp.name }}</div>
            </div>
          </div>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="result-card">
          <template #header>
            <div class="result-header">
              <span>生成结果</span>
              <el-button type="text" @click="clearResult">清空</el-button>
            </div>
          </template>
          
          <div v-if="!carResult" class="empty-state">
            <div class="empty-icon">
              <el-icon><Car /></el-icon>
            </div>
            <p>点击上方按钮生成车身模型</p>
          </div>

          <div v-else class="result-content">
            <div class="result-stats">
              <div class="stat-item">
                <span class="stat-value">{{ carResult.total_surfaces }}</span>
                <span class="stat-label">部件数量</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ carResult.parameters?.length || 0 }}</span>
                <span class="stat-label">参数数量</span>
              </div>
            </div>

            <div class="component-list">
              <h4>部件列表</h4>
              <el-table :data="carResult.components" style="width: 100%" stripe size="small">
                <el-table-column prop="name" label="部件名称" />
                <el-table-column prop="type" label="类型" width="100">
                  <template #default="{ row }">
                    <el-tag size="small">{{ row.type }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="color" label="颜色" width="100">
                  <template #default="{ row }">
                    <span class="color-dot" :style="{ background: row.color }"></span>
                    {{ row.color }}
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="result-actions">
              <el-button type="primary" @click="regenerateCar">重新生成</el-button>
              <el-button type="success" @click="exportCarData">导出数据</el-button>
            </div>
          </div>
        </el-card>

        <el-card class="preview-card" v-if="carResult">
          <template #header>
            <span>3D 预览</span>
          </template>
          <div class="preview-placeholder">
            <el-icon><Monitor /></el-icon>
            <p>GLB 模型预览区域</p>
            <p class="preview-hint">提示：使用导出功能下载 GLB 文件后在 3D 查看器中打开</p>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  Play, Car, Monitor, Building,
  Window, Circle, DoorOpen, Shield,
  Headphones, MoreHorizontal
} from '@element-plus/icons-vue'
import { carAPI, projectAPI } from '../services/api'

const paramTab = ref('dimensions')
const carParams = ref({
  overall_length: 4800,
  overall_width: 1850,
  overall_height: 1450,
  wheel_base: 2800
})
const componentParams = ref({
  hood_length: 1200,
  roof_height: 450,
  wheel_diameter: 600,
  door_front_length: 1000
})
const angleParams = ref({
  hood_angle: 25,
  windshield_angle: 50,
  rear_window_angle: 30
})

const carResult = ref(null)
const projects = ref([])
const selectedProject = ref('')

const componentList = [
  { key: 'hood', name: '发动机盖', icon: Building, color: '#00d9ff' },
  { key: 'roof', name: '车顶', icon: Building, color: '#ff6b6b' },
  { key: 'wheel', name: '车轮', icon: Circle, color: '#ffd93d' },
  { key: 'door_front', name: '前车门', icon: DoorOpen, color: '#6bcb77' },
  { key: 'door_rear', name: '后车门', icon: DoorOpen, color: '#4d96ff' },
  { key: 'windshield', name: '前风挡', icon: Window, color: '#87CEEB' },
  { key: 'bumper_front', name: '前保险杠', icon: Shield, color: '#9966ff' },
  { key: 'bumper_rear', name: '后保险杠', icon: Shield, color: '#ff9966' },
  { key: 'headlight', name: '前大灯', icon: MoreHorizontal, color: '#ffff00' },
  { key: 'taillight', name: '后尾灯', icon: MoreHorizontal, color: '#ff0000' },
  { key: 'mirror', name: '后视镜', icon: Headphones, color: '#666666' },
  { key: 'trunk', name: '行李箱', icon: Building, color: '#00ff88' }
]

const loadProjects = async () => {
  try {
    const response = await projectAPI.list()
    projects.value = response.data
    if (projects.value.length > 0) {
      selectedProject.value = projects.value[0].id
    }
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

const generateCar = async () => {
  try {
    const params = {
      ...carParams.value,
      ...componentParams.value,
      ...angleParams.value
    }
    const response = await carAPI.generate({ params_override: params })
    carResult.value = response.data
  } catch (error) {
    console.error('Failed to generate car:', error)
    alert('车身生成失败')
  }
}

const generateComponent = async (component) => {
  try {
    const response = await carAPI.generateComponent(component, {})
    if (!carResult.value) {
      carResult.value = { components: [], total_surfaces: 0 }
    }
    carResult.value.components.push(response.data)
    carResult.value.total_surfaces = carResult.value.components.length
  } catch (error) {
    console.error('Failed to generate component:', error)
    alert('部件生成失败')
  }
}

const regenerateCar = async () => {
  try {
    const response = await carAPI.regenerate({})
    carResult.value = response.data
  } catch (error) {
    console.error('Failed to regenerate:', error)
    alert('重新生成失败')
  }
}

const exportCarData = async () => {
  try {
    await carAPI.export({})
    alert('数据导出成功')
  } catch (error) {
    console.error('Export failed:', error)
    alert('导出失败')
  }
}

const clearResult = () => {
  carResult.value = null
}

onMounted(() => {
  loadProjects()
})
</script>

<style>
.designer-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.main-content {
  display: grid;
  grid-template-columns: 450px 1fr;
  gap: 20px;
}

.panel-card { margin-bottom: 20px; }

.component-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.component-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.component-item:hover {
  border-color: #00d9ff;
  background: rgba(0, 217, 255, 0.05);
}

.comp-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  margin-bottom: 8px;
}

.comp-name { font-size: 12px; color: #666; }

.result-card { height: 500px; }

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 350px;
  color: #999;
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: #f5f7fa;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  font-size: 40px;
  color: #00d9ff;
}

.result-content { height: calc(100% - 60px); overflow-y: auto; }

.result-stats {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.stat-item { text-align: center; }

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #00d9ff;
}

.stat-label { font-size: 12px; color: #999; }

.component-list h4 { margin-bottom: 15px; }

.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.result-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.preview-card { height: 300px; }

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: #fafafa;
  border-radius: 8px;
  color: #999;
}

.preview-placeholder .el-icon {
  font-size: 40px;
  margin-bottom: 15px;
  color: #00d9ff;
}

.preview-hint {
  font-size: 12px;
  margin-top: 5px;
}
</style>
