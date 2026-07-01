<template>
  <div class="app-container">
    <el-container>
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h2>EVOLUTION AI</h2>
          <p>A级曲面开发平台</p>
        </div>
        <el-menu :default-active="activeMenu" class="sidebar-menu">
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/designer">
            <el-icon><Palette /></el-icon>
            <span>模型生成</span>
          </el-menu-item>
          <el-menu-item index="/projects">
            <el-icon><FolderOpened /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/models">
            <el-icon><Picture /></el-icon>
            <span>模型管理</span>
          </el-menu-item>
          <el-menu-item index="/export">
            <el-icon><Download /></el-icon>
            <span>模型导出</span>
          </el-menu-item>
          <el-menu-item index="/variants">
            <el-icon><GitBranch /></el-icon>
            <span>模型变体</span>
          </el-menu-item>
          <el-menu-item index="/workflow">
            <el-icon><List /></el-icon>
            <span>工作流</span>
          </el-menu-item>
          <el-menu-item index="/quality">
            <el-icon><CheckCircle /></el-icon>
            <span>质量检查</span>
          </el-menu-item>
          <el-menu-item index="/parameters">
            <el-icon><Setting /></el-icon>
            <span>参数管理</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <span>报告中心</span>
          </el-menu-item>
          <el-menu-item index="/handover">
            <el-icon><Upload /></el-icon>
            <span>数据交接</span>
          </el-menu-item>
          <el-menu-item index="/modify">
            <el-icon><Edit /></el-icon>
            <span>模型修改</span>
          </el-menu-item>
          <el-menu-item index="/demo">
            <el-icon><VideoPlay /></el-icon>
            <span>DEMO演示</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="header">
          <div class="header-content">
            <span class="title">{{ currentTitle }}</span>
            <div class="header-right">
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
import {
  HomeFilled,
  FolderOpened,
  Picture,
  List,
  CheckCircle,
  Setting,
  Document,
  Upload,
  Bell,
  Edit,
  VideoPlay,
  Palette,
  Download,
  GitBranch
} from '@element-plus/icons-vue'

const router = useRouter()

const notificationCount = ref(3)

const activeMenu = computed(() => {
  return router.currentRoute.value.path
})

const currentTitle = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/designer': '模型生成',
    '/projects': '项目管理',
    '/models': '模型管理',
    '/export': '模型导出',
    '/variants': '模型变体',
    '/workflow': '工作流',
    '/quality': '质量检查',
    '/parameters': '参数管理',
    '/reports': '报告中心',
    '/handover': '数据交接',
    '/modify': '模型修改',
    '/demo': 'DEMO演示'
  }
  return titles[router.currentRoute.value.path] || 'EVOLUTION AI'
})
</script>

<style>
.app-container {
  height: 100vh;
  width: 100%;
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
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
}

.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.8);
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
}
</style>