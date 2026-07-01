<template>
  <div class="handover-page">
    <div class="page-header">
      <div class="header-left">
        <h2>工程数据交接</h2>
        <p>准备和管理工程数据交付</p>
      </div>
      <el-button type="primary" @click="showHandoverDialog = true">
        <el-icon><Upload /></el-icon>
        开始交接
      </el-button>
    </div>

    <div class="formats-info">
      <h3>支持的交付格式</h3>
      <div class="formats-grid">
        <div class="format-card">
          <div class="format-icon">IGES</div>
          <div class="format-info">
            <h4>IGES</h4>
            <p>A级曲面数据</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">STEP</div>
          <div class="format-info">
            <h4>STEP</h4>
            <p>实体模型数据</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">JT</div>
          <div class="format-info">
            <h4>JT</h4>
            <p>轻量化评审数据</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">OBJ</div>
          <div class="format-info">
            <h4>OBJ</h4>
            <p>通用3D格式</p>
          </div>
        </div>
      </div>
    </div>

    <div class="accuracy-standard">
      <h3>精度标准</h3>
      <el-table :data="accuracyStandards" style="width: 100%" stripe>
        <el-table-column prop="level" label="精度等级" />
        <el-table-column prop="accuracy" label="精度要求" />
        <el-table-column prop="continuity" label="连续性" />
        <el-table-column prop="usage" label="应用场景" />
      </el-table>
    </div>

    <el-dialog v-model="showHandoverDialog" title="准备工程数据交接" width="500px">
      <el-form :model="handoverForm" label-width="100px">
        <el-form-item label="选择模型" required>
          <el-select v-model="handoverForm.model_id" placeholder="请选择模型">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="输出格式">
          <el-checkbox-group v-model="handoverForm.formats">
            <el-checkbox label="IGES" />
            <el-checkbox label="STEP" />
            <el-checkbox label="JT" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="其他选项">
          <el-checkbox v-model="handoverForm.include_renders">包含渲染图</el-checkbox>
          <el-checkbox v-model="handoverForm.include_documentation">包含文档</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showHandoverDialog = false">取消</el-button>
        <el-button type="primary" @click="prepareHandover">开始准备</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showResultDialog" title="交接完成" width="600px">
      <div v-if="handoverResult" class="result-content">
        <div class="result-header">
          <el-icon class="success-icon"><CircleCheck /></el-icon>
          <span class="result-title">数据交接准备完成</span>
        </div>
        <div class="result-summary">
          <div class="summary-item">
            <span class="label">完成率:</span>
            <span class="value">{{ handoverResult.report.summary.completion_rate }}</span>
          </div>
          <div class="summary-item">
            <span class="label">总文件数:</span>
            <span class="value">{{ handoverResult.report.total_files }}</span>
          </div>
          <div class="summary-item">
            <span class="label">已交付:</span>
            <span class="value">{{ handoverResult.report.summary.existing_files }}</span>
          </div>
        </div>
        <h4>精度验证结果</h4>
        <el-table :data="handoverResult.report.accuracy.checks" style="width: 100%">
          <el-table-column prop="check" label="检查项" />
          <el-table-column prop="target" label="目标" />
          <el-table-column prop="actual" label="实际" />
          <el-table-column prop="result" label="结果">
            <template #default="{ row }">
              <el-tag :type="row.result === '通过' ? 'success' : 'danger'">
                {{ row.result }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="result-actions">
          <el-button type="success" @click="downloadArchive">下载归档包</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Upload, CircleCheck } from '@element-plus/icons-vue'
import { handoverAPI, modelAPI } from '../services/api'

const models = ref([])
const showHandoverDialog = ref(false)
const showResultDialog = ref(false)
const handoverResult = ref(null)

const handoverForm = ref({
  model_id: '',
  formats: ['IGES', 'STEP', 'JT'],
  include_renders: true,
  include_documentation: true
})

const accuracyStandards = ref([
  { level: '概念级', accuracy: '±5-10mm', continuity: 'G0-G1', usage: '快速验证' },
  { level: '验证级', accuracy: '±1-2mm', continuity: 'G1-G2', usage: '设计评审' },
  { level: '工程级', accuracy: '±0.5mm', continuity: 'G2', usage: '工程分析' },
  { level: '生产级', accuracy: '±0.1mm', continuity: 'G2+', usage: '制造数据' }
])

const loadModels = async () => {
  try {
    const response = await modelAPI.list()
    models.value = response.data
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const prepareHandover = async () => {
  if (!handoverForm.value.model_id) {
    alert('请选择模型')
    return
  }

  try {
    showHandoverDialog.value = false
    const response = await handoverAPI.prepare(handoverForm.value)
    handoverResult.value = response.data
    showResultDialog.value = true
  } catch (error) {
    console.error('Handover preparation failed:', error)
    alert('数据交接准备失败')
  }
}

const downloadArchive = () => {
  alert('归档包下载功能')
}

loadModels()
</script>

<style>
.handover-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.formats-info, .accuracy-standard {
  margin-bottom: 30px;
}

.formats-info h3, .accuracy-standard h3 { margin-bottom: 15px; }

.formats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
}

.format-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.format-icon {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #00d9ff, #0099cc);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  font-weight: bold;
}

.format-info h4 { margin: 0; }
.format-info p { margin: 5px 0 0 0; font-size: 14px; color: #666; }

.result-content { padding: 10px; }

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.success-icon {
  font-size: 32px;
  color: #00ff88;
}

.result-title { font-size: 20px; font-weight: bold; }

.result-summary {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
}

.summary-item { display: flex; gap: 10px; }
.summary-item .label { color: #666; }
.summary-item .value { font-weight: bold; font-size: 18px; }

.result-actions { margin-top: 20px; text-align: center; }
</style>