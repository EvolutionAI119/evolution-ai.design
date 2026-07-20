import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 3000,
    proxy: {
      '/api/ide': {
        target: 'https://trae-api-cn.mchost.guru',
        changeOrigin: true,
        secure: false
      },
      '/api/v1': {
        target: 'http://localhost:8001',
        changeOrigin: true
      }
    }
  },
  build: {
    assetsDir: 'assets',
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
