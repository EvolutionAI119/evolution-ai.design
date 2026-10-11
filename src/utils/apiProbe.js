// ============================================================================
// API 探测 / 演示模式判定
//
// 背景：公网 GitHub Pages 为纯静态站（无后端反代），/api/v1/* 返回 404。
// 与其让用户在每个动态功能点反复撞"服务暂时不可用"，不如启动时探测一次，
// 全局置为「演示模式」：顶部横幅一次性说明 + 拦截器把 404 文案改为
// 演示版专属提示。
//
// 兼容性：
//   - 本地开发（同源代理可达）→ 探测 200 → 演示模式关闭，零打扰
//   - 未来接通隧道/后端（VITE_API_BASE_URL 注入）→ 探测 200 → 自动关闭
//   - 公网静态站 → 探测 404 → 演示模式开启
//
// 缓存策略：sessionStorage 会话级缓存 10 分钟，避免每次刷新重复探测；
// 探测用原生 fetch（不经 axios 实例，规避拦截器/鉴权循环依赖）。
// ============================================================================
import { ref } from 'vue'

export const demoMode = ref(false)       // true = 静态演示环境（API 不可达）
export const demoDismissed = ref(false)  // 用户已关闭横幅（仅影响 UI）

const CACHE_KEY = 'evo_api_probe_v1'
const PROBE_TTL_MS = 10 * 60 * 1000      // 10 分钟内复用探测结论

function readCache() {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed.demo === 'boolean' &&
        Date.now() - parsed.ts < PROBE_TTL_MS) {
      return parsed.demo
    }
  } catch { /* 缓存损坏 → 重探 */ }
  return null
}

function writeCache(demo) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), demo }))
  } catch { /* 隐私模式等场景忽略 */ }
}

/**
 * 探测后端可达性并更新全局 demoMode。
 * @returns {Promise<boolean>} true = API 可用
 */
export async function probeApi(timeoutMs = 4000) {
  const cached = readCache()
  if (cached !== null) {
    demoMode.value = cached
    return !cached
  }

  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let available = false
  try {
    const resp = await fetch(base + '/auth/methods', {
      signal: controller.signal,
    })
    available = resp.ok
  } catch {
    available = false
  } finally {
    clearTimeout(timer)
  }

  demoMode.value = !available
  writeCache(!available)
  return available
}
