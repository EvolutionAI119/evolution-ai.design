<template>
  <div class="variant-page">
    <div class="page-header">
      <div class="header-left">
        <h2>模型变体</h2>
        <p>管理模型变体、版本对比与回滚</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        创建变体
      </el-button>
    </div>

    <div class="variant-container">
      <div class="left-panel">
        <el-card class="model-select-card">
          <template #header>
            <span>选择模型</span>
          </template>
          <el-select v-model="selectedModelId" placeholder="请选择模型" style="width: 100%">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-card>

        <el-card class="variants-list-card">
          <template #header>
            <div class="list-header">
              <span>变体列表</span>
              <span class="count">{{ variants.length }} 个</span>
            </div>
          </template>
          <div v-if="variants.length === 0" class="empty-variants">
            <p>暂无变体</p>
          </div>
          <div v-else class="variants-list">
            <div
              v-for="variant in variants"
              :key="variant.id"
              class="variant-item"
              :class="{ active: selectedVariantId === variant.id }"
              @click="selectVariant(variant)"
            >
              <div class="variant-header">
                <span class="variant-name">{{ variant.name }}</span>
                <span class="variant-date">{{ variant.created_at }}</span>
              </div>
              <div class="variant-desc">{{ variant.description || '无描述' }}</div>
              <div class="variant-actions">
                <el-button type="text" size="small" @click.stop="compareVariant(variant)">对比</el-button>
                <el-button type="text" size="small" @click.stop="rollbackVariant(variant)">回滚</el-button>
                <el-button type="text" size="small" @click.stop="deleteVariant(variant)">删除</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="compare-card">
          <template #header>
            <span>变体对比</span>
          </template>
          <el-form :model="compareForm" label-width="80px">
            <el-form-item label="模型A">
              <el-select v-model="compareForm.model_a" placeholder="选择模型">
                <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="模型B">
              <el-select v-model="compareForm.model_b" placeholder="选择模型">
                <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" @click="runCompare" style="width: 100%">
              <el-icon><GitCompare /></el-icon>
              执行对比
            </el-button>
          </el-form>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="detail-card" v-if="selectedVariant">
          <template #header>
            <div class="detail-header">
              <span>变体详情</span>
              <el-tag type="success">版本 {{ selectedVariant.id }}</el-tag>
            </div>
          </template>
          <div class="detail-content">
            <div class="detail-row">
              <span class="detail-label">名称</span>
              <span class="detail-value">{{ selectedVariant.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">描述</span>
              <span class="detail-value">{{ selectedVariant.description || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">模型ID</span>
              <span class="detail-value">{{ selectedVariant.model_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ selectedVariant.created_at }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">参数差异</span>
              <div class="delta-list" v-if="selectedVariant.delta">
                <div
                  v-for="(value, key) in selectedVariant.delta"
                  :key="key"
                  class="delta-item"
                >
                  <span class="delta-key">{{ key }}</span>
                  <span class="delta-value">{{ value }}</span>
                </div>
              </div>
              <span v-else class="detail-value">无参数变更</span>
            </div>
          </div>
        </el-card>

        <el-card class="compare-result-card" v-if="compareResult">
          <template #header>
            <span>对比结果</span>
          </template>
          <div class="compare-summary">
            <div class="compare-item">
              <span class="compare-label">模型A</span>
              <span class="compare-value">{{ compareResult.model_a?.filename || '-' }}</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">模型B</span>
              <span class="compare-value">{{ compareResult.model_b?.filename || '-' }}</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">文件大小差异</span>
              <span class="compare-value">{{ compareResult.differences?.file_size_diff ?? '-' }} bytes</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">类型匹配</span>
              <span :class="compareResult.differences?.type_match ? 'match-yes' : 'match-no'">
                {{ compareResult.differences?.type_match ? '是' : '否' }}
              </span>
            </div>
          </div>

          <div class="compare-details" v-if="compareResult.param_differences">
            <h4>参数差异 ({{ Object.keys(compareResult.param_differences).length }} 项)</h4>
            <el-table :data="paramDiffList" style="width: 100%" stripe size="small">
              <el-table-column prop="name" label="参数名称" />
              <el-table-column prop="value_a" label="模型A">
                <template #default="{ row }">
                  {{ row.value_a ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="value_b" label="模型B">
                <template #default="{ row }">
                  {{ row.value_b ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="delta" label="差异">
                <template #default="{ row }">
                  <span v-if="row.delta !== null" :class="row.delta > 0 ? 'delta-positive' : 'delta-negative'">
                    {{ row.delta > 0 ? '+' : '' }}{{ row.delta }}
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="no-diff">
            <p>两模型无参数差异记录</p>
          </div>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>版本历史</span>
          </template>
          <div v-if="versionHistory.length === 0" class="empty-history">
            <p>暂无版本历史</p>
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="(item, idx) in versionHistory"
              :key="idx"
              :timestamp="item.timestamp"
              placement="top"
            >
              <el-card size="small">
                <div class="history-title">{{ item.action }}</div>
                <div class="history-desc">{{ item.description }}</div>
                <el-tag size="small" :type="item.type === 'create' ? 'success' : 'warning'">
                  {{ item.type === 'create' ? '创建' : '修改' }}
                </el-tag>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" title="创建变体" width="500px">
      <el-form :model="variantForm" label-width="80px">
        <el-form-item label="模型" required>
          <el-select v-model="variantForm.model_id" placeholder="请选择模型">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="变体名称" required>
          <el-input v-model="variantForm.name" placeholder="请输入变体名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="variantForm.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="参数变更">
          <el-input v-model="variantForm.params_json" type="textarea" placeholder='{"param_name": value}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createVariant">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, GitCompare } from '@element-plus/icons-vue'
import { variantAPI, modelAPI } from '../services/api'

const models = ref([])
const selectedModelId = ref('')
const variants = ref([])
const selectedVariantId = ref(null)
const selectedVariant = ref(null)
const compareForm = ref({
  model_a: '',
  model_b: ''
})
const compareResult = ref(null)
const versionHistory = ref([])

// 将后端 param_differences dict 转为表格数组
const paramDiffList = computed(() => {
  if (!compareResult.value?.param_differences) return []
  return Object.entries(compareResult.value.param_differences).map(([name, data]) => ({
    name,
    value_a: data.value_a,
    value_b: data.value_b,
    delta: data.delta ?? null
  }))
})
const showCreateDialog = ref(false)

const variantForm = ref({
  model_id: '',
  name: '',
  description: '',
  params_json: ''
})

const loadModels = async () => {
  try {
    const response = await modelAPI.list()
    models.value = response.data
  } catch (error) {
    console.error('Failed to load models:', error)
  }
}

const loadVariants = async () => {
  if (!selectedModelId.value) return
  try {
    const response = await variantAPI.list(selectedModelId.value)
    variants.value = response.data
  } catch (error) {
    console.error('Failed to load variants:', error)
  }
}

const selectVariant = (variant) => {
  selectedVariantId.value = variant.id
  selectedVariant.value = variant
}

const createVariant = async () => {
  if (!variantForm.value.model_id || !variantForm.value.name) {
    alert('请填写模型和名称')
    return
  }

  try {
    const params = {
      model_id: variantForm.value.model_id,
      name: variantForm.value.name,
      description: variantForm.value.description
    }
    if (variantForm.value.params_json) {
      params.delta = JSON.parse(variantForm.value.params_json)
    }
    await variantAPI.create(params)
    showCreateDialog.value = false
    variantForm.value = { model_id: '', name: '', description: '', params_json: '' }
    await loadVariants()
    alert('变体创建成功')
  } catch (error) {
    console.error('Create variant failed:', error)
    alert('创建失败')
  }
}

const compareVariant = async (variant) => {
  if (!selectedModelId.value) return
  try {
    const response = await variantAPI.compare({
      model_id_a: selectedModelId.value,
      model_id_b: variant.model_id
    })
    compareResult.value = response.data
  } catch (error) {
    console.error('Compare failed:', error)
  }
}

const rollbackVariant = async (variant) => {
  if (!confirm('确定要回滚到此变体吗？')) return
  try {
    await variantAPI.rollback(variant.model_id, variant.id)
    alert('回滚成功')
  } catch (error) {
    console.error('Rollback failed:', error)
    alert('回滚失败')
  }
}

const deleteVariant = async (variant) => {
  if (!confirm('确定要删除此变体吗？')) return
  try {
    await variantAPI.delete(variant.model_id, variant.id)
    await loadVariants()
    alert('删除成功')
  } catch (error) {
    console.error('Delete failed:', error)
    alert('删除失败')
  }
}

const runCompare = async () => {
  if (!compareForm.value.model_a || !compareForm.value.model_b) {
    alert('请选择两个模型')
    return
  }
  try {
    const response = await variantAPI.compare({
      model_id_a: compareForm.value.model_a,
      model_id_b: compareForm.value.model_b
    })
    compareResult.value = response.data
  } catch (error) {
    console.error('Compare failed:', error)
    alert('对比失败')
  }
}

watch(selectedModelId, () => {
  loadVariants()
})

onMounted(() => {
  loadModels()
})
</script>

<style>
.variant-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.variant-container {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 20px;
}

.model-select-card { margin-bottom: 20px; }

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.count { font-size: 12px; color: #999; }

.variants-list-card { height: 400px; }

.empty-variants {
  text-align: center;
  padding: 60px;
  color: #999;
}

.variants-list { height: calc(100% - 50px); overflow-y: auto; }

.variant-item {
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.variant-item:hover { border-color: #00d9ff; }

.variant-item.active {
  border-color: #00d9ff;
  background: rgba(0, 217, 255, 0.05);
}

.variant-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.variant-name { font-weight: bold; }
.variant-date { font-size: 12px; color: #999; }

.variant-desc { font-size: 13px; color: #666; margin-bottom: 10px; }

.variant-actions { display: flex; gap: 15px; }

.compare-card { margin-top: 20px; }

.detail-card { margin-bottom: 20px; }

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-content { display: flex; flex-direction: column; gap: 15px; }

.detail-row { display: flex; gap: 20px; }

.detail-label {
  font-weight: bold;
  color: #999;
  min-width: 100px;
}

.detail-value { flex: 1; }

.delta-list { flex: 1; display: flex; flex-direction: column; gap: 5px; }

.delta-item {
  display: flex;
  justify-content: space-between;
  padding: 5px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.delta-key { font-weight: bold; }
.delta-value { color: #00d9ff; }

.compare-result-card { margin-bottom: 20px; }

.compare-summary {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.compare-item { text-align: center; }

.compare-label { font-size: 12px; color: #999; display: block; }
.compare-value { font-size: 24px; font-weight: bold; color: #00d9ff; }

.compare-details h4 { margin-bottom: 15px; }

.delta-positive { color: #00ff88; font-weight: bold; }
.delta-negative { color: #ff4757; font-weight: bold; }

.match-yes { color: #00ff88; font-weight: bold; font-size: 18px; }
.match-no { color: #ff4757; font-weight: bold; font-size: 18px; }

.no-diff { text-align: center; padding: 30px; color: #999; }

.history-card { min-height: 300px; }

.empty-history {
  text-align: center;
  padding: 40px;
  color: #999;
}

.history-title { font-weight: bold; }
.history-desc { font-size: 12px; color: #999; margin-top: 5px; }
</style>
