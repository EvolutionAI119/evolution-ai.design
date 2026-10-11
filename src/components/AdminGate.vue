<template>
  <!-- 启动身份核验 -->
  <div v-if="state === 'checking'" class="boot-box">
    <el-icon class="is-loading" :size="26"><Loading /></el-icon>
    <span>{{ t('adminGate.checking') }}</span>
  </div>

  <!-- 登录门：生产环境管理员凭邮箱口令进入 -->
  <div v-else-if="state === 'login'" class="gate-shell">
    <div class="login-card">
      <div class="brand">
        <h2>EVOLUTION AI</h2>
        <p>{{ t('adminGate.title') }}</p>
      </div>
      <el-form @submit.prevent="doLogin">
        <el-form-item>
          <el-input
            v-model="email"
            size="large"
            :placeholder="t('adminGate.email')"
            clearable
          >
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            size="large"
            show-password
            :placeholder="t('adminGate.password')"
            @keyup.enter="doLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="busy"
          @click="doLogin"
        >{{ t('adminGate.login') }}</el-button>
      </el-form>
    </div>
  </div>

  <!-- 已登录但非管理员 -->
  <div v-else-if="state === 'forbidden'" class="gate-shell">
    <div class="forbidden-card">
      <el-icon :size="44" class="warn-icon"><WarningFilled /></el-icon>
      <h2>{{ t('adminGate.forbidden') }}</h2>
      <p>{{ t('adminGate.forbiddenHint') }}</p>
      <el-button type="primary" plain @click="backToLogin">
        {{ t('adminGate.back') }}
      </el-button>
    </div>
  </div>

  <!-- 核验通过：完整管理后台 -->
  <div v-else class="admin-shell">
    <Admin />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Loading, Lock, Message, WarningFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import Admin from '../views/Admin.vue'

const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

// checking → login / ready / forbidden
const state = ref('checking')
const email = ref('')
const password = ref('')
const busy = ref(false)

const isManager = (u) =>
  u?.role === 'admin' || u?.role === 'superadmin' || u?.is_admin === true

onMounted(async () => {
  try {
    const me = await auth.fetchMe()
    state.value = me && isManager(me) ? 'ready' : 'forbidden'
  } catch {
    // 401（生产环境无令牌 / 游客模式关闭）：出示登录门
    state.value = 'login'
  }
})

const doLogin = async () => {
  if (!email.value.trim() || !password.value) {
    ElMessage.warning(t('adminGate.formRequired'))
    return
  }
  busy.value = true
  try {
    const data = await auth.login(email.value.trim(), password.value)
    if (isManager(data.user)) {
      state.value = 'ready'
    } else {
      // 非管理员：清空会话，转入无权页
      auth.setToken('')
      auth.user = null
      state.value = 'forbidden'
    }
  } catch {
    ElMessage.error(t('adminGate.loginFailed'))
  } finally {
    busy.value = false
  }
}

const backToLogin = () => {
  email.value = ''
  password.value = ''
  state.value = 'login'
}
</script>

<style scoped>
.boot-box {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: var(--text-muted);
  font-size: 14px;
}

.gate-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-card {
  width: 380px;
  max-width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 36px 32px;
}

.brand {
  text-align: center;
  margin-bottom: 26px;
}

.brand h2 {
  font-size: 22px;
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.brand p {
  font-size: 13px;
  color: var(--text-muted);
}

.submit-btn {
  width: 100%;
}

.forbidden-card {
  width: 420px;
  max-width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 40px 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.warn-icon {
  color: #fbbf24;
}

.forbidden-card p {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.admin-shell {
  padding: 24px 28px;
  min-height: 100vh;
}
</style>
