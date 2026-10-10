"""应用配置：基于pydantic-settings，从.env读取"""
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 开发默认密钥：仅允许非生产环境使用（生产 fail-fast 校验依赖此常量识别默认值）
_DEFAULT_SECRET_KEY = "evolution-ai-dev-secret-change-me-in-production-2026"
# 生产环境 SECRET_KEY 最小长度
_MIN_PROD_SECRET_LEN = 32


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./evolution_ai.db"

    # ============ 用户账户 / JWT 鉴权 ============
    # 开发默认密钥；生产必须通过 .env 覆盖（>=32 位随机字符串），
    # 未覆盖时下方 _require_strong_secret_in_production 校验会拒绝启动（fail-fast）
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天
    # 注册时是否要求邮箱唯一（默认开启）
    REQUIRE_EMAIL_VERIFICATION: bool = False

    # ============ 游客模式（账号体系封存期） ============
    # true：所有受保护接口免登录，统一落到内置 guest 账户（角色 superadmin，
    # 保证「游客可测试全部功能」）。账号模块封存阶段的临时开关，
    # 生产环境禁止开启（下方校验 fail-fast）。
    GUEST_MODE: bool = False

    # ============ 微信扫码登录（开放平台） ============
    # 在 https://open.weixin.qq.com/ 创建「网站应用」后获得
    WECHAT_APPID: str = ""          # 例如 wx1234567890abcdef
    WECHAT_SECRET: str = ""         # 对应 AppSecret
    WECHAT_REDIRECT_URI: str = ""   # 默认 http://127.0.0.1:8000/api/v1/auth/wechat/callback
    # 前端页面地址（微信回调页 postMessage 的目标 origin）
    FRONTEND_URL: str = "http://127.0.0.1:5173"

    # ============ 微信公众号网页授权（个人测试号即可） ============
    # 测试号申请：https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login
    # 需要在公众号后台「网页授权获取用户基本信息」中配置授权回调域名
    MP_APPID: str = ""              # 公众号 AppID
    MP_SECRET: str = ""             # 公众号 AppSecret
    MP_REDIRECT_URI: str = ""       # 默认 http://127.0.0.1:8000/api/v1/auth/mp/callback

    DATA_DIR: str = "../data"
    MODELS_DIR: str = "../data/models"
    REPORTS_DIR: str = "../data/reports"
    EXPORTS_DIR: str = "../data/exports"

    # ============ AI 训练后端（真实 PyTorch 训练） ============
    # pytorch  = 使用本机 PyTorch（CPU）执行真实训练
    # disabled = 显式关闭训练能力，/ai/train 将返回 503（不做假训练）
    TRAINING_BACKEND: str = "pytorch"
    TRAINING_MAX_EPOCHS: int = 100
    TRAINING_MAX_SAMPLES: int = 10000
    TRAINING_MAX_CONCURRENT: int = 2
    TRAINING_CHECKPOINT_DIR: str = "../data/training"

    MAX_FILE_SIZE: int = 52428800
    ALLOWED_EXTENSIONS: str = ".glb,.gltf,.obj,.stl,.fbx,.igs,.iges,.step,.stp"

    TOPOLOGY_TARGET_FACES: int = 30000
    TOPOLOGY_MIN_QUAD_RATIO: float = 0.75
    QUALITY_TOLERANCE_POSITION: float = 0.1
    QUALITY_TOLERANCE_TANGENT: float = 0.01
    QUALITY_TOLERANCE_CURVATURE: float = 0.001

    DEFAULT_LANGUAGE: str = "zh"
    SUPPORTED_LANGUAGES: str = "zh,en"

    # ============ Redis 会话持久化 ============
    # 启用 Redis：true 时优先用 Redis，false 时走进程内存（重启丢失）
    SESSION_USE_REDIS: bool = False
    # Redis 连接串：redis://[[username]:[password]]@host:port[/db]
    # 示例：redis://localhost:6379/0  或  redis://:pass@host:6379/1
    SESSION_REDIS_URL: str = "redis://localhost:6379/0"
    # 会话 TTL（秒），默认 24h；0 表示不自动过期（建议仍设一个上限）
    SESSION_TTL_SECONDS: int = 86400
    # Redis key 前缀，区分不同部署/业务
    SESSION_REDIS_PREFIX: str = "evoai:session:"
    # 连接池大小 / 超时
    SESSION_REDIS_POOL_SIZE: int = 16
    SESSION_REDIS_TIMEOUT: float = 2.0

    # ============ CORS & 安全响应头 ============
    # CORS 允许的 Origin（逗号分隔；默认包含本地开发常见端口）
    CORS_ALLOW_ORIGINS: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174,"
        "http://127.0.0.1:8000,http://localhost:8000"
    )
    # 是否在非预检的 CORS 响应里回显 Vary: Origin（建议开启，避免 CDN/反代缓存 ACAO）
    CORS_VARY_ORIGIN: bool = True
    # 是否去掉 "server: uvicorn" 信息泄露头（审计中标记为中危）
    HIDE_SERVER_HEADER: bool = True
    # 安全响应头（覆盖所有接口，包括 2xx/4xx/5xx/FileResponse）
    SEC_HEADER_XCTO: str = "nosniff"                 # X-Content-Type-Options
    SEC_HEADER_XFO: str = "DENY"                      # X-Frame-Options  (SAMEORIGIN 若要内嵌 iframe)
    SEC_HEADER_CSP: str = (                           # Content-Security-Policy
        "default-src 'self'; "
        "img-src 'self' data: https: blob:; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; "
        "connect-src 'self' https: ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    SEC_HEADER_RP: str = "strict-origin-when-cross-origin"   # Referrer-Policy
    SEC_HEADER_PERM: str = (                                 # Permissions-Policy
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), fullscreen=(self), usb=(), bluetooth=()"
    )
    # Strict-Transport-Security（仅 HTTPS 部署生效；设 max-age 0 表示不强制）
    SEC_HEADER_HSTS_MAX_AGE: int = 0
    # Cache-Control：动态 API 默认 no-store（禁用任何缓存，避免会话数据陈旧）；
    #   静态 /i18n/config 等可后续按路由微调
    SEC_HEADER_CC_API: str = "no-store, no-cache, must-revalidate, max-age=0"

    # ============ API 限流（slowapi，按客户端 IP） ============
    # 总开关：pytest / 本地调试可置 false 整体禁用（环境变量优先级高于 .env）
    RATE_LIMIT_ENABLED: bool = True
    # 登录/注册：防口令爆破与批量注册
    RATE_LIMIT_AUTH: str = "10/minute"
    # LLM 代理转发（chat/embeddings/images）：防滥用刷量
    RATE_LIMIT_AI: str = "10/minute"

    @property
    def allowed_extensions_list(self):
        return [e.strip() for e in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def supported_languages_list(self):
        return [l.strip() for l in self.SUPPORTED_LANGUAGES.split(",")]

    @property
    def cors_allow_origins_list(self):
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self):
        """生产环境强制 SECRET_KEY 合规：禁止内置开发默认值、长度至少 32 位。

        违规时 pydantic 抛 ValidationError，应用启动阶段即失败（fail-fast），
        避免带着可预测的弱密钥静默上线签发 JWT / 加密 API Key。
        """
        if self.ENVIRONMENT.strip().lower() == "production":
            if self.SECRET_KEY == _DEFAULT_SECRET_KEY:
                raise ValueError(
                    "生产环境必须通过环境变量或 .env 覆盖 SECRET_KEY，"
                    "不能使用内置开发默认值；请设置一个至少 "
                    f"{_MIN_PROD_SECRET_LEN} 位的随机字符串，例如："
                    "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            if len(self.SECRET_KEY) < _MIN_PROD_SECRET_LEN:
                raise ValueError(
                    f"生产环境 SECRET_KEY 长度至少 {_MIN_PROD_SECRET_LEN} 位，"
                    f"当前仅 {len(self.SECRET_KEY)} 位"
                )
            # DEBUG=true 时 CORS 回退为任意 Origin、500 响应暴露异常细节，生产必须关闭
            if self.DEBUG:
                raise ValueError(
                    "生产环境必须设置 DEBUG=false：DEBUG 开启时 CORS 放行任意 Origin，"
                    "且 500 响应会暴露异常堆栈"
                )
            # 游客模式把所有受保护接口对匿名访客完全开放（含超管接口），
            # 仅限本地封存测试期使用，生产开启等同于无鉴权裸奔，禁止。
            if self.GUEST_MODE:
                raise ValueError(
                    "生产环境禁止开启 GUEST_MODE=true：该模式将包含超级管理员"
                    "接口在内的全部受保护接口对匿名访客开放，仅限本地封存测试使用"
                )
        return self

    @property
    def data_path(self): return Path(self.DATA_DIR).resolve()

    @property
    def models_path(self): return Path(self.MODELS_DIR).resolve()

    @property
    def reports_path(self): return Path(self.REPORTS_DIR).resolve()

    @property
    def exports_path(self): return Path(self.EXPORTS_DIR).resolve()

    @property
    def training_checkpoint_path(self):
        return Path(self.TRAINING_CHECKPOINT_DIR).resolve()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
