<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="bg-grid"></div>
      <div class="bg-glow"></div>
    </div>

    <div class="auth-card">
      <div class="auth-brand">
        <div class="brand-mark">E</div>
        <h1 class="brand-name">EVOLUTION AI</h1>
        <p class="brand-sub">{{ t('auth.subtitle') }}</p>
      </div>

      <el-tabs v-model="activeTab" class="auth-tabs" stretch>
        <!-- 登录 -->
        <el-tab-pane :label="t('auth.login')" name="login">
          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-position="top"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="email" :label="t('auth.email')">
              <el-input
                v-model="loginForm.email"
                size="large"
                :placeholder="t('auth.emailPlaceholder')"
                :prefix-icon="Message"
              />
            </el-form-item>
            <el-form-item prop="password" :label="t('auth.password')">
              <el-input
                v-model="loginForm.password"
                type="password"
                size="large"
                show-password
                :placeholder="t('auth.passwordPlaceholder')"
                :prefix-icon="Lock"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="auth-submit"
              :loading="auth.loading"
              @click="handleLogin"
            >{{ t('auth.loginSubmit') }}</el-button>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane :label="t('auth.register')" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
            @submit.prevent="handleRegister"
          >
            <el-form-item prop="username" :label="t('auth.username')">
              <el-input
                v-model="registerForm.username"
                size="large"
                :placeholder="t('auth.usernamePlaceholder')"
                :prefix-icon="User"
              />
            </el-form-item>
            <el-form-item prop="email" :label="t('auth.email')">
              <el-input
                v-model="registerForm.email"
                size="large"
                :placeholder="t('auth.emailPlaceholder')"
                :prefix-icon="Message"
              />
            </el-form-item>
            <el-form-item prop="password" :label="t('auth.password')">
              <el-input
                v-model="registerForm.password"
                type="password"
                size="large"
                show-password
                :placeholder="t('auth.newPasswordPlaceholder')"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-form-item prop="confirm" :label="t('auth.confirmPassword')">
              <el-input
                v-model="registerForm.confirm"
                type="password"
                size="large"
                show-password
                :placeholder="t('auth.confirmPlaceholder')"
                :prefix-icon="Lock"
                @keyup.enter="handleRegister"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="auth-submit"
              :loading="auth.loading"
              @click="handleRegister"
            >{{ t('auth.registerSubmit') }}</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="auth-demo-hint">
        <el-icon><InfoFilled /></el-icon>
        <span>{{ t('auth.demoHint') }}</span>
      </div>

      <!-- 第三方登录：微信扫码 / 公众号网页授权 -->
      <div v-if="showPasswordLogin || showWechatLogin || showMpLogin" class="auth-divider"><span>{{ t('auth.orContinueWith') }}</span></div>
      <div class="oauth-row">
        <button v-if="showWechatLogin" class="wechat-btn" :disabled="wechatLoading" @click="handleWechatLogin">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d="M8.69 4C4.99 4 2 6.46 2 9.5c0 1.73.96 3.26 2.45 4.28l-.61 1.83 2.13-1.06c.29.06.58.11.89.14-.06-.24-.1-.49-.1-.75 0-2.9 2.9-5.25 6.48-5.25.23 0 .46.01.68.03C13.32 6.11 11.24 4 8.69 4zm-1.7 3.06a.84.84 0 1 1 0 1.68.84.84 0 0 1 0-1.68zm4.55 0a.84.84 0 1 1 0 1.68.84.84 0 0 1 0-1.68zM22 13.94c0-2.53-2.53-4.59-5.66-4.59-3.12 0-5.65 2.06-5.65 4.59 0 2.54 2.53 4.6 5.65 4.6.66 0 1.29-.1 1.87-.27l1.77.88-.5-1.5A4.4 4.4 0 0 0 22 13.94zm-7.68-1.5a.7.7 0 1 1 0 1.4.7.7 0 0 1 0-1.4zm3.77 0a.7.7 0 1 1 0 1.4.7.7 0 0 1 0-1.4z"/>
          </svg>
          <span>{{ wechatLoading ? t('auth.wechatLoading') : t('auth.wechatLogin') }}</span>
        </button>
        <button v-if="showMpLogin" class="wechat-btn mp" :disabled="mpLoading" @click="handleMpLogin">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-6h2v6zm0-8h-2V7h2v2zm6 8h-2v-4h-2v4h-2v-6h6v6z"/>
          </svg>
          <span>{{ mpLoading ? t('auth.wechatLoading') : t('auth.mpLogin') }}</span>
        </button>
      </div>

      <!-- 公众号扫码弹窗：PC 端展示二维码，手机微信扫码确认后自动登录 -->
      <el-dialog
        v-model="mpDialogVisible"
        :title="t('auth.mpLogin')"
        width="320px"
        align-center
        @close="stopMpPolling"
      >
        <div class="mp-qr-box">
          <canvas ref="mpQrCanvas" class="mp-qr-canvas"></canvas>
          <p class="mp-qr-hint">{{ t('auth.mpScanHint') }}</p>
        </div>
      </el-dialog>

      <div class="auth-footer">
        <button class="lang-mini" @click="switchLang('zh')">中文</button>
        <span class="dot">·</span>
        <button class="lang-mini" @click="switchLang('en')">English</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Lock, Message, User, InfoFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { authAPI } from '../api'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const activeTab = ref('login')
