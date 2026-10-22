"""安全围栏（Security Fence）子系统

指导思想（薛澜《推动全球人工智能治理制度构建》，光明日报）：
  - 「安全是发展的前提」——围栏是平台能力的第一道前提约束；
  - 「确保人工智能始终处于人类控制之下」——全部围栏能力由配置驱动，
    管理员可随时通过应急开关停用任一能力（killswitch / 维护模式）；
  - 防「恶用、滥用及失控」——输入侧守卫（请求体/消息/上传上限、注入特征检测）；
  - 「技术监测、风险预警、应急响应体系」——结构化审计事件流 + 观测接口 +
    应急开关，四层并举；
  - 「原则与工具并举、可运行、可验证、可扩展」——全部能力配置化、
    带契约测试（tests/test_security_fence.py）、按层可独立扩展。

模块划分：
  audit.py       技术监测：结构化安全审计事件流（JSONL 滚动文件）
  middleware.py  边界守卫：请求追踪（X-Request-Id）/ 请求体上限 / 维护模式
  guards.py      防恶用：LLM payload 守卫 + 注入特征检测 + 上传分块限读
  killswitch.py  应急响应：能力级应急开关（FastAPI 依赖工厂）

设计约束：
  - 围栏永不阻断业务主流程：审计写入失败仅记 warning，不抛出；
  - FENCE_ENABLED=false 时中间件与守卫全部旁路（应急降级通道），
    审计流由 FENCE_AUDIT_ENABLED 独立控制（保留取证能力）；
  - 所有阈值/开关从 settings 动态读取（便于测试与运行时调整）。
"""
from .audit import emit, configure_audit, request_id_var
from .guards import guard_llm_payload, scan_injection, read_upload_limited
from .killswitch import killswitch_dependency

__all__ = [
    "emit", "configure_audit", "request_id_var",
    "guard_llm_payload", "scan_injection", "read_upload_limited",
    "killswitch_dependency",
]
