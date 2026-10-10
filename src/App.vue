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

            <!-- 通知中心（仅登录用户） -->
            <el-popover
              v-if="auth.isAuthenticated"
              v-model:visible="notifVisible"
              placement="bottom-end"
              :width="360"
              trigger="click"
              popper-class="notif-popper"
              @show="loadNotifications"
            >
              <template #reference>
                <div class="notif-trigger">
                  <el-badge
                    :value="unreadCount"
                    :hidden="unreadCount === 0"
                    :max="99"
                  >
                    <el-icon class="header-icon"><Bell /></el-icon>
                  </el-badge>
                </div>
              </template>
              <div class="notif-panel">
                <div class="notif-header">
                  <span class="notif-title">{{ t('notify.title') }}</span>
                  <el-button
                    v-if="unreadCount > 0"
                    size="small" text type="primary"
                    @click="readAll"
                  >{{ t('notify.readAll') }}</el-button>
                </div>
                <div class="notif-list" v-loading="notifLoading">
                  <el-empty
                    v-if="!notifications.length && !notifLoading"
                    :description="t('notify.empty')"
                    :image-size="60"
                  />
                  <div
                    v-for="n in notifications"
                    :key="n.id"
                    class="notif-item"
                    :class="{ unread: !n.is_read }"
                    @click="openNotification(n)"
                  >
                    <span class="notif-dot" v-if="!n.is_read"></span>
                    <div class="notif-body">
                      <div class="notif-item-title">{{ n.title }}</div>
                      <div class="notif-item-text" v-if="n.body">{{ n.body }}</div>
                      <div class="notif-time">{{ formatNotifTime(n.created_at) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </el-popover>

            <!-- 账号模块封存期：用户菜单/登录入口已移除（Contact 页在侧栏） -->
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
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Odometer, Brush, Folder, MagicStick, CircleCheck, Upload, VideoPlay,
  Bell, Moon, Sunny, QuestionFilled, ChatDotRound, Message, Setting,
  Promotion,
} from '@element-plus/icons-vue'
// Element Plus 内置语言包
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import enLocale from 'element-plus/dist/locale/en.mjs'
import { useAuthStore } from './stores/auth'
import { analyticsAPI } from './api'
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

// 登录页采用全屏独立布局（封存期 Login 路由已移除，此处恒为 false，保留以兼容复启）
const isLoginRoute = computed(() => route.name === 'Login')

const userInitial = computed(() => {
  const name = auth.user?.username || 'U'
  return name.slice(0, 1).toUpperCase()
})

// 账号模块封存期：登录引导弹窗/用户菜单指令处理已随模板一并移除

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

// ── 通知中心（登录用户） ──────────────────────
const notifVisible = ref(false)
const notifLoading = ref(false)
const notifications = ref([])
const unreadCount = ref(0)
let notifTimer = null

const formatNotifTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const pollUnreadCount = async () => {
  if (!auth.isAuthenticated) return
  try {
    const { data } = await analyticsAPI.unreadCount()
    unreadCount.value = data.unread_count
  } catch { /* 静默失败，不打断用户 */ }
}

const loadNotifications = async () => {
  notifLoading.value = true
  try {
    const { data } = await analyticsAPI.listNotifications(20)
    notifications.value = data.items
    unreadCount.value = data.unread_count
  } catch { /* 静默 */ } finally {
    notifLoading.value = false
  }
}

const openNotification = async (n) => {
  if (!n.is_read) {
    try {
      await analyticsAPI.markNotificationRead(n.id)
      n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch { /* 静默 */ }
  }
  notifVisible.value = false
  if (n.link) router.push(n.link)
}

const readAll = async () => {
  try {
    await analyticsAPI.markAllNotificationsRead()
    notifications.value.forEach((n) => { n.is_read = true })
    unreadCount.value = 0
  } catch { /* 静默 */ }
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light') {
    isDark.value = false
    document.documentElement.classList.add('light-theme')
  }
  document.documentElement.setAttribute('lang', locale.value === 'zh' ? 'zh-CN' : 'en')
  // 启动访问埋点（路由切换自动上报 + 停留时长）
  tracker.start(router)
  // 通知未读数轮询（60s）；游客模式下命中内置 guest 账户
  pollUnreadCount()
  notifTimer = setInterval(pollUnreadCount, 60000)
})

onBeforeUnmount(() => {
  tracker.stop()
  if (notifTimer) clearInterval(notifTimer)
})

const baseMenuGroups = [
  {
    labelKey: 'menu.groupHome',
    items: [
      { path: '/', nameKey: 'menu.dashboard', icon: Odometer }
    ]
  },
  {
    labelKey: 'menu.groupDesign',
    items: [
      { path: '/copilot', nameKey: 'menu.copilot', icon: Promotion },
      { path: '/designer', nameKey: 'menu.aiDesigner', icon: Brush },
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
    labelKey: 'menu.groupExplore',
    items: [
      { path: '/demo', nameKey: 'menu.demo', icon: VideoPlay },
      { path: '/community', nameKey: 'menu.community', icon: ChatDotRound }
    ]
  },
  {
    labelKey: 'menu.groupSupport',
    items: [
      { path: '/help', nameKey: 'menu.help', icon: QuestionFilled },
      { path: '/contact', nameKey: 'menu.contact', icon: Message }
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

/* 通知中心 */
.notif-trigger { display: flex; align-items: center; cursor: pointer; }

.notif-panel { display: flex; flex-direction: column; }

.notif-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 4px;
}

.notif-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }

.notif-list {
  max-height: 380px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.notif-item:hover { background: rgba(255, 255, 255, 0.04); }
html.light-theme .notif-item:hover { background: rgba(0, 0, 0, 0.04); }

.notif-item.unread .notif-item-title { font-weight: 700; }

.notif-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
  margin-top: 6px;
}

.notif-body { flex: 1; min-width: 0; }
.notif-item-title { font-size: 13px; color: var(--text-primary); line-height: 1.4; }
.notif-item-text {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.notif-time { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

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