const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = reactive({ email: '', password: '' })
const registerForm = reactive({
  username: '', email: '', password: '', confirm: ''
})

// 校验规则（提示文案随当前语言）
const emailValidator = (rule, value, callback) => {
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) {
    callback(new Error(t('auth.invalidEmail')))
  } else {
    callback()
  }
}

const loginRules = {
  email: [
    { required: true, message: t('auth.emailRequired'), trigger: 'blur' },
    { validator: emailValidator, trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('auth.passwordRequired'), trigger: 'blur' }
  ]
}

const registerRules = {
  username: [
    { required: true, message: t('auth.usernameRequired'), trigger: 'blur' },
    { min: 1, max: 100, message: t('auth.usernameLength'), trigger: 'blur' }
  ],
  email: [
    { required: true, message: t('auth.emailRequired'), trigger: 'blur' },
    { validator: emailValidator, trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('auth.passwordRequired'), trigger: 'blur' },
    { min: 6, max: 128, message: t('auth.passwordLength'), trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: t('auth.confirmRequired'), trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error(t('auth.confirmMismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const goAfterAuth = () => {
  const redirect = route.query.redirect
  router.replace(redirect && typeof redirect === 'string' ? redirect : '/')
}

const handleLogin = async () => {
  try {
    await loginFormRef.value.validate()
  } catch {
    return
  }
  try {
    await auth.login(loginForm.email.trim(), loginForm.password)
    ElMessage.success(t('auth.loginSuccess'))
    goAfterAuth()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('auth.loginFailed'))
  }
}

const handleRegister = async () => {
  try {
    await registerFormRef.value.validate()
  } catch {
    return
  }
  try {
    await auth.register(
      registerForm.email.trim(),
      registerForm.username.trim(),
      registerForm.password
    )
    ElMessage.success(t('auth.registerSuccess'))
    goAfterAuth()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('auth.registerFailed'))
  }
}

const switchLang = (lang) => {
  locale.value = lang
  localStorage.setItem('language', lang)
}

// ── 微信扫码登录：弹窗扫码 → 后端回调 postMessage 回传 JWT ──
const wechatLoading = ref(false)
let wechatPopup = null

// ── 登录方式探测：仅显示后端已配置的入口 ──
const showPasswordLogin = ref(true)
const showWechatLogin = ref(false)
const showMpLogin = ref(false)

onMounted(async () => {
  // 公众号授权回跳（微信内整页跳转）：URL 携带 mp_token 直接完成登录
  const mpToken = route.query.mp_token
  if (typeof mpToken === 'string' && mpToken) {
    auth.setToken(mpToken)
    await auth.fetchMe().catch(() => {})
    ElMessage.success(t('auth.mpSuccess'))
    goAfterAuth()
    return
  }
  try {
    const { data } = await authAPI.methods()
    showWechatLogin.value = !!data.wechat_qr
    showMpLogin.value = !!data.mp_oauth
  } catch {
    // 探测失败时保守处理：都不显示，避免点击报"未配置"
    showWechatLogin.value = false
    showMpLogin.value = false
  }
})

// ── 公众号登录：PC 端展示二维码 + 轮询；微信内置浏览器直接整页跳转授权 ──
const mpLoading = ref(false)
let mpPopup = null
const mpDialogVisible = ref(false)
const mpQrCanvas = ref()
const mpQrContent = ref('')
let mpPollTimer = null
// 微信内置浏览器内直接跳转授权页（PC 浏览器打不开公众号授权页）
const isWechatBrowser = /MicroMessenger/i.test(navigator.userAgent)

// 登录会话票据：同一会话内多次点击/开关二维码均复用，
// 保证手机扫码结果与 PC 轮询始终对应，不会错配
const MP_TICKET_KEY = 'evoai_mp_ticket'
const getMpTicket = () => {
  let tk = sessionStorage.getItem(MP_TICKET_KEY)
  if (!tk) {
    tk = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
    sessionStorage.setItem(MP_TICKET_KEY, tk)
  }
  return tk
}
const mpTicket = ref(getMpTicket())

const stopMpPolling = () => {
  if (mpPollTimer) {
    clearInterval(mpPollTimer)
    mpPollTimer = null
  }
}

// 二维码渲染：弹窗打开且 canvas 挂载后绘制
watch(mpDialogVisible, async (visible) => {
  if (!visible) return
  await nextTick()
  if (mpQrCanvas.value) {
    const QR = await import('qrcode')
    QR.toCanvas(mpQrCanvas.value, mpQrContent.value, { width: 240, margin: 1 })
  }
})

const startMpPolling = () => {
  stopMpPolling()
  mpPollTimer = setInterval(async () => {
    try {
      const { data } = await authAPI.mpPoll(mpTicket.value)
      if (data.status === 'done') {
        stopMpPolling()
        mpDialogVisible.value = false
        const result = data.result
        if (result?.ok && result.token) {
          auth.setToken(result.token)
          auth.user = result.user || null
          ElMessage.success(t('auth.mpSuccess'))
          goAfterAuth()
        } else {
          ElMessage.error(t('auth.wechatFailed'))
        }
      } else if (data.status === 'expired') {
        stopMpPolling()
        mpDialogVisible.value = false
        ElMessage.warning(t('auth.mpExpired'))
      }
      // pending：继续轮询；网络抖动：下个周期重试
    } catch { /* 忽略单次轮询失败 */ }
  }, 2000)
}

const handleMpLogin = async () => {
  mpLoading.value = true
  try {
    const { data } = await authAPI.mpAuthorize(mpTicket.value)
    if (data.ticket) mpTicket.value = data.ticket
    if (isWechatBrowser) {
      // 微信内：整页跳转授权，回调后展示成功页
      window.location.href = data.auth_url
      return
    }
    // PC：弹二维码，手机微信扫码确认后按票据轮询自动登录
    mpQrContent.value = data.auth_url
    mpDialogVisible.value = true
    startMpPolling()
  } catch (e) {
    const status = e.response?.status
    if (status === 503) {
      ElMessage.warning(t('auth.mpUnavailable'))
    } else {
      ElMessage.error(t('auth.wechatFailed'))
    }
  } finally {
    mpLoading.value = false
  }
}

// 回调弹窗 postMessage 监听（微信扫码登录弹窗场景）
const onWechatMessage = async (event) => {
  // 仅接受后端回调域的消息（配置 FRONTEND_URL 对应本页面域）
  const data = event.data
  if (!data || (data.type !== 'wechat_auth' && data.type !== 'mp_auth')) return
  window.removeEventListener('message', onWechatMessage)
  if (wechatPopup && !wechatPopup.closed) wechatPopup.close()
  if (mpPopup && !mpPopup.closed) mpPopup.close()
  wechatPopup = null
  mpPopup = null
  if (data.ok && data.token) {
    auth.setToken(data.token)
    auth.user = data.user || null
    ElMessage.success(data.type === 'mp_auth' ? t('auth.mpSuccess') : t('auth.wechatSuccess'))
    goAfterAuth()
  } else {
    ElMessage.error(t('auth.wechatFailed'))
  }
}

const openAuthPopup = (url, name) => {
  window.addEventListener('message', onWechatMessage)
  const w = 600, h = 700
  const left = window.screenX + (window.outerWidth - w) / 2
  const top = window.screenY + (window.outerHeight - h) / 2
  const popup = window.open(
    url, name,
    `width=${w},height=${h},left=${left},top=${top},menubar=no,toolbar=no`
  )
  if (!popup) {
    // 浏览器拦截弹窗：退化为整页跳转
    window.location.href = url
  }
  return popup
}

const handleWechatLogin = async () => {
  wechatLoading.value = true
  try {
    const { data } = await authAPI.wechatQr()
    wechatPopup = openAuthPopup(data.auth_url, 'wechat_login')
  } catch (e) {
    const status = e.response?.status
    if (status === 503) {
      ElMessage.warning(t('auth.wechatUnavailable'))
    } else {
      ElMessage.error(t('auth.wechatFailed'))
    }
  } finally {
    wechatLoading.value = false
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('message', onWechatMessage)
  stopMpPolling()
})
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
  background: #07070c;
}

.auth-bg { position: absolute; inset: 0; pointer-events: none; }

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(74, 222, 128, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(74, 222, 128, 0.05) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black 30%, transparent 75%);
}

