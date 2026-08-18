import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 端口配置说明：
// - 默认端口 5173，可通过环境变量 VITE_PORT 覆盖
// - strictPort: false 确保端口被占用时自动切换（5174, 5175...）
// - base: './' 使用相对路径，确保生产部署时的可移植性
export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: parseInt(process.env.VITE_PORT) || 5173,
    strictPort: false,
    host: 'localhost',
    proxy: {
      '/api/ide': {
        target: 'https://trae-api-cn.mchost.guru',
        changeOrigin: true,
        secure: false
      },
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: parseInt(process.env.VITE_PREVIEW_PORT) || 4173,
    strictPort: false
  },
  build: {
    assetsDir: 'assets',
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('three')) {
            return 'three'
          }
          if (id.includes('element-plus')) {
            return 'element-plus'
          }
          if (id.includes('vue') && !id.includes('/src/')) {
            return 'vue'
          }
          if (id.includes('markdown-it')) {
            return 'markdown-it'
          }
          if (id.includes('axios')) {
            return 'axios'
          }
        }
      }
    }
  }
})
