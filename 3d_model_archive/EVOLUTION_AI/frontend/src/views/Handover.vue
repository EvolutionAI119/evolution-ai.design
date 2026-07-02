<template>
  <div class="handover-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('handover.title') }}</h2>
        <p>{{ $t('handover.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="showHandoverDialog = true">
        <el-icon><Upload /></el-icon>
        {{ $t('handover.startHandover') }}
      </el-button>
    </div>

    <div class="formats-info">
      <h3>{{ $t('handover.supportedFormats') }}</h3>
      <div class="formats-grid">
        <div class="format-card">
          <div class="format-icon">{{ $t('handover.iges') }}</div>
          <div class="format-info">
            <h4>{{ $t('handover.iges') }}</h4>
            <p>{{ $t('handover.igesDesc') }}</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">{{ $t('handover.step') }}</div>
          <div class="format-info">
            <h4>{{ $t('handover.step') }}</h4>
            <p>{{ $t('handover.stepDesc') }}</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">{{ $t('handover.jt') }}</div>
          <div class="format-info">
            <h4>{{ $t('handover.jt') }}</h4>
            <p>{{ $t('handover.jtDesc') }}</p>
          </div>
        </div>
        <div class="format-card">
          <div class="format-icon">{{ $t('handover.obj') }}</div>
          <div class="format-info">
            <h4>{{ $t('handover.obj') }}</h4>
            <p>{{ $t('handover.objDesc') }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="accuracy-standard">
      <h3>{{ $t('handover.accuracyStandard') }}</h3>
      <el-table :data="accuracyStandards" style="width: 100%" stripe>
        <el-table-column prop="level" :label="$t('handover.accuracyLevel')" />
        <el-table-column prop="accuracy" :label="$t('handover.accuracyReq')" />
        <el-table-column prop="continuity" :label="$t('handover.continuity')" />
        <el-table-column prop="usage" :label="$t('handover.application')" />
      </el-table>
    </div>

    <el-dialog v-model="showHandoverDialog" :title="$t('handover.prepareHandover')" width="500px">
      <el-form :model="handoverForm" label-width="100px">
        <el-form-item :label="$t('handover.selectModel')" required>
          <el-select v-model="handoverForm.model_id" :placeholder="$t('common.pleaseSelect')">
            <el-option v-for="m in models" :key="m.id" :label="m.filename" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('handover.outputFormat')">
          <el-checkbox-group v-model="handoverForm.formats">
            <el-checkbox :label="$t('handover.iges')" />
            <el-checkbox :label="$t('handover.step')" />
            <el-checkbox :label="$t('handover.jt')" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item :label="$t('common.other')">
          <el-checkbox v-model="handoverForm.include_renders">{{ $t('handover.includeRenders') }}</el-checkbox>
          <el-checkbox v-model="handoverForm.include_documentation">{{ $t('handover.includeDocs') }}</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showHandoverDialog = false">{{ $t('handover.cancel') }}</el-button>
        <el-button type="primary" @click="prepareHandover">{{ $t('handover.startPrepare') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showResultDialog" :title="$t('handover.title')" width="600px">
      <div v-if="handoverResult" class="result-content">
        <div class="result-header">
          <el-icon class="success-icon"><CircleCheck /></el-icon>
          <span class="result-title">{{ $t('handover.title') }}</span>
        </div>
        <div class="result-summary">
          <div class="summary-item">
            <span class="label">{{ $t('common.completion') }}:</span>
            <span class="value">{{ handoverResult.report.summary.completion_rate }}</span>
          </div>
          <div class="summary-item">
            <span class="label">{{ $t('common.totalFiles') }}:</span>
            <span class="value">{{ handoverResult.report.total_files }}</span>
          </div>
          <div class="summary-item">
            <span class="label">{{ $t('common.delivered') }}:</span>
            <span class="value">{{ handoverResult.report.summary.existing_files }}</span>
          </div>
        </div>
        <h4>{{ $t('handover.accuracyStandard') }}</h4>
        <el-table :data="handoverResult.report.accuracy.checks" style="width: 100%">
          <el-table-column prop="check" :label="$t('common.checkItem')" />
          <el-table-column prop="target" :label="$t('common.target')" />
          <el-table-column prop="actual" :label="$t('common.actual')" />
          <el-table-column prop="result" :label="$t('common.result')">
            <template #default="{ row }">
              <el-tag :type="row.result === $t('common.passed') ? 'success' : 'danger'">
                {{ row.result }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="result-actions">
          <el-button type="success" @click="downloadArchive">{{ $t('handover.downloadArchive') }}</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Upload, CircleCheck } from '@element-plus/icons-vue'
import { handoverAPI, modelAPI } from '../services/api'

const { t } = useI18n()

const models = ref([])
const showHandoverDialog = ref(false)
const showResultDialog = ref(false)
const handoverResult = ref(null)

const handoverForm = ref({
  model_id: '',
  formats: [t('handover.iges'), t('handover.step'), t('handover.jt')],
  include_renders: true,
  include_documentation: true
})

const accuracyStandards = ref([
  { level: t('handover.conceptLevel'), accuracy: t('handover.conceptAccuracy'), continuity: t('handover.conceptContinuity'), usage: t('handover.conceptUsage') },
  { level: t('handover.verificationLevel'), accuracy: t('handover.verificationAccuracy'), continuity: t('handover.verificationContinuity'), usage: t('handover.verificationUsage') },
  { level: t('handover.engineeringLevel'), accuracy: t('handover.engineeringAccuracy'), continuity: t('handover.engineeringContinuity'), usage: t('handover.engineeringUsage') },
  { level: t('handover.productionLevel'), accuracy: t('handover.productionAccuracy'), continuity: t('handover.productionContinuity'), usage: t('handover.productionUsage') }
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
    alert(t('handover.selectModel'))
    return
  }

  try {
    showHandoverDialog.value = false
    const response = await handoverAPI.prepare(handoverForm.value)
    handoverResult.value = response.data
    showResultDialog.value = true
  } catch (error) {
    console.error('Handover preparation failed:', error)
    alert(t('handover.prepareFailed') || 'Preparation failed')
  }
}

const downloadArchive = () => {
  alert(t('handover.downloadArchive'))
}

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
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
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
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