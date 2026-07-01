<template>
  <div class="parameters-page">
    <div class="page-header">
      <div class="header-left">
        <h2>参数管理</h2>
        <p>管理整车级参数化建模参数</p>
      </div>
      <el-button type="primary" @click="validateParams">
        <el-icon><CheckCircle /></el-icon>
        验证参数
      </el-button>
    </div>

    <div class="param-tree">
      <el-tabs v-model="activeLevel">
        <el-tab-pane label="整车级" name="整车级">
          <el-table :data="paramsByLevel['整车级'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" label="参数名称" />
            <el-table-column prop="value" label="值">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="min_value" label="最小值" />
            <el-table-column prop="max_value" label="最大值" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="子系统级" name="子系统级">
          <el-table :data="paramsByLevel['子系统级'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" label="参数名称" />
            <el-table-column prop="value" label="值">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="部件级" name="部件级">
          <el-table :data="paramsByLevel['部件级'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" label="参数名称" />
            <el-table-column prop="value" label="值">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="细节级" name="细节级">
          <el-table :data="paramsByLevel['细节级'] || []" style="width: 100%" stripe>
            <el-table-column prop="name" label="参数名称" />
            <el-table-column prop="value" label="值">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.value"
                  :min="row.min_value"
                  :max="row.max_value"
                  @change="updateParam(row)"
                />
                <span class="unit">{{ row.unit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="param-validation" v-if="validationResult">
      <el-card>
        <template #header>
          <span>参数验证结果</span>
        </template>
        <div class="validation-summary">
          <div class="validation-item">
            <span class="label">参数总数:</span>
            <span class="value">{{ validationResult.total_parameters }}</span>
          </div>
          <div class="validation-item">
            <span class="label">有效参数:</span>
            <span class="value valid">{{ validationResult.valid_parameters }}</span>
          </div>
          <div class="validation-item">
            <span class="label">验证结果:</span>
            <span :class="validationResult.valid ? 'value valid' : 'value invalid'">
              {{ validationResult.valid ? '✓ 通过' : '✗ 未通过' }}
            </span>
          </div>
        </div>
        <div v-if="validationResult.issues.length > 0" class="validation-issues">
          <h4>问题列表:</h4>
          <el-table :data="validationResult.issues" style="width: 100%">
            <el-table-column prop="parameter" label="参数" />
            <el-table-column prop="issue" label="问题" />
            <el-table-column prop="severity" label="严重程度">
              <template #default="{ row }">
                <el-tag :type="row.severity === '高' ? 'danger' : 'warning'">
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
import { CheckCircle } from '@element-plus/icons-vue'
import { parameterAPI } from '../services/api'

const parameters = ref({})
const activeLevel = ref('整车级')
const validationResult = ref(null)

const paramsByLevel = computed(() => {
  const result = {}
  for (const level of ['整车级', '子系统级', '部件级', '细节级']) {
    result[level] = parameters.value[level] || []
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

<style>
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