# =========================================================================
#  Evolution-Ai.Design — Backend (FastAPI) Dockerfile
#  多阶段构建：
#    stage 1 (builder): 安装编译工具 → pip install 依赖 → 编译 algorithm_model Cython 扩展
#    stage 2 (runtime): python slim + 仅复制 site-packages + 项目源码 + 非 root
#  环境变量覆盖：见 config.py / pydantic-settings BaseSettings（以 env 为准）
# =========================================================================

# ----------------------------- builder -----------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# 1) 安装编译时依赖（gcc/g++，用于 Cython + numpy/scipy 可能的原生编译）
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
 && rm -rf /var/lib/apt/lists/*

# 2) 先 COPY 3 份 requirements，充分利用 Docker build 缓存（依赖不频繁改）
COPY requirements.txt                 ./requirements-root.txt
COPY backend/requirements.txt         ./requirements-backend.txt
COPY algorithm_model/requirements.txt ./requirements-algorithm.txt

# 可选：若需要内网 / 国内镜像加速，构建时传 --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
RUN PIP_EXTRA="" ; \
    if [ -n "$PIP_INDEX_URL" ]; then PIP_EXTRA="--index-url $PIP_INDEX_URL --trusted-host ${PIP_TRUSTED_HOST:-mirrors.aliyun.com}"; fi ; \
    pip install --no-cache-dir $PIP_EXTRA \
        -r requirements-root.txt \
 && pip install --no-cache-dir $PIP_EXTRA \
        -r requirements-backend.txt \
 && pip install --no-cache-dir $PIP_EXTRA \
        -r requirements-algorithm.txt \
 && pip install --no-cache-dir $PIP_EXTRA cython setuptools wheel

# 3) 复制源码（此时 Cython 在 image 里已就绪，可以直接编译）
COPY . .

# 4) 编译 Cython 扩展（.so / .pyd），失败时打印提示，不阻塞构建（纯 Python 仍能跑）
RUN python setup_nurbs.py build_ext --inplace 2>&1 \
      || { echo "⚠️ Cython 编译失败（降级纯 Python 模式）" ; } ; \
    find algorithm_model -maxdepth 3 \( -name "*.so" -o -name "*.c" \) -type f -print 2>/dev/null | head -40

# ----------------------------- runtime -----------------------------
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="evolution-ai-design-backend" \
      org.opencontainers.image.description="EVOLUTION AI - 参数化+AI驱动的汽车造型开发平台（FastAPI 后端）"

WORKDIR /app

# 运行时：只需要 curl（healthcheck）+ 一些证书/时区
ENV TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone

# 1) 从 builder 复制整个 site-packages 和 uvicorn/fastapi 可执行脚本
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin                /usr/local/bin

# 2) 复制项目源码 + 编译出来的 Cython .so（builder 里已生成）
COPY --from=builder /build /app

# 3) 后端运行时的工作目录必须是 /app/backend（start.py 里 from app.config import settings）
WORKDIR /app/backend

# 4) 运行时数据目录（Volume 挂载点，持久化 uploads/exports/sessions 等）
#    config.py 默认 DATA_DIR="../data" → 解析后就是 /app/data（与 WORKDIR 相对）
RUN mkdir -p /app/data/uploads /app/data/exports /app/data/models /app/data/reports /app/logs

# 5) 非 root：创建 appuser，给目录授权（生产最佳实践）
RUN groupadd --system --gid 10001 evoai \
 && useradd  --system --uid 10000 --gid evoai --no-create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:evoai /app

USER appuser

# 6) 声明 Volume（容器重建时不丢）
VOLUME ["/app/data", "/app/logs"]

# 7) uvicorn 监听端口（config.py 默认 0.0.0.0:8000）
EXPOSE 8000

# 8) Healthcheck：走 /api/v1/health（与前面审计一致的端点）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null || exit 1

# 9) 启动：start.py（app.config.settings 驱动所有参数）
#    注意：若想用多 worker 可显式传 uvicorn，但 start.py 已对 server_header/安全头做了设置。
CMD ["python", "start.py"]
