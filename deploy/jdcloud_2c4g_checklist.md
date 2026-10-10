# 京东云 2C4G 一键部署清单（EVOLUTION AI）

> 目标：内地合规部署，微信扫码登录数据不出境，本机回归纯开发机。
> 适用：京东云轻量云主机 2C4G / 60G SSD / 5M / 500G月流量，Ubuntu 22.04 LTS。
> 执行顺序不可乱：先买机 → 备案 → DNS → 部署 → 微信后台。

---

## 第 0 步 · 域名转移 + 购买 + 备案（总周期约 1 个月+，最先启动）

- [ ] **域名转入境内注册商**（工信部硬性要求：境外注册商 Spaceship 不能直接备案）
  - [ ] 先查 `.design` 后缀在 [工信部域名公示页](https://domain.miit.gov.cn/) 的批复状态（2018 年已批复，操作前再确认一次）
  - [ ] 确认域名注册已满 60 天（ICANN 转移锁）；在 Spaceship 控制台解锁 `clientTransferProhibited`、获取转移码
  - [ ] 在京东云（或选定的云厂商）发起域名转入，5-7 天完成；转入后立即做**实名认证**（再等 2-3 天入库工信部）
  - [ ] 注意：转移期间 DNS 不能动，GitHub Pages 照常运行不受影响
- [ ] 购买：京东云轻量云主机 **2C4G 5M**，系统镜像选 **Ubuntu 22.04**，地域选离用户近的（华北-北京/华东-宿迁）
  - 活动入口：京东云「AI焕新季」（至 2026-10-31），新客 2C4G ≈ ¥199/年，个人可买；**建议直接 3 年付锁价，珍惜新客资格**
- [ ] 防火墙/安全组放行：`22`（SSH）、`80`、`443`
- [ ] 京东云备案小程序提交 **ICP 备案**（域名实名信息须与备案主体一致）
  - 备案期间 80/443 不通属正常；本机 + Cloudflare Tunnel 方案继续开发不受影响

## 第 1 步 · DNS 解析（备案通过后）

在域名 DNS 控制台（`evolution-ai.design` 当前解析商处）添加：

| 记录 | 类型 | 值 |
|---|---|---|
| `@` | A | 京东云服务器公网 IP |
| `www` | A | 京东云服务器公网 IP |

> 不需要 api 子域——nginx 同域反代 `/api`，微信回调与站点同域，少签一张证书。

## 第 2 步 · 服务器初始化（一条命令）

```bash
ssh root@<服务器IP>
curl -fsSL https://<仓库raw地址>/deploy/server_bootstrap.sh -o bootstrap.sh
bash bootstrap.sh        # 装 Docker、配 2G swap、DaoCloud 加速器、时区
```

> 若仓库未公开，把 `deploy/server_bootstrap.sh` 内容粘贴保存后 `bash` 执行。
> 2C4G 必须开 swap：PG + Redis + 双 uvicorn worker 峰值接近 3G，无 swap 会 OOM。

## 第 3 步 · 本机构建前端并上传（Windows 本机执行）

```powershell
npm ci
npm run build            # 生成 dist/
# 上传代码（二选一）：
#   a) git push 后服务器 git clone（推荐）
#   b) scp -r dist root@<IP>:/opt/evoai/dist   +  git clone 其余
```

## 第 4 步 · 服务器部署（SSH 上执行）

```bash
mkdir -p /opt/evoai && cd /opt/evoai
git clone https://github.com/EvolutionAI119/evolution-ai.design.git .
# 或把本机 dist 放到 /opt/evoai/dist（dist 已 gitignore，不会随 clone 带上来）

# ---- 根目录 .env（给 docker compose 读，gitignored）----
cat > .env <<'EOF'
POSTGRES_PASSWORD=<随机32位>
REDIS_PASSWORD=<随机32位>
EOF

# ---- 后端密钥 backend/.env（gitignored，复制 .env.example 修改）----
cp backend/.env.example backend/.env
# 必须改以下键（用 openssl rand -hex 32 生成 SECRET_KEY）：
#   SECRET_KEY=<随机32位>        ← 默认值会触发 fail-fast 拒绝启动
#   MP_APPID / MP_SECRET=<微信测试号/公众号凭证>
#   MP_REDIRECT_URI=https://evolution-ai.design/api/v1/auth/mp/callback
#   FRONTEND_URL=https://evolution-ai.design
#   EVOAI_REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/0

# ---- 启动（无 TLS 先跑通）----
docker compose up -d --build
docker compose exec backend bash -c "cd /app/backend && alembic upgrade head"

# ---- 验证 ----
curl http://127.0.0.1:8000/api/v1/auth/methods     # 返回 JSON 即后端 OK
curl http://127.0.0.1/                             # 返回 index.html 即前端 OK
```

## 第 5 步 · TLS 证书（https 必须，微信授权强制）

```bash
# 用现有 prod overlay + certbot 一键签发（需先停 nginx 释放 80，或按 yml 注释走 8080 webroot）
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot certonly \
  --standalone -d evolution-ai.design -d www.evolution-ai.design \
  --email <邮箱> --agree-tos --non-interactive
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

curl -I https://evolution-ai.design/                        # 200
curl https://evolution-ai.design/api/v1/auth/methods        # JSON
```

## 第 6 步 · 微信后台（最后一次配置，永久不变）

- [ ] 微信公众平台（测试号/公众号）→「网页授权获取用户基本信息」域名填：**`evolution-ai.design`**
- [ ] 手机微信扫码 → 确认 → PC 自动登录，全链路验收

## 第 7 步 ·（可选）本机历史数据迁移

```powershell
# 本机执行：把 SQLite 老数据迁入云上 PG（幂等，可重复跑）
$env:DATABASE_URL='postgresql+psycopg://evoai:<POSTGRES_PASSWORD>@<服务器IP>:5432/evoai'
python backend/scripts/migrate_sqlite_to_pg.py
```
> 需先在服务器临时放行 5432 给本机 IP，迁完立即收回（安全组删掉该规则）。

## 第 8 步 · 收尾

- [ ] GitHub Pages 保留为文档备份或停用（线上以云上为准，避免两套不一致）
- [ ] 本机 `start_services.ps1` 回归纯开发用途；Cloudflare Tunnel 方案不再推进
- [ ] 补《隐私政策》页面：说明微信登录采集 openid/昵称、数据存于境内（京东云华北）、用途与删除渠道

---

### 日常运维速查

```bash
docker compose ps                          # 四服务状态
docker compose logs -f backend             # 后端日志
docker compose up -d --build backend       # 改代码后只重建后端
docker compose restart backend             # 只改 .env 后重启
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot renew   # 证书续期
```

### 2C4G 资源预算（为什么够用）

| 服务 | 常驻内存 |
|---|---|
| nginx | ~20 MB |
| postgres:16 | ~200 MB |
| redis:7 | ~30 MB |
| backend（uvicorn ×2 worker） | ~700 MB |
| 系统 + swap 缓冲 | ~1 GB |
| **合计** | **< 2 GB / 4 GB，余量充足** |
