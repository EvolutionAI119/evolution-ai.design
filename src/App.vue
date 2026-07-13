<template>
  <div class="app-container">
    <el-container>
      <el-aside width="230px" class="sidebar">
        <div class="logo">
          <h2>EVOLUTION AI</h2>
          <p>{{ $t('app.subtitle') }}</p>
        </div>
        <el-menu :default-active="activeMenu" router class="sidebar-menu" background-color="transparent" text-color="rgba(255,255,255,0.8)" active-text-color="#00d9ff">
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>{{ $t('app.dashboard') }}</span>
          </el-menu-item>
          <el-menu-item index="/designer">
            <el-icon><Brush /></el-icon>
            <span>{{ $t('app.designer') }}</span>
          </el-menu-item>
          <el-menu-item index="/projects">
            <el-icon><FolderOpened /></el-icon>
            <span>{{ $t('app.projects') }}</span>
          </el-menu-item>
          <el-menu-item index="/models">
            <el-icon><Picture /></el-icon>
            <span>{{ $t('app.models') }}</span>
          </el-menu-item>
          <el-menu-item index="/export">
            <el-icon><Download /></el-icon>
            <span>{{ $t('app.export') }}</span>
          </el-menu-item>
          <el-menu-item index="/variants">
            <el-icon><RefreshRight /></el-icon>
            <span>{{ $t('app.variants') }}</span>
          </el-menu-item>
          <el-menu-item index="/workflow">
            <el-icon><List /></el-icon>
            <span>{{ $t('app.workflow') }}</span>
          </el-menu-item>
          <el-menu-item index="/quality">
            <el-icon><CircleCheck /></el-icon>
            <span>{{ $t('app.quality') }}</span>
          </el-menu-item>
          <el-menu-item index="/parameters">
            <el-icon><Setting /></el-icon>
            <span>{{ $t('app.parameters') }}</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <span>{{ $t('app.reports') }}</span>
          </el-menu-item>
          <el-menu-item index="/handover">
            <el-icon><Upload /></el-icon>
            <span>{{ $t('app.handover') }}</span>
          </el-menu-item>
          <el-menu-item index="/modify">
            <el-icon><Edit /></el-icon>
            <span>{{ $t('app.modify') }}</span>
          </el-menu-item>
          <el-menu-item index="/demo">
            <el-icon><VideoPlay /></el-icon>
            <span>{{ $t('app.demo') }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container class="main-container">
        <el-header class="header">
          <div class="header-content">
            <span class="title">{{ currentTitle }}</span>
            <div class="header-right">
              <el-select
                v-model="currentLang"
                class="lang-select"
                @change="switchLang"
              >
                <el-option label="中文" value="zh" />
                <el-option label="English" value="en" />
              </el-select>
              <el-badge :value="notificationCount" class="notification">
                <el-icon class="avatar"><Bell /></el-icon>
              </el-badge>
            </div>
          </div>
        </el-header>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  HomeFilled,
  FolderOpened,
  Picture,
  List,
  CircleCheck,
  Setting,
  Document,
  Upload,
  Bell,
  Edit,
  VideoPlay,
  Brush,
  Download,
  RefreshRight
} from '@element-plus/icons-vue'

const router = useRouter()
const { t, locale } = useI18n()

const notificationCount = ref(3)
const currentLang = ref(localStorage.getItem('language') || locale.value)

const activeMenu = computed(() => {
  return router.currentRoute.value.path
})

const isDemoPage = computed(() => {
  return router.currentRoute.value.path === '/demo'
})

const currentTitle = computed(() => {
  const titles = {
    '/': 'app.dashboard',
    '/designer': 'app.designer',
    '/projects': 'app.projects',
    '/models': 'app.models',
    '/export': 'app.export',
    '/variants': 'app.variants',
    '/workflow': 'app.workflow',
    '/quality': 'app.quality',
    '/parameters': 'app.parameters',
    '/reports': 'app.reports',
    '/handover': 'app.handover',
    '/modify': 'app.modify',
    '/demo': 'app.demo'
  }
  const key = titles[router.currentRoute.value.path]
  return key ? t(key) : 'EVOLUTION AI'
})

const switchLang = (lang) => {
  locale.value = lang
  currentLang.value = lang
  localStorage.setItem('language', lang)
  window.location.reload()
}
</script>

<style>
.app-container {
  height: 100vh;
  width: 100%;
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  overflow-y: auto;
  height: 100vh;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo h2 {
  margin: 0;
  font-size: 20px;
  font-weight: bold;
  background: linear-gradient(90deg, #00d9ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.logo p {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.sidebar-menu {
  border-right: none;
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.8);
  overflow: visible;
  white-space: nowrap;
  text-overflow: unset;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(0, 217, 255, 0.1);
  color: #00d9ff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(0, 217, 255, 0.2), transparent);
  color: #00d9ff;
  border-left: 3px solid #00d9ff;
}

.header {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.notification {
  cursor: pointer;
}

.avatar {
  font-size: 24px;
  color: #666;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

.main-container.demo-fullscreen {
  flex: 1;
}
</style>