.bg-glow {
  position: absolute;
  width: 620px;
  height: 620px;
  left: 50%;
  top: 38%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(74, 222, 128, 0.14), transparent 65%);
  filter: blur(20px);
}

.auth-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  background: rgba(18, 18, 26, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 36px 36px 24px;
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.auth-brand { text-align: center; margin-bottom: 12px; }

.brand-mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 800;
  color: #06120a;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  box-shadow: 0 8px 24px rgba(74, 222, 128, 0.3);
}

.brand-name {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 1.5px;
  color: #fff;
}

.brand-sub {
  margin: 6px 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.auth-tabs { margin-top: 8px; }
.auth-tabs :deep(.el-tabs__item) { font-size: 15px; font-weight: 600; }
.auth-tabs :deep(.el-tabs__item.is-active) { color: #4ade80; }
.auth-tabs :deep(.el-tabs__active-bar) { background-color: #4ade80; }
.auth-tabs :deep(.el-tabs__nav-wrap::after) { background-color: rgba(255,255,255,0.07); }

.auth-tabs :deep(.el-form-item__label) {
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
  padding-bottom: 4px;
}

.auth-tabs :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.04);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08) inset;
  border-radius: 8px;
}

.auth-tabs :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.6) inset;
}

.auth-tabs :deep(.el-input__inner) { color: #fff; }
.auth-tabs :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.3); }

