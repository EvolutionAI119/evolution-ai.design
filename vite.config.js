import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置：端口3000，代理 /api 到后端8000
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
