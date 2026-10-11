// 独立管理后台构建配置
// 产物落入 backend/app/static/admin，由 FastAPI StaticFiles 在 /admin 提供；
// 主站 dist（gh-pages）不包含任何 Admin 代码。
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'

// 入口 HTML 随源文件名输出为 admin.html；StaticFiles 需要 index.html，
// 构建结束后补一份同名 index.html（内容完全一致）。
const renameEntryPlugin = {
  name: 'admin-entry-index',
  closeBundle() {
    const outDir = path.resolve(__dirname, 'backend/app/static/admin')
    const src = path.join(outDir, 'admin.html')
    const dst = path.join(outDir, 'index.html')
    if (fs.existsSync(src)) fs.copyFileSync(src, dst)
  }
}

export default defineConfig({
  plugins: [vue(), renameEntryPlugin],
  // /admin/ 为 FastAPI 挂载前缀；所有资源按该绝对基址解析
  base: '/admin/',
  // 不拷贝 public/：其中 CNAME/_preview/mp4 为主站素材，后台不需要
  publicDir: false,
  build: {
    outDir: path.resolve(__dirname, 'backend/app/static/admin'),
    assetsDir: 'assets',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: path.resolve(__dirname, 'admin.html'),
      output: {
        manualChunks(id) {
          if (id.includes('echarts')) return 'echarts'
          if (id.includes('three')) return 'three'
          if (id.includes('element-plus')) return 'element-plus'
          if (id.includes('vue') && !id.includes('/src/')) return 'vue'
          if (id.includes('axios')) return 'axios'
        }
      }
    }
  }
})
