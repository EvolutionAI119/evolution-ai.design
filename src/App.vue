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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Odometer, Brush, Folder, MagicStick, CircleCheck, Upload, VideoPlay, Bell, Setting
} from '@element-plus/icons-vue'

const router = useRouter()

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
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0a0a0f;
  color: #fff;
}

#app { height: 100vh; width: 100%; }

.app-container { height: 100vh; width: 100%; }

.sidebar {
  background: #12121a;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  overflow-y: auto;
  height: 100vh;
}

.logo {
  padding: 20px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.logo h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #fff;
}

.logo p {
  margin: 4px 0 0 0;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.3px;
}

.menu-group-label {
  padding: 16px 20px 6px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.sidebar-menu { border-right: none; background: transparent !important; }

.sidebar-menu :deep(.el-menu-item) {
  height: 40px;
  line-height: 40px;
  margin: 2px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: rgba(74, 222, 128, 0.12);
  color: #4ade80;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 16px;
  margin-right: 10px;
}

.header {
  background: #12121a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0 20px;
  height: 52px !important;
}

.header :deep(.el-header) { height: 52px !important; }

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.sep {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.2);
}

.current-page {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.55);
  cursor: pointer;
  transition: color 0.2s;
}

.header-icon:hover { color: #fff; }

.main-content {
  background: #0a0a0f;
  padding: 16px;
  width: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
