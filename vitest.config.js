import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 5173,
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
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.{test,spec}.{ts,js}', 'src/**/*.{test,spec}.{ts,js}'],
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
