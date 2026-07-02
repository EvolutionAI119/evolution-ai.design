<template>
  <div class="variant-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('variants.title') }}</h2>
        <p>{{ $t('variants.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        {{ $t('variants.createVariant') }}
      </el-button>
    </div>

    <div class="variant-container">
      <div class="left-panel">
        <el-card class="model-select-card">
          <template #header>
            <span>{{ $t('variants.selectModel') }}</span>
          </template>
          <el-select v-model="selectedModelId" :placeholder="$t('common.pleaseSelect')" style="width: 100%">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-card>

        <el-card class="variants-list-card">
          <template #header>
            <div class="list-header">
              <span>{{ $t('variants.variantList') }}</span>
              <span class="count">{{ variants.length }} {{ $t('variants.count') }}</span>
            </div>
          </template>
          <div v-if="variants.length === 0" class="empty-variants">
            <p>{{ $t('variants.noVariants') }}</p>
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
              <div class="variant-desc">{{ variant.description || $t('variants.noDescription') }}</div>
              <div class="variant-actions">
                <el-button type="text" size="small" @click.stop="compareVariant(variant)">{{ $t('variants.compare') }}</el-button>
                <el-button type="text" size="small" @click.stop="rollbackVariant(variant)">{{ $t('variants.rollback') }}</el-button>
                <el-button type="text" size="small" @click.stop="deleteVariant(variant)">{{ $t('variants.delete') }}</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="compare-card">
          <template #header>
            <span>{{ $t('variants.variantCompare') }}</span>
          </template>
          <el-form :model="compareForm" label-width="80px">
            <el-form-item :label="$t('variants.modelA')">
              <el-select v-model="compareForm.model_a" :placeholder="$t('common.pleaseSelect')">
                <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('variants.modelB')">
              <el-select v-model="compareForm.model_b" :placeholder="$t('common.pleaseSelect')">
                <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" @click="runCompare" style="width: 100%">
              <el-icon><RefreshRight /></el-icon>
              {{ $t('variants.runCompare') }}
            </el-button>
          </el-form>
        </el-card>
      </div>

      <div class="right-panel">
        <el-card class="detail-card" v-if="selectedVariant">
          <template #header>
            <div class="detail-header">
              <span>{{ $t('variants.variantDetail') }}</span>
              <el-tag type="success">{{ $t('variants.version') }} {{ selectedVariant.id }}</el-tag>
            </div>
          </template>
          <div class="detail-content">
            <div class="detail-row">
              <span class="detail-label">{{ $t('variants.name') }}</span>
              <span class="detail-value">{{ selectedVariant.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ $t('variants.description') }}</span>
              <span class="detail-value">{{ selectedVariant.description || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ $t('variants.modelId') }}</span>
              <span class="detail-value">{{ selectedVariant.model_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ $t('variants.createdAt') }}</span>
              <span class="detail-value">{{ selectedVariant.created_at }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">{{ $t('variants.paramDelta') }}</span>
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
              <span v-else class="detail-value">{{ $t('variants.noDelta') }}</span>
            </div>
          </div>
        </el-card>

        <el-card class="compare-result-card" v-if="compareResult">
          <template #header>
            <span>{{ $t('variants.compareResult') }}</span>
          </template>
          <div class="compare-summary">
            <div class="compare-item">
              <span class="compare-label">{{ $t('variants.modelA') }}</span>
              <span class="compare-value">{{ compareResult.model_a?.filename || '-' }}</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">{{ $t('variants.modelB') }}</span>
              <span class="compare-value">{{ compareResult.model_b?.filename || '-' }}</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">{{ $t('variants.fileSizeDiff') }}</span>
              <span class="compare-value">{{ compareResult.differences?.file_size_diff ?? '-' }} bytes</span>
            </div>
            <div class="compare-item">
              <span class="compare-label">{{ $t('variants.typeMatch') }}</span>
              <span :class="compareResult.differences?.type_match ? 'match-yes' : 'match-no'">
                {{ compareResult.differences?.type_match ? $t('variants.yes') : $t('variants.no') }}
              </span>
            </div>
          </div>

          <div class="compare-details" v-if="compareResult.param_differences">
            <h4>{{ $t('variants.paramDifferences') }} ({{ Object.keys(compareResult.param_differences).length }} {{ $t('variants.items') }})</h4>
            <el-table :data="paramDiffList" style="width: 100%" stripe size="small">
              <el-table-column prop="name" :label="$t('variants.paramName')" />
              <el-table-column prop="value_a" :label="$t('variants.valueA')">
                <template #default="{ row }">
                  {{ row.value_a ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="value_b" :label="$t('variants.valueB')">
                <template #default="{ row }">
                  {{ row.value_b ?? '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="delta" :label="$t('variants.difference')">
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
            <p>{{ $t('variants.noDiff') }}</p>
          </div>
        </el-card>

        <el-card class="history-card">
          <template #header>
            <span>{{ $t('variants.versionHistory') }}</span>
          </template>
          <div v-if="versionHistory.length === 0" class="empty-history">
            <p>{{ $t('variants.noHistory') }}</p>
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
                  {{ item.type === 'create' ? $t('variants.create') : $t('variants.modify') }}
                </el-tag>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" :title="$t('variants.createVariant')" width="500px">
      <el-form :model="variantForm" label-width="80px">
        <el-form-item :label="$t('variants.model')" required>
          <el-select v-model="variantForm.model_id" :placeholder="$t('common.pleaseSelect')">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('variants.variantName')" required>
          <el-input v-model="variantForm.name" :placeholder="$t('variants.enterName')" />
        </el-form-item>
        <el-form-item :label="$t('variants.description')">
          <el-input v-model="variantForm.description" type="textarea" :placeholder="$t('common.pleaseInput')" />
        </el-form-item>
        <el-form-item :label="$t('variants.paramChange')">
          <el-input v-model="variantForm.params_json" type="textarea" placeholder='{"param_name": value}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">{{ $t('variants.cancel') }}</el-button>
        <el-button type="primary" @click="createVariant">{{ $t('variants.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, RefreshRight } from '@element-plus/icons-vue'
import { variantAPI, modelAPI } from '../services/api'

const { t } = useI18n()

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
    alert(t('variants.enterModelAndName'))
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
    alert(t('variants.createSuccess'))
  } catch (error) {
    console.error('Create variant failed:', error)
    alert(t('variants.createFailed'))
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
  if (!confirm(t('variants.confirmRollback'))) return
  try {
    await variantAPI.rollback(variant.model_id, variant.id)
    alert(t('variants.rollbackSuccess'))
  } catch (error) {
    console.error('Rollback failed:', error)
    alert(t('variants.rollbackFailed'))
  }
}

const deleteVariant = async (variant) => {
  if (!confirm(t('variants.confirmDelete'))) return
  try {
    await variantAPI.delete(variant.model_id, variant.id)
    await loadVariants()
    alert(t('variants.deleteSuccess'))
  } catch (error) {
    console.error('Delete failed:', error)
    alert(t('variants.deleteFailed'))
  }
}

const runCompare = async () => {
  if (!compareForm.value.model_a || !compareForm.value.model_b) {
    alert(t('variants.selectModels'))
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
    alert(t('variants.compareFailed'))
  }
}

watch(selectedModelId, () => {
  loadVariants()
})

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.variant-page { padding: 10px; }

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

.variants-list-card { min-height: 300px; max-height: 60vh; }

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

@media (max-width: 800px) {
  .variant-container {
    grid-template-columns: 1fr;
  }
}
</style>
