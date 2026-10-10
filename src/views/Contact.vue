<template>
  <div class="contact-page">
    <div class="contact-card">
      <div class="contact-icon">
        <el-icon :size="34"><Message /></el-icon>
      </div>
      <h1 class="contact-title">{{ t('contact.title') }}</h1>
      <p class="contact-subtitle">{{ t('contact.subtitle') }}</p>
      <div class="contact-email-row">
        <span class="contact-email">{{ email }}</span>
        <el-button size="small" class="copy-btn" @click="copyEmail">
          {{ copied ? t('contact.copied') : t('contact.copy') }}
        </el-button>
      </div>
      <el-button type="primary" class="mail-btn" @click="openMail">
        {{ t('contact.mailto') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
// 联系页（替代封存中的 Account 账户模块）：
// 单一联系方式入口，点击唤起邮件客户端或复制地址
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Message } from '@element-plus/icons-vue'

const { t } = useI18n({ useScope: 'global' })
const email = 'Icemtrainer@hotmail.com'
const copied = ref(false)

const openMail = () => {
  window.location.href = `mailto:${email}`
}

const copyEmail = async () => {
  try {
    await navigator.clipboard.writeText(email)
  } catch {
    // 剪贴板 API 不可用（非安全上下文）时退回 execCommand
    const ta = document.createElement('textarea')
    ta.value = email
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<style scoped>
.contact-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 24px;
}

.contact-card {
  max-width: 520px;
  width: 100%;
  text-align: center;
  padding: 48px 40px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.light-theme .contact-card {
  background: #fff;
  border-color: rgba(0, 0, 0, 0.08);
}

.contact-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
}

.contact-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
}

.contact-subtitle {
  margin: 0 0 24px;
  opacity: 0.65;
  font-size: 14px;
  line-height: 1.6;
}

.contact-email-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 24px;
}

.contact-email {
  font-family: monospace;
  font-size: 15px;
  letter-spacing: 0.02em;
}

.copy-btn {
  flex-shrink: 0;
}

.mail-btn {
  min-width: 180px;
}
</style>
