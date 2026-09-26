<template>
  <div class="account-page">
    <div class="page-hero">
      <h1 class="hero-title">{{ t('account.title') }}</h1>
      <p class="hero-subtitle">{{ t('account.subtitle') }}</p>
    </div>

    <div class="account-layout">
      <!-- 用户信息卡 -->
      <el-card class="user-card">
        <div class="user-avatar">
          {{ avatarText }}
        </div>
        <div class="user-meta" v-if="auth.user">
          <h2 class="user-name">{{ auth.user.username }}</h2>
          <p class="user-email">{{ auth.user.email }}</p>
        </div>
        <el-divider />
        <div class="user-rows">
          <div class="user-row">
            <span class="row-label">{{ t('account.userId') }}</span>
            <span class="row-value">{{ auth.user?.id }}</span>
          </div>
          <div class="user-row">
            <span class="row-label">{{ t('account.role') }}</span>
            <span class="row-value">
              <el-tag :type="auth.user?.is_admin ? 'warning' : 'success'" size="small" effect="dark">
                {{ auth.user?.is_admin ? t('account.admin') : t('account.member') }}
              </el-tag>
            </span>
          </div>
          <div class="user-row">
            <span class="row-label">{{ t('account.joinedAt') }}</span>
            <span class="row-value">{{ formatDate(auth.user?.created_at) }}</span>
          </div>
        </div>
        <el-button class="logout-btn" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          {{ t('account.logout') }}
        </el-button>
      </el-card>

      <!-- Token 管理 -->
      <el-card class="keys-card">
        <template #header>
          <div class="keys-header">
            <div>
              <span class="keys-title">{{ t('account.keysTitle') }}</span>
              <p class="keys-desc">{{ t('account.keysDesc') }}</p>
            </div>
            <el-button text :icon="Refresh" @click="loadKeys">
              {{ t('account.refresh') }}
            </el-button>
          </div>
        </template>

        <div class="key-row" v-for="item in keys" :key="item.provider">
          <div class="key-info">
            <div class="key-brand">
              <span class="key-logo" :class="item.provider">
                {{ providerMeta[item.provider]?.short || item.provider.slice(0, 2) }}
              </span>
              <div>
                <div class="key-name">{{ providerMeta[item.provider]?.name || item.provider }}</div>
                <div class="key-status">
                  <span class="status-dot" :class="{ on: item.configured }"></span>
                  {{ item.configured
                      ? t('account.configuredAt', { date: formatDate(item.updated_at) })
                      : t('account.notConfigured') }}
                </div>
              </div>
            </div>
            <div class="key-masked">{{ item.configured ? item.masked : '—' }}</div>
          </div>
          <div class="key-actions">
            <el-input
              v-model="editing[item.provider]"
              size="default"
              class="key-input"
              :placeholder="t('account.tokenPlaceholder')"
              show-password
              clearable
            />
            <el-button
              type="primary"
              :disabled="!canSave(item.provider)"
              :loading="saving === item.provider"
              @click="saveKey(item.provider)"
            >{{ item.configured ? t('account.update') : t('account.save') }}</el-button>
            <el-button
              v-if="item.configured"
              type="danger"
              plain
              :loading="removing === item.provider"
              @click="removeKey(item.provider)"
            >{{ t('account.delete') }}</el-button>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, SwitchButton } from '@element-plus/icons-vue'
import { apiKeyAPI } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const keys = ref([])
const editing = reactive({})
const saving = ref('')
const removing = ref('')

// 提供商展示元信息（与后端 LLM 代理注册表对应）
const providerMeta = {
  ernie: { name: '百度文心一言', short: '文' },
  qwen: { name: '阿里通义千问', short: '通' },
  hunyuan: { name: '腾讯混元', short: '混' },
  doubao: { name: '字节豆包', short: '豆' },
  deepseek: { name: 'DeepSeek 深度求索', short: 'DS' },
  kimi: { name: 'Moonshot Kimi', short: 'K' },
  siliconflow: { name: '硅基流动 SiliconFlow', short: 'SF' }
}

const avatarText = computed(() => {
  const name = auth.user?.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

const formatDate = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()).padStart(2, '0')}`
}

const canSave = (provider) => {
  const v = editing[provider] || ''
  return v.trim().length >= 4
}

const loadKeys = async () => {
  try {
    const { data } = await apiKeyAPI.list()
    keys.value = data
    data.forEach((k) => {
      if (!(k.provider in editing)) editing[k.provider] = ''
    })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('account.loadFailed'))
  }
}

const saveKey = async (provider) => {
  saving.value = provider
  try {
    await apiKeyAPI.set(provider, editing[provider].trim())
    ElMessage.success(t('account.saveSuccess', { name: providerMeta[provider].name }))
    editing[provider] = ''
    await loadKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('account.saveFailed'))
  } finally {
    saving.value = ''
  }
}

const removeKey = async (provider) => {
  try {
    await ElMessageBox.confirm(
      t('account.deleteConfirm', { name: providerMeta[provider].name }),
      t('account.deleteTitle'),
      { type: 'warning', confirmButtonText: t('account.delete'),
        cancelButtonText: t('account.cancel') }
    )
  } catch {
    return
  }
  removing.value = provider
  try {
    await apiKeyAPI.remove(provider)
    ElMessage.success(t('account.deleteSuccess'))
    await loadKeys()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('account.deleteFailed'))
  } finally {
    removing.value = ''
  }
}

const handleLogout = () => {
  auth.logout()
  router.replace('/login')
}

onMounted(async () => {
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      router.replace('/login')
      return
    }
  }
  await loadKeys()
})
</script>

<style scoped>
.account-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 12px 0;
}

.page-hero { text-align: center; padding: 28px 20px 8px; }

.hero-title {
  margin: 0 0 10px;
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
}

.hero-subtitle {
  margin: 0 auto;
  max-width: 560px;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
}

.account-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
}

.user-card,
.keys-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

:deep(.el-card__body) { padding: 24px; }

.user-avatar {
  width: 72px;
  height: 72px;
  margin: 0 auto 14px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 800;
  color: #06120a;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  box-shadow: 0 8px 24px rgba(74, 222, 128, 0.25);
}

.user-meta { text-align: center; }

.user-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.user-email {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}

:deep(.el-divider) { border-color: var(--border-color); margin: 18px 0; }

.user-rows { display: flex; flex-direction: column; gap: 14px; }

.user-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.row-label { color: var(--text-muted); }
.row-value { color: var(--text-primary); font-weight: 600; }

.logout-btn {
  width: 100%;
  margin-top: 22px;
  border-color: rgba(248, 113, 113, 0.4);
  color: #f87171;
  background: transparent;
}

.logout-btn:hover {
  background: rgba(248, 113, 113, 0.1);
  border-color: #f87171;
  color: #f87171;
}

.keys-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.keys-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.keys-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.key-row {
  padding: 18px 0;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.key-row:last-child { border-bottom: none; padding-bottom: 4px; }
.key-row:first-of-type { padding-top: 10px; }

.key-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.key-brand { display: flex; align-items: center; gap: 12px; }

.key-logo {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #4ade80;
  background: var(--accent-bg);
  border: 1px solid rgba(74, 222, 128, 0.2);
}

.key-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.key-status {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}

.status-dot.on { background: #4ade80; box-shadow: 0 0 6px rgba(74,222,128,0.6); }

.key-masked {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.key-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.key-input { flex: 1; min-width: 160px; }

:deep(.key-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.03);
  box-shadow: 0 0 0 1px var(--border-color) inset;
}

@media (max-width: 900px) {
  .account-layout { grid-template-columns: 1fr; }
}
</style>
