<template>
  <div class="app-container">
    <el-container>
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h2>EVOLUTION AI</h2>
          <p>Class A Surface Development Platform</p>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
          background-color="transparent"
          text-color="rgba(255,255,255,0.7)"
          active-text-color="#4ade80"
        >
          <template #default>
            <template v-for="group in menuGroups" :key="group.label">
              <div v-if="group.label" class="menu-group-label">{{ group.label }}</div>
              <el-menu-item
                v-for="item in group.items"
                :key="item.path"
                :index="item.path"
              >
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.name }}</span>
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
            <div class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换到浅色模式' : '切换到深色模式'">
              <el-icon class="header-icon"><component :is="isDark ? Moon : Sunny" /></el-icon>
            </div>
            <el-icon class="header-icon"><Bell /></el-icon>
            <el-icon class="header-icon"><Setting /></el-icon>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Odometer, Brush, Folder, MagicStick, CircleCheck, Upload, VideoPlay, Bell, Setting, Moon, Sunny
} from '@element-plus/icons-vue'

const router = useRouter()

const isDark = ref(true)

const toggleTheme = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('light-theme', !isDark.value)
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  const saved = localStorage.getItem('theme')
  if (saved === 'light') {
    isDark.value = false
    document.documentElement.classList.add('light-theme')
  }
})

const menuGroups = [
  {
    label: '',
    items: [
      { path: '/', name: 'Dashboard', icon: Odometer },
      { path: '/designer', name: 'AI Designer', icon: Brush }
    ]
  },
  {
    label: 'Design',
    items: [
      { path: '/projects', name: 'Projects', icon: Folder },
      { path: '/deep-learning', name: 'Deep Learning Designer', icon: MagicStick }
    ]
  },
  {
    label: 'Workflow',
    items: [
      { path: '/quality', name: 'Quality', icon: CircleCheck },
      { path: '/deliver', name: 'Deliver', icon: Upload }
    ]
  },
  {
    label: '',
    items: [
      { path: '/demo', name: 'DEMO', icon: VideoPlay }
    ]
  }
]

const allMenuItems = menuGroups.flatMap(g => g.items)

const activeMenu = computed(() => router.currentRoute.value.path)

const currentPageName = computed(() => {
  const item = allMenuItems.find(m => m.path === router.currentRoute.value.path)
  return item ? item.name : 'AI Designer'
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
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
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

.main-content {
  background: var(--bg-primary);
  padding: 16px;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  transition: background 0.3s;
}
</style>
