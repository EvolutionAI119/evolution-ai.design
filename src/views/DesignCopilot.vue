<template>
  <div class="copilot-page">
    <!-- 标题 -->
    <div class="copilot-hero">
      <h1 class="copilot-title">{{ t('copilot.title') }}</h1>
      <p class="copilot-subtitle">{{ t('copilot.subtitle') }}</p>
    </div>

    <!-- 输入区 -->
    <el-card class="input-card" shadow="never">
      <el-input
        v-model="prompt"
        type="textarea"
        :rows="3"
        maxlength="1000"
        show-word-limit
        :placeholder="t('copilot.placeholder')"
        @keydown.ctrl.enter="onGenerate"
      />
      <div class="input-actions">
        <el-button
          type="primary"
          :loading="loading"
          :disabled="prompt.trim().length < 2"
          @click="onGenerate"
        >
          <el-icon class="btn-icon"><MagicStick /></el-icon>
          {{ t('copilot.generate') }}
        </el-button>
        <span class="hint">{{ t('copilot.ctrlEnter') }}</span>
      </div>
      <div v-if="examples.length" class="example-row">
        <span class="example-label">{{ t('copilot.examples') }}:</span>
        <el-tag
          v-for="(ex, i) in examples"
          :key="i"
          class="example-tag"
          effect="plain"
          @click="prompt = ex"
        >{{ ex }}</el-tag>
      </div>
    </el-card>

    <!-- 结果区 -->
    <template v-if="plan">
      <el-card class="result-card" shadow="never">
        <div class="result-head">
          <div class="result-tags">
            <el-tag size="large" type="success" effect="dark">
              {{ t('deepLearning.carTypes.' + plan.car_type) }}
            </el-tag>
            <el-tag
              v-for="tag in plan.style_tags"
              :key="tag"
              size="large"
              effect="plain"
              class="style-tag"
            >{{ tag }}</el-tag>
          </div>
          <div class="confidence">
            <span class="conf-label">{{ t('copilot.confidence') }}</span>
            <el-progress
              :percentage="Math.round(plan.confidence * 100)"
              :stroke-width="8"
              style="width: 120px"
            />
          </div>
        </div>

        <div class="color-row">
          <div class="color-swatch" :style="{ background: plan.color.hex }" />
          <span class="color-name">{{ plan.color.name }}</span>
          <span class="color-hex">{{ plan.color.hex }}</span>
        </div>

        <el-alert
          class="rationale"
          type="info"
          :closable="false"
          :title="plan.rationale"
        />

        <!-- 参数表 -->
        <div class="param-groups">
          <div v-for="g in paramGroups" :key="g.key" class="param-group">
            <h4>{{ t(g.titleKey) }}</h4>
            <div
              v-for="name in g.keys"
              :key="name"
              class="param-line"
            >
              <span class="param-name">{{ t('deepLearning.paramNames.' + name) }}</span>
              <span class="param-value">
                {{ plan.params[name] }}
                <em>{{ name.includes('angle') ? '°' : 'mm' }}</em>
              </span>
            </div>
          </div>
        </div>

        <el-alert
          v-if="plan.warnings.length"
          class="warnings"
          type="warning"
          :closable="false"
          show-icon
        >
          <template #title>{{ t('copilot.warnings') }} ({{ plan.warnings.length }})</template>
          <ul class="warning-list">
            <li v-for="(w, i) in plan.warnings" :key="i">{{ w }}</li>
          </ul>
        </el-alert>

        <div class="result-actions">
          <el-button type="primary" size="large" @click="applyToDesigner">
            <el-icon class="btn-icon"><Brush /></el-icon>
            {{ t('copilot.apply') }}
          </el-button>
          <el-button size="large" @click="copyJson">
            <el-icon class="btn-icon"><CopyDocument /></el-icon>
            {{ t('copilot.copy') }}
          </el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { MagicStick, Brush, CopyDocument } from '@element-plus/icons-vue'
import { designIntentAPI } from '../api'
import { useDesignerStore } from '../stores/designer'

const { t, locale } = useI18n()
const router = useRouter()
const designer = useDesignerStore()

