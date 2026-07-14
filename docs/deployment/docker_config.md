# Docker配置与部署指南

## 1. 概述

EVOLUTION AI支持Docker容器化部署，提供完整的Dockerfile和docker-compose配置。

## 2. Docker环境要求

| 组件 | 版本要求 |
|------|----------|
| Docker | >= 20.10 |
| Docker Compose | >= 2.0 |
| 操作系统 | Linux/Ubuntu 20.04+ / Windows 10+ |

## 3. Dockerfile配置

### 3.1 后端Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 前端Dockerfile

```dockerfile
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 3.3 nginx.conf配置

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    server {
        listen 80;
        server_name evolution-ai.design;
        
        root /usr/share/nginx/html;
        index index.html;
        
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        location /ws/ {
            proxy_pass http://backend:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
        
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    }
}
```

## 4. docker-compose配置

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: evolution-ai-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/evolution.db
      - MODELS_PATH=/app/data/models
      - REPORTS_PATH=/app/data/reports
      - EXPORTS_PATH=/app/data/exports
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: evolution-ai-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: evolution-ai-nginx
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
    restart: unless-stopped
```

## 5. 环境变量配置

### 5.1 后端环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | sqlite:///./data/evolution.db | 数据库连接URL |
| MODELS_PATH | ./data/models | 模型文件存储路径 |
| REPORTS_PATH | ./data/reports | 报告文件存储路径 |
| EXPORTS_PATH | ./data/exports | 导出文件存储路径 |
| DEFAULT_LANGUAGE | zh-CN | 默认语言 |
| SUPPORTED_LANGUAGES | zh-CN,en-US | 支持的语言列表 |

### 5.2 .env文件示例

```env
DATABASE_URL=sqlite:///./data/evolution.db
MODELS_PATH=./data/models
REPORTS_PATH=./data/reports
EXPORTS_PATH=./data/exports
DEFAULT_LANGUAGE=zh-CN
SUPPORTED_LANGUAGES=zh-CN,en-US
```

## 6. 部署步骤

### 6.1 本地开发部署

```bash
# 克隆仓库
git clone https://github.com/EvolutionAI119/evolution-ai.design.git
cd evolution-ai.design

# 创建数据目录
mkdir -p data/models data/reports data/exports

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 6.2 生产环境部署

```bash
# 创建SSL证书目录
mkdir -p ssl

# 生成SSL证书（使用Let's Encrypt）
certbot certonly --webroot -w /usr/share/nginx/html -d evolution-ai.design

# 复制证书到SSL目录
cp /etc/letsencrypt/live/evolution-ai.design/fullchain.pem ssl/
cp /etc/letsencrypt/live/evolution-ai.design/privkey.pem ssl/

# 更新nginx配置支持HTTPS
docker-compose up -d --build
```

### 6.3 手动启动（不使用Docker）

```bash
# 后端启动
cd backend
pip install -r requirements.txt
python start.py

# 前端启动
npm install
npm run dev
```

## 7. 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 构建镜像
docker-compose build

# 更新服务
git pull
docker-compose up -d --build
```

## 8. 数据库配置

### 8.1 SQLite（默认）

```python
# config.py
DATABASE_URL = "sqlite:///./data/evolution.db"
```

### 8.2 PostgreSQL（生产环境）

```python
# config.py
DATABASE_URL = "postgresql://user:password@localhost/evolution"
```

### 8.3 MySQL

```python
# config.py
DATABASE_URL = "mysql+pymysql://user:password@localhost/evolution"
```

## 9. 性能优化

### 9.1 资源限制

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 9.2 缓存配置

```nginx
# nginx.conf
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 10. 安全配置

### 10.1 CORS配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://evolution-ai.design"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 10.2 Rate Limiting

```python
# 安装依赖
pip install slowapi uvicorn

# 添加限速
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/car/generate")
@limiter.limit("10/minute")
async def generate_car():
    pass
```

## 11. 监控与日志

### 11.1 健康检查

```bash
# 检查后端健康
curl http://localhost:8000/api/v1/health

# 检查前端健康
curl http://localhost:80/
```

### 11.2 日志收集

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

## 12. CI/CD配置

### 12.1 GitHub Actions

```yaml
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: docker-compose build
      
      - name: Run tests
        run: docker-compose run backend pytest
      
      - name: Deploy to production
        uses: appleboy/ssh-action@v0.1.4
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd evolution-ai.design
            git pull
            docker-compose up -d --build
```

## 13. 备份与恢复

### 13.1 数据库备份

```bash
# 备份SQLite数据库
docker exec evolution-ai-backend sqlite3 /app/data/evolution.db .backup /app/data/backup.sqlite

# 备份PostgreSQL数据库
docker exec evolution-ai-backend pg_dump -U user evolution > /app/data/backup.sql
```

### 13.2 数据恢复

```bash
# 恢复SQLite数据库
docker exec evolution-ai-backend sqlite3 /app/data/evolution.db < /app/data/backup.sqlite

# 恢复PostgreSQL数据库
docker exec -i evolution-ai-backend psql -U user evolution < /app/data/backup.sql
```

## 14. 故障排查

### 14.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 端口被占用 | 8000/80端口已被其他服务占用 | 修改docker-compose端口映射 |
| 数据库连接失败 | 数据目录权限不足 | 执行chmod -R 777 data |
| 前端无法访问API | 反向代理配置错误 | 检查nginx.conf配置 |
| Docker构建失败 | 网络问题导致依赖下载失败 | 使用国内镜像源 |

### 14.2 日志查看

```bash
# 查看所有日志
docker-compose logs

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 查看nginx日志
docker-compose logs -f nginx
```