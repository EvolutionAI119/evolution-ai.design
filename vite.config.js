import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// 端口配置说明：
// - 默认端口 5173，可通过环境变量 VITE_PORT 覆盖
// - strictPort: false 确保端口被占用时自动切换（5174, 5175...）
// - base: './' 使用相对路径，确保生产部署时的可移植性
export default defineConfig({
  plugins: [vue()],
  base: './',
  // 单元/集成测试：jsdom 提供 localStorage / location，测试文件放 src/tests
  test: {
    environment: 'jsdom',
    include: ['src/tests/**/*.spec.js']
  },
  server: {
    port: parseInt(process.env.VITE_PORT) || 5173,
    strictPort: false,
    // 显式监听 IPv4 的 127.0.0.1，避免 Vite 5 在 Win 上只绑 [::1]
    // 导致“localhost / 预览器”按 IPv4 访问时出现「服务不可用」占位页
    host: '127.0.0.1',
    proxy: {
      '/api/ide': {
        target: 'https://trae-api-cn.mchost.guru',
        changeOrigin: true,
        secure: false
      },
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: parseInt(process.env.VITE_PREVIEW_PORT) || 4173,
    strictPort: false,
    host: '127.0.0.1'
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