const prompt = ref('')
const examples = ref([])
const loading = ref(false)
const plan = ref(null)

const paramGroups = [
  { key: 'size', titleKey: 'copilot.groupSize',
    keys: ['overall_length', 'overall_width', 'overall_height',
           'wheel_base', 'track_width', 'ground_clearance'] },
  { key: 'body', titleKey: 'copilot.groupBody',
    keys: ['hood_length', 'roof_height', 'wheel_diameter'] },
  { key: 'angle', titleKey: 'copilot.groupAngle',
    keys: ['windshield_angle', 'rear_window_angle', 'rear_slant_angle'] },
  { key: 'overhang', titleKey: 'copilot.groupOverhang',
    keys: ['front_overhang', 'rear_overhang'] }
]

onMounted(async () => {
  try {
    const { data } = await designIntentAPI.examples(locale.value)
    examples.value = data.examples
  } catch { /* 示例加载失败不阻塞 */ }
})

const onGenerate = async () => {
  if (prompt.value.trim().length < 2 || loading.value) return
  loading.value = true
  try {
    const { data } = await designIntentAPI.parse(prompt.value.trim())
    plan.value = data
    if (!data.warnings.length) {
      ElMessage.success(t('copilot.success'))
    }
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'copilot.failed'))
  } finally {
    loading.value = false
  }
}

const applyToDesigner = () => {
  designer.setCarType(plan.value.car_type)
  designer.updateParams(plan.value.params)
  designer.selectColor(plan.value.color.hex)
  ElMessage.success(t('copilot.applied'))
  router.push('/designer')
}

const copyJson = async () => {
  const text = JSON.stringify(
    { car_type: plan.value.car_type, params: plan.value.params,
      color: plan.value.color }, null, 2)
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(t('copilot.copied'))
  } catch {
    ElMessage.warning(t('copilot.copyFailed'))
  }
}
</script>

<style scoped>
.copilot-page { max-width: 980px; margin: 0 auto; }

.copilot-hero { margin-bottom: 20px; }
.copilot-title { font-size: 24px; font-weight: 800; margin: 0 0 6px; }
.copilot-subtitle { color: var(--text-secondary); font-size: 13px; margin: 0; }

.input-card, .result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}
.input-card :deep(.el-textarea__inner) {
  background: var(--control-bg);
  color: var(--text-primary);
  border-radius: 8px;
}
.input-actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.btn-icon { margin-right: 4px; }
.hint { color: var(--text-muted); font-size: 11px; }

.example-row { margin-top: 14px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.example-label { color: var(--text-muted); font-size: 12px; }
.example-tag { cursor: pointer; max-width: 340px; overflow: hidden; }
.example-tag:hover { border-color: var(--accent); }

.result-card { margin-top: 16px; }
.result-head {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 12px; margin-bottom: 14px;
}
.result-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.style-tag { font-size: 13px; }
.confidence { display: flex; align-items: center; gap: 10px; }
.conf-label { font-size: 12px; color: var(--text-secondary); }

.color-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
}
.color-swatch {
  width: 34px; height: 34px; border-radius: 8px;
  border: 1px solid var(--border-color);
}
.color-name { font-size: 14px; font-weight: 600; }
.color-hex { color: var(--text-muted); font-size: 12px; font-family: monospace; }

.rationale { margin-bottom: 18px; border-radius: 8px; }

.param-groups {
  display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 16px;
}
.param-group h4 {
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.6px;
  color: var(--text-muted); margin: 0 0 8px;
}
.param-line {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 5px 0; border-bottom: 1px solid var(--border-color);
}
.param-name { font-size: 13px; color: var(--text-secondary); }
.param-value { font-size: 13px; font-weight: 600; }
.param-value em {
  font-style: normal; color: var(--text-muted); font-size: 11px; margin-left: 3px;
}

.warnings { margin-bottom: 16px; border-radius: 8px; }
.warning-list { margin: 4px 0 0; padding-left: 18px; font-size: 12px; line-height: 1.8; }

.result-actions { display: flex; gap: 12px; margin-top: 4px; }

@media (max-width: 720px) {
  .param-groups { grid-template-columns: 1fr; }
}
</style>