.auth-submit {
  width: 100%;
  margin-top: 6px;
  background: #4ade80;
  border-color: #4ade80;
  color: #06120a;
  font-weight: 700;
  border-radius: 8px;
}

.auth-submit:hover {
  background: #22c55e;
  border-color: #22c55e;
}

.auth-demo-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 10px 12px;
  background: rgba(74, 222, 128, 0.07);
  border: 1px solid rgba(74, 222, 128, 0.15);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.55);
}

.auth-footer {
  margin-top: 16px;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
}

.lang-mini {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
}

.lang-mini:hover { color: #4ade80; }
.dot { margin: 0 6px; }

/* 微信扫码登录 */
.auth-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0 12px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
}
.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
}

.wechat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 0;
  border-radius: 8px;
  border: 1px solid rgba(9, 187, 7, 0.45);
  background: rgba(9, 187, 7, 0.1);
  color: #3fd43d;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}
.wechat-btn:hover:not(:disabled) {
  background: rgba(9, 187, 7, 0.2);
  border-color: rgba(9, 187, 7, 0.7);
}
.wechat-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 第三方登录按钮排布 */
.oauth-row {
  display: flex;
  gap: 10px;
}
.oauth-row .wechat-btn { flex: 1; }
.wechat-btn.mp {
  border-color: rgba(74, 222, 128, 0.35);
  background: rgba(74, 222, 128, 0.08);
  color: #4ade80;
}
.wechat-btn.mp:hover:not(:disabled) {
  background: rgba(74, 222, 128, 0.16);
  border-color: rgba(74, 222, 128, 0.6);
}

/* 公众号扫码弹窗 */
.mp-qr-box { text-align: center; }
.mp-qr-canvas { width: 240px; height: 240px; }
.mp-qr-hint {
  margin: 14px 0 4px;
  font-size: 13px;
  line-height: 1.6;
  color: #909399;
}
</style>
