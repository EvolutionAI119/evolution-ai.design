<template>
  <!-- 登录/注册页：无侧边栏的全屏布局 -->
  <router-view v-if="isLoginRoute" />
  <div v-else class="app-container">
    <el-container>
      <el-aside width="216px" class="sidebar">
        <div class="logo">
          <h2>EVOLUTION AI</h2>
          <p>{{ t('app.subtitle') }}</p>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
          background-color="transparent"
          :text-color="menuTextColor"
          :active-text-color="activeMenuColor"
        >
          <template #default>
            <template v-for="group in menuGroups" :key="group.labelKey || 'ungrouped'">
              <div v-if="group.labelKey" class="menu-group-label">{{ t(group.labelKey) }}</div>
              <el-menu-item
                v-for="item in group.items"
                :key="item.path"
                :index="item.path"
              >
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ t(item.nameKey) }}</span>
              </el-menu-item>
            </template>
          </template>
        </el-menu>
      </el-aside>
      <el-container class="main-container">
        <el-header class="header">
          <div class="header-left">
            <span class="breadcrumb">EVOLUTION AI</span>
            <span class="sep">/</span>
            <span class="current-page">{{ currentPageName }}</span>
          </div>
          <div class="header-right">
            <!-- 中英文独立语言切换 -->
            <div class="lang-switch" :title="t('menu.language')">
              <button
                class="lang-btn"
                :class="{ active: locale === 'zh' }"
                @click="changeLanguage('zh')"
              >中</button>
              <button
                class="lang-btn"
                :class="{ active: locale === 'en' }"
                @click="changeLanguage('en')"
              >EN</button>
            </div>
            <div class="theme-toggle" @click="toggleTheme" :title="isDark ? t('menu.lightMode') : t('menu.darkMode')">
              <el-icon class="header-icon"><component :is="isDark ? Moon : Sunny" /></el-icon>
            </div>
            <el-icon class="header-icon"><Bell /></el-icon>

            <!-- 已登录：用户菜单；未登录：登录入口 -->
            <el-dropdown
              v-if="auth.isAuthenticated"
              trigger="click"
              @command="onUserCommand"
            >
              <div class="user-chip">
                <div class="user-chip-avatar">{{ userInitial }}</div>
                <span class="user-chip-name">{{ auth.user?.username || '—' }}</span>
                <el-icon class="chip-arrow"><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="account">
                    <el-icon><UserFilled /></el-icon>{{ t('account.menuItem') }}
                  </el-dropdown-item>
                  <el-dropdown-item command="logout" divided>
                    <el-icon><SwitchButton /></el-icon>{{ t('account.logout') }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-else
              size="small"
              class="login-btn"
              @click="goLogin"
            >
              <el-icon><UserFilled /></el-icon>{{ t('auth.login') }}
            </el-button>
          </div>
        </el-header>
        <el-main class="main-content">
          <!-- Element Plus 组件级语言随全局语言联动 -->
          <el-config-provider :locale="elementLocale">
            <router-view />
          </el-config-provider>
        </el-main>
      </el-container>
    </el-container>
  </div>

  <!-- 全局登录引导：游客触发「项目工作 / 模型生成」时友好提示，不强制跳转 -->
  <el-dialog
    v-model="loginPromptVisible"
    :title="t('auth.loginRequiredTitle')"
    width="380px"
    align-center
  >
    <div class="login-prompt-body">
      <el-icon class="login-prompt-icon"><Lock /></el-icon>
      <p>{{ loginPromptText }}</p>
    </div>
    <template #footer>
      <el-button @click="loginPromptVisible = false">{{ t('auth.maybeLater') }}</el-button>
      <el-button type="primary" @click="goLoginFromPrompt">{{ t('auth.login') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Odometer, Brush, Folder, MagicStick, CircleCheck, Upload, VideoPlay,
  Bell, Moon, Sunny, ArrowDown, UserFilled, SwitchButton, QuestionFilled,
  TrendCharts,
  Lock, Setting,
} from '@element-plus/icons-vue'
// Element Plus 内置语言包
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import enLocale from 'element-plus/dist/locale/en.mjs'
import { useAuthStore } from './stores/auth'
import { tracker } from './utils/tracker'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const isDark = ref(true)

// 侧边栏文字颜色必须随主题切换（Element Plus 通过内联样式注入，CSS 无法覆盖）
const menuTextColor = computed(() =>
  isDark.value ? 'rgba(255,255,255,0.72)' : 'rgba(26,26,46,0.72)'
)
const activeMenuColor = computed(() => (isDark.value ? '#4ade80' : '#16a34a'))

// 登录页采用全屏独立布局
const isLoginRoute = computed(() => route.name === 'Login')

const userInitial = computed(() => {
  const name = auth.user?.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

const goLogin = () => router.push('/login')

// ── 全局登录引导弹窗 ──────────────────────────
// 游客在任意页面触发需登录动作时，api.js/业务页派发 evoai:auth-required
// 事件，这里统一展示友好引导（可携带 detail.message 定制文案）。
const loginPromptVisible = ref(false)
const loginPromptMessage = ref('')
const loginPromptText = computed(() =>
  loginPromptMessage.value || t('auth.loginRequiredBody'))

const onAuthRequired = (event) => {
  loginPromptMessage.value = event?.detail?.message || ''
  loginPromptVisible.value = true
}

const goLoginFromPrompt = () => {
  loginPromptVisible.value = false
  const redirect = isLoginRoute.value ? '/' : route.fullPath
  router.push({ path: '/login', query: redirect !== '/' ? { redirect } : {} })
}

const onUserCommand = (command) => {
  if (command === 'account') {
    router.push('/account')
  } else if (command === 'logout') {
    auth.logout()
    // 退出后留在当前页、回到游客模式；
    // 仅当当前页要求登录（如账户设置）时回首页，避免守卫弹回登录页
    if (route.meta.requiresAuth) router.replace('/')
  }
}

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('light-theme', !isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

// 切换语言：两种语言独立模式，持久化保存
const changeLanguage = (lang) => {
  locale.value = lang
  localStorage.setItem('language', lang)
  document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-CN' : 'en')
}

// Element Plus 组件语言（分页、日历、校验提示等）
const elementLocale = computed(() => (locale.value === 'zh' ? zhCn : enLocale))

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light') {
    isDark.value = false
    document.documentElement.classList.add('light-theme')
  }
  document.documentElement.setAttribute('lang', locale.value === 'zh' ? 'zh-CN' : 'en')
  // 登录态仅存内存（会话级），页面打开时不恢复任何历史凭据
  // 全局登录引导事件（api.js 401 拦截与业务页动作拦截共用）
  window.addEventListener('evoai:auth-required', onAuthRequired)
  // 启动访问埋点（路由切换自动上报 + 停留时长）
  tracker.start(router)
})

onBeforeUnmount(() => {
  window.removeEventListener('evoai:auth-required', onAuthRequired)
  tracker.stop()
})

const baseMenuGroups = [
  {
    labelKey: '',
    items: [
      { path: '/', nameKey: 'menu.dashboard', icon: Odometer },
      { path: '/designer', nameKey: 'menu.aiDesigner', icon: Brush }
    ]
  },
  {
    labelKey: 'menu.groupDesign',
    items: [
      { path: '/projects', nameKey: 'menu.projects', icon: Folder },
      { path: '/deep-learning', nameKey: 'menu.deepLearning', icon: MagicStick }
    ]
  },
  {
    labelKey: 'menu.groupWorkflow',
    items: [
      { path: '/quality', nameKey: 'menu.quality', icon: CircleCheck },
      { path: '/deliver', nameKey: 'menu.deliver', icon: Upload }
    ]
  },
  {
    labelKey: '',
    items: [
      { path: '/demo', nameKey: 'menu.demo', icon: VideoPlay },
      { path: '/help', nameKey: 'menu.help', icon: QuestionFilled },
      { path: '/analytics', nameKey: 'menu.analytics', icon: TrendCharts },
      { path: '/account', nameKey: 'menu.account', icon: UserFilled }
    ]
  }
]

// 管理后台入口仅对管理员（admin / superadmin）显示
const menuGroups = computed(() => {
  if (!auth.isAdmin) return baseMenuGroups
  return [
    ...baseMenuGroups,
    {
      labelKey: 'menu.groupAdmin',
      items: [
        { path: '/admin', nameKey: 'menu.admin', icon: Setting }
      ]
    }
  ]
})

const allMenuItems = computed(() => menuGroups.value.flatMap(g => g.items))

const activeMenu = computed(() => router.currentRoute.value.path)

const currentPageName = computed(() => {
  const item = allMenuItems.value.find(m => m.path === router.currentRoute.value.path)
  return item ? t(item.nameKey) : t('menu.aiDesigner')
})
</script>

<style>
:root {
  --bg-primary: #0a0a0f;
  --bg-secondary: #12121a;
  --bg-card: #16161f;
  --text-primary: #ffffff;
  --text-secondary: rgba(255, 255, 255, 0.65);
  --text-muted: rgba(255, 255, 255, 0.4);
  --text-faint: rgba(255, 255, 255, 0.35);
  --border-color: rgba(255, 255, 255, 0.06);
  --accent: #4ade80;
  --accent-bg: rgba(74, 222, 128, 0.12);
  --hover-bg: rgba(255, 255, 255, 0.06);
  --control-bg: rgba(255, 255, 255, 0.05);
  --icon-color: rgba(255, 255, 255, 0.55);
  --icon-hover: #ffffff;
}

.light-theme {
  --bg-primary: #f5f5f7;
  --bg-secondary: #ffffff;
  --bg-card: #ffffff;
  --text-primary: #1a1a2e;
  --text-secondary: rgba(0, 0, 0, 0.65);
  --text-muted: rgba(0, 0, 0, 0.4);
  --text-faint: rgba(0, 0, 0, 0.35);
  --border-color: rgba(0, 0, 0, 0.08);
  --accent: #16a34a;
  --accent-bg: rgba(22, 163, 74, 0.1);
  --hover-bg: rgba(0, 0, 0, 0.04);
  --control-bg: rgba(0, 0, 0, 0.05);
  --icon-color: rgba(0, 0, 0, 0.55);
  --icon-hover: #1a1a2e;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  transition: background 0.3s, color 0.3s;
}

#app { height: 100vh; width: 100%; }

.app-container { height: 100vh; width: 100%; }

.sidebar {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
  height: 100vh;
  transition: background 0.3s, border-color 0.3s;
}

.logo {
  padding: 20px 18px;
  border-bottom: 1px solid var(--border-color);
}

.logo h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--text-primary);
}

