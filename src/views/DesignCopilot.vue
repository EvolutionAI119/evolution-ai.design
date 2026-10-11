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

    <!-- 结果区：多车型范式候选 -->
    <template v-if="variants.length">
      <div class="variants-head">
        <div class="variants-title">
          <el-tag size="large" effect="dark" type="primary">{{ t('copilot.variants') }}</el-tag>
          <span class="variants-hint">{{ t('copilot.variantsHint') }}</span>
        </div>
        <el-tag
          v-if="failedCount"
          type="warning"
          effect="plain"
        >{{ failedCount }} {{ t('copilot.variantFailed') }}</el-tag>
      </div>

      <div class="variants-grid">
        <el-card
          v-for="plan in variants"
          :key="plan.car_type"
          class="variant-card"
          :class="{ 'is-failed': !!plan.error }"
          shadow="never"
        >
          <!-- 失败占位卡 -->
          <template v-if="plan.error">
            <div class="failed-body">
              <el-tag type="danger" effect="plain">
                {{ t('deepLearning.carTypes.' + plan.car_type) }}
              </el-tag>
              <p class="failed-msg">{{ plan.error }}</p>
            </div>
          </template>

          <!-- 正常方案卡 -->
          <template v-else>
            <div class="card-head">
              <el-tag size="large" type="success" effect="dark">
                {{ t('deepLearning.carTypes.' + plan.car_type) }}
              </el-tag>
              <div class="confidence">
                <span class="conf-label">{{ t('copilot.confidence') }}</span>
                <el-progress
                  :percentage="Math.round(plan.confidence * 100)"
                  :stroke-width="6"
                  style="width: 84px"
                />
              </div>
            </div>

            <div class="tag-row">
              <el-tag
                v-for="tag in plan.style_tags"
                :key="tag"
                size="small"
                effect="plain"
              >{{ tag }}</el-tag>
            </div>

            <div class="color-row">
              <div class="color-swatch" :style="{ background: plan.color.hex }" />
              <span class="color-name">{{ plan.color.name }}</span>
              <span class="color-hex">{{ plan.color.hex }}</span>
            </div>

            <div class="key-params">
              <div v-for="k in keyParamKeys" :key="k" class="key-param">
                <span class="kp-name">{{ t('deepLearning.paramNames.' + k) }}</span>
                <span class="kp-value">
                  {{ plan.params[k] }}
                  <em>{{ k.includes('angle') ? '°' : 'mm' }}</em>
                </span>
              </div>
            </div>

            <p class="rationale-text">{{ plan.rationale }}</p>

            <el-tooltip
              v-if="plan.warnings.length"
              :content="plan.warnings.join('；')"
              placement="top"
            >
              <el-tag size="small" type="warning" effect="plain" class="warn-badge">
                {{ t('copilot.warnings') }} ({{ plan.warnings.length }})
              </el-tag>
            </el-tooltip>

            <div class="card-actions">
              <el-button
                type="primary"
                size="small"
                @click="applyToDesigner(plan)"
              >
                <el-icon class="btn-icon"><Brush /></el-icon>
                {{ t('copilot.apply') }}
              </el-button>
              <el-button size="small" @click="copyJson(plan)">
                <el-icon class="btn-icon"><CopyDocument /></el-icon>
                {{ t('copilot.copy') }}
              </el-button>
            </div>
          </template>
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
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
const variants = ref([])

// 范式卡片的摘要参数（全量 14 参数通过复制 JSON / 设计器查看）
const keyParamKeys = [
  'overall_length', 'wheel_base', 'overall_height', 'windshield_angle'
]

const okCount = computed(() => variants.value.filter(v => !v.error).length)
const failedCount = computed(() => variants.value.filter(v => !!v.error).length)

const loadExamples = async () => {
  try {
    const { data } = await designIntentAPI.examples(locale.value)
    examples.value = data.examples
  } catch { /* 示例加载失败不阻塞 */ }
}

onMounted(loadExamples)

const onGenerate = async () => {
  if (prompt.value.trim().length < 2 || loading.value) return
  loading.value = true
  try {
    const { data } = await designIntentAPI.parseVariants(prompt.value.trim(), locale.value)
    variants.value = data.variants || []
    if (okCount.value && !failedCount.value) {
      ElMessage.success(t('copilot.variantsSuccess', { n: okCount.value }))
    } else if (okCount.value) {
      ElMessage.warning(t('copilot.variantsPartial',
        { ok: okCount.value, fail: failedCount.value }))
    } else {
      ElMessage.error(t('copilot.failed'))
    }
  } catch (e) {
    ElMessage.error(t(e.errorKey || 'copilot.failed'))
  } finally {
    loading.value = false
  }
}

// 切换界面语言后：示例与已生成方案都按新语言重新加载/解析，
// 保证英文界面下不残留后端旧语言的标签、颜色名与设计说明
watch(locale, async () => {
  await loadExamples()
  if (prompt.value.trim().length >= 2) await onGenerate()
})

const applyToDesigner = (plan) => {
  designer.setCarType(plan.car_type)
  designer.updateParams(plan.params)
  designer.selectColor(plan.color.hex)
  ElMessage.success(t('copilot.applied'))
  router.push('/designer')
}

const copyJson = async (plan) => {
  const text = JSON.stringify(
    { car_type: plan.car_type, params: plan.params, color: plan.color }, null, 2)
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

.result-card, .variant-card {
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

/* ── 多车型范式候选区 ── */
.variants-head {
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 10px; margin: 20px 0 12px;
}
.variants-title { display: flex; align-items: center; gap: 10px; }
.variants-hint { color: var(--text-secondary); font-size: 12px; }

.variants-grid {
  display: grid; grid-template-columns: repeat(2, 1fr);
  gap: 14px; align-items: start;
}
.variant-card { transition: border-color 0.2s; }
.variant-card:hover { border-color: var(--accent); }
.variant-card.is-failed { opacity: 0.75; }

.failed-body { display: flex; flex-direction: column; gap: 10px; }
.failed-msg {
  color: var(--text-muted); font-size: 12px; margin: 0;
  word-break: break-all; line-height: 1.6;
}

.card-head {
  display: flex; justify-content: space-between; align-items: center;
  gap: 10px; margin-bottom: 10px;
}
.confidence { display: flex; align-items: center; gap: 8px; }
.conf-label { font-size: 11px; color: var(--text-secondary); }

.tag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }

.color-row { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.color-swatch {
  width: 26px; height: 26px; border-radius: 6px;
  border: 1px solid var(--border-color); flex: none;
}
.color-name { font-size: 13px; font-weight: 600; }
.color-hex { color: var(--text-muted); font-size: 11px; font-family: monospace; }

.key-params { margin-bottom: 12px; }
.key-param {
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 4px 0; border-bottom: 1px solid var(--border-color);
}
.kp-name { font-size: 12px; color: var(--text-secondary); }
.kp-value { font-size: 13px; font-weight: 600; }
.kp-value em {
  font-style: normal; color: var(--text-muted); font-size: 10px; margin-left: 2px;
}

.rationale-text {
  color: var(--text-secondary); font-size: 12px; line-height: 1.7;
  margin: 0 0 12px;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
}

.warn-badge { cursor: help; }

.card-actions { display: flex; gap: 8px; margin-top: 12px; }

@media (max-width: 860px) {
  .variants-grid { grid-template-columns: 1fr; }
}
</style>
