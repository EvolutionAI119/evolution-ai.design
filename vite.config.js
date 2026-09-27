import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'

// 让仓库根的 docs/ 目录在前端可访问：
//  - 开发态：通过 dev server 中间件直接读取磁盘 docs/
//  - 构建态：将 docs/*.md / *.pdf / *.html 复制到 dist/docs/
// 这样 Help 模块可以 fetch 并渲染知识库文档原文。
const docsPlugin = {
  name: 'serve-docs',
  configureServer(server) {
    const docsRoot = path.resolve(__dirname, 'docs')
    server.middlewares.use((req, res, next) => {
      if (!req.url || !req.url.startsWith('/docs/')) return next()
      const rel = decodeURIComponent(req.url.slice('/docs/'.length).split('?')[0])
      const file = path.join(docsRoot, rel)
      if (!file.startsWith(docsRoot) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        return next()
      }
      const ext = path.extname(file).toLowerCase()
      const types = {
        '.md': 'text/markdown; charset=utf-8',
        '.pdf': 'application/pdf',
        '.html': 'text/html; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.png': 'image/png'
      }
      res.setHeader('Content-Type', types[ext] || 'application/octet-stream')
      fs.createReadStream(file).pipe(res)
    })
  },
  writeBundle() {
    const src = path.resolve(__dirname, 'docs')
    const dst = path.resolve(__dirname, 'dist', 'docs')
    if (!fs.existsSync(src)) return
    // 递归复制（含 docs/en/ 英文伴生文档），仅复制可发布的文档类型
    const copyDir = (from, to) => {
      fs.mkdirSync(to, { recursive: true })
      for (const name of fs.readdirSync(from)) {
        const s = path.join(from, name), d = path.join(to, name)
        if (fs.statSync(s).isDirectory()) copyDir(s, d)
        else if (/\.(md|pdf|html|svg|png)$/i.test(name)) fs.copyFileSync(s, d)
      }
    }
    copyDir(src, dst)
  }
}

// 端口配置说明：
// - 默认端口 5173，可通过环境变量 VITE_PORT 覆盖
// - strictPort: false 确保端口被占用时自动切换（5174, 5175...）
// - base: './' 使用相对路径，确保生产部署时的可移植性
export default defineConfig({
  plugins: [vue(), docsPlugin],
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