.logo p {
  margin: 4px 0 0 0;
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.3px;
}

.menu-group-label {
  padding: 16px 20px 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.sidebar-menu { border-right: none; background: transparent !important; }

.sidebar-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
}

/* 菜单名称完整显示：不换行、不省略 */
.sidebar-menu :deep(.el-menu-item span) {
  flex: 1;
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--hover-bg);
  color: var(--text-primary);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--accent-bg);
  color: var(--accent);
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 16px;
  margin-right: 10px;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header {
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 20px;
  height: 52px !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: background 0.3s, border-color 0.3s;
}

.header :deep(.el-header) {
  height: 52px !important;
  padding: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb {
  font-size: 13px;
  color: var(--text-muted);
}

.sep {
  font-size: 13px;
  color: var(--text-faint);
}

.current-page {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 语言切换器 */
.lang-switch {
  display: flex;
  align-items: center;
  background: var(--control-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 2px;
}

.lang-btn {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  font-family: 'Inter', sans-serif;
  padding: 3px 9px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.lang-btn:hover { color: var(--text-primary); }

.lang-btn.active {
  background: var(--accent);
  color: #06120a;
}

.theme-toggle {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.header-icon {
  font-size: 18px;
  color: var(--icon-color);
  cursor: pointer;
  transition: color 0.2s;
}

.header-icon:hover { color: var(--icon-hover); }

/* 用户芯片 */
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--control-bg);
  transition: border-color 0.2s, background 0.2s;
}

.user-chip:hover {
  border-color: rgba(74, 222, 128, 0.35);
  background: rgba(74, 222, 128, 0.06);
}

.user-chip-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  color: #06120a;
  background: var(--accent);
}

.user-chip-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-arrow {
  font-size: 11px;
  color: var(--text-muted);
}

.login-btn {
  border-color: rgba(74, 222, 128, 0.4);
  color: var(--accent);
  background: transparent;
}

.login-btn:hover {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
}

.main-content {
  background: var(--bg-primary);
  padding: 16px;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  transition: background 0.3s;
}

/* 全局登录引导弹窗 */
.login-prompt-body {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.login-prompt-icon {
  font-size: 26px;
  color: var(--accent);
  flex-shrink: 0;
  margin-top: 2px;
}

.login-prompt-body p {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
}
</style>
