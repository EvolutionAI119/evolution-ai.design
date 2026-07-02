<template>
  <div class="parameters-page">
    <div class="page-header">
      <div class="header-left">
        <h2>{{ $t('parameters.title') }}</h2>
        <p>{{ $t('parameters.subtitle') }}</p>
      </div>
      <el-button type="primary" @click="validateParams">
        <el-icon><CircleCheck /></el-icon>
        {{ $t('parameters.validate') }}
      </el-button>
    </div>

    <div class="param-tree">
      <el-tabs v-model="activeLevel">
        <el-tab-pane :label="$t('parameters.vehicleLevel')" name="vehicle">
          <el-table :data="paramsByLevel['vehicle'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" :label="$t('parameters.paramName')" />
            <el-table-column prop="value" :label="$t('parameters.value')">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  style="width: 120px"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" :label="$t('parameters.description')" />
            <el-table-column prop="min_value" :label="$t('parameters.minValue')" />
            <el-table-column prop="max_value" :label="$t('parameters.maxValue')" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="$t('parameters.subsystemLevel')" name="subsystem">
          <el-table :data="paramsByLevel['subsystem'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" :label="$t('parameters.paramName')" />
            <el-table-column prop="value" :label="$t('parameters.value')">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  style="width: 120px"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" :label="$t('parameters.description')" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="$t('parameters.componentLevel')" name="component">
          <el-table :data="paramsByLevel['component'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" :label="$t('parameters.paramName')" />
            <el-table-column prop="value" :label="$t('parameters.value')">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  style="width: 120px"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" :label="$t('parameters.description')" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane :label="$t('parameters.detailLevel')" name="detail">
          <el-table :data="paramsByLevel['detail'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" :label="$t('parameters.paramName')" />
            <el-table-column prop="value" :label="$t('parameters.value')">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  style="width: 120px"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" :label="$t('parameters.description')" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="param-validation" v-if="validationResult">
      <el-card>
        <template #header>
          <span>{{ $t('parameters.validationResult') }}</span>
        </template>
        <div class="validation-summary">
          <div class="validation-item">
            <span class="label">{{ $t('parameters.totalParams') }}:</span>
            <span class="value">{{ validationResult.total_parameters }}</span>
          </div>
          <div class="validation-item">
            <span class="label">{{ $t('parameters.validParams') }}:</span>
            <span class="value valid">{{ validationResult.valid_parameters }}</span>
          </div>
          <div class="validation-item">
            <span class="label">{{ $t('parameters.validationStatus') }}:</span>
            <span :class="validationResult.valid ? 'value valid' : 'value invalid'">
              {{ validationResult.valid ? $t('parameters.pass') : $t('parameters.fail') }}
            </span>
          </div>
        </div>
        <div v-if="validationResult.issues.length > 0" class="validation-issues">
          <h4>{{ $t('parameters.issues') }}:</h4>
          <el-table :data="validationResult.issues" style="width: 100%">
            <el-table-column prop="parameter" :label="$t('parameters.parameter')" />
            <el-table-column prop="issue" :label="$t('parameters.issue')" />
            <el-table-column prop="severity" :label="$t('parameters.severity')">
              <template #default="{ row }">
                <el-tag :type="row.severity === $t('parameters.high') ? 'danger' : 'warning'">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CircleCheck } from '@element-plus/icons-vue'
import { parameterAPI } from '../services/api'

const { t } = useI18n()

const parameters = ref({})
const activeLevel = ref('vehicle')
const validationResult = ref(null)

const levelKeyMap = {
  vehicle: '整车级',
  subsystem: '子系统级',
  component: '部件级',
  detail: '细节级'
}

const paramsByLevel = computed(() => {
  const result = {}
  const levels = ['vehicle', 'subsystem', 'component', 'detail']
  for (const level of levels) {
    result[level] = parameters.value[levelKeyMap[level]] || []
  }
  return result
})

const loadParameters = async () => {
  try {
    const response = await parameterAPI.list()
    parameters.value = response.data
  } catch (error) {
    console.error('Failed to load parameters:', error)
  }
}

const updateParam = async (param) => {
  try {
    await parameterAPI.update(param.name, param.value)
    console.log(`Parameter ${param.name} updated to ${param.value}`)
  } catch (error) {
    console.error('Failed to update parameter:', error)
  }
}

const validateParams = async () => {
  try {
    const response = await parameterAPI.validate()
    validationResult.value = response.data
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

loadParameters()
</script>

<style scoped>
.parameters-page { padding: 20px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 { margin: 0; font-size: 24px; }
.header-left p { margin: 5px 0 0 0; color: #999; }

.param-tree { margin-bottom: 20px; }

.unit { margin-left: 5px; color: #999; }

.validation-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 30px;
  margin-bottom: 20px;
}

.validation-item { display: flex; align-items: center; gap: 10px; }
.validation-item .label { color: #666; }
.validation-item .value { font-weight: bold; font-size: 18px; }
.validation-item .value.valid { color: #00ff88; }
.validation-item .value.invalid { color: #ff4757; }

.validation-issues h4 { margin-bottom: 10px; }
</style>