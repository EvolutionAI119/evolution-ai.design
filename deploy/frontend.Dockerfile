# =========================================================================
#  Evolution-Ai.Design — Frontend Dockerfile (Vue 3 + Vite → Nginx)
#  多阶段构建：
#    stage 1 (builder):  node:20-alpine → npm ci → vite build
#    stage 2 (runtime):  nginx:alpine    → 托管 dist/ + 反代 /api/v1 → backend:8000
# =========================================================================

# ----------------------------- builder -----------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# 1) 先 copy package 描述文件 → npm ci（比 install 更可复现）
COPY package.json package-lock.json ./

# 可选：国内 npm 镜像 —— 构建时传 --build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_REGISTRY=
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi ; \
    npm ci --no-audit --no-fund

# 2) 其余源码 + 静态资源（public/brands/ 等）→ vite build
COPY . .
RUN npm run build

# 构建后产物目录：/app/dist

# ----------------------------- runtime -----------------------------
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="evolution-ai-design-frontend" \
      org.opencontainers.image.description="EVOLUTION AI - 前端（Vue 3 + Element Plus，Nginx 静态托管 + 反代 /api/v1）"

# 1) 复制自定义 nginx.conf（含 gzip、安全头、/api/v1 反代、SPA 回退到 index.html）
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/default.conf.template /etc/nginx/templates/default.conf.template

# 2) 复制静态资源
COPY --from=builder /app/dist /usr/share/nginx/html

# 3) 前端只监听 80；HTTPS/证书请在外部反代（Traefik/Nginx/Caddy/Cloudflare）处理
EXPOSE 80

# 4) 健康检查：HTTP HEAD / （nginx 返回 200 即可）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
