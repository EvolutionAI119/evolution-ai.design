// 可验证的影响证据 · 前端埋点 SDK
//
// 职责：
//  - 维护跨会话 visitor_id（localStorage，用于 UV 去重）
//  - 维护会话级 session_id（sessionStorage）
//  - SPA 路由切换时上报页面进入（POST /track，拿到 view_id）
//  - 路由离开 / 页面隐藏 / 关闭时回填停留时长
//  - 页面卸载使用 navigator.sendBeacon，保证离页信号可靠送达
//  - 所有上报静默失败，绝不影响业务交互
import api from '../api'

const VISITOR_KEY = 'evoai_visitor_id'
const SESSION_KEY = 'evoai_session_id'

function uuidCompact(prefix) {
  const raw = (crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`).replace(/-/g, '')
  return `${prefix}${raw}`.slice(0, 32)
}

function getVisitorId() {
  let id = localStorage.getItem(VISITOR_KEY)
  if (!id) {
    id = uuidCompact('v_')
    localStorage.setItem(VISITOR_KEY, id)
  }
  return id
}

function getSessionId() {
  let id = sessionStorage.getItem(SESSION_KEY)
  if (!id) {
    id = uuidCompact('s_')
    sessionStorage.setItem(SESSION_KEY, id)
  }
  return id
}

class AnalyticsTracker {
  constructor() {
    this.visitorId = getVisitorId()
    this.sessionId = getSessionId()
    this.currentViewId = null
    this.enterAt = 0
    this.firstView = true
    this._onHide = this._onHide.bind(this)
  }

  start(router) {
    this.router = router
    router.afterEach((to) => this._enter(to.path))
    window.addEventListener('pagehide', this._onHide)
    document.addEventListener('visibilitychange', this._onHide)
  }

  stop() {
    window.removeEventListener('pagehide', this._onHide)
    document.removeEventListener('visibilitychange', this._onHide)
  }

  // 页面进入：先结算上一页，再落地新访问记录
  async _enter(path) {
    this._flushCurrent(false)
    // 导航令牌：响应返回时若已切到别的页，丢弃本次结果防止错配
    const token = Symbol('nav')
    this._navToken = token
    const enterAt = Date.now()
    // 外部 referrer 只在会话首次访问时归因，避免每页都记成外部来源
    const referrer = this.firstView ? document.referrer || null : null
    this.firstView = false
    try {
      const { data } = await api.post('/analytics/track', {
        visitor_id: this.visitorId,
        session_id: this.sessionId,
        path,
        referrer
      })
      if (this._navToken !== token) return
      this.currentViewId = data.id
      this.enterAt = enterAt
    } catch {
      if (this._navToken === token) this.currentViewId = null
    }
  }

  // 结算当前页停留时长
  _flushCurrent(useBeacon) {
    if (!this.currentViewId || !this.enterAt) return
    const duration = Math.min(
      Math.round((Date.now() - this.enterAt) / 1000), 24 * 3600)
    const viewId = this.currentViewId
    if (useBeacon && navigator.sendBeacon) {
      const blob = new Blob(
        [JSON.stringify({ view_id: viewId, duration_seconds: duration })],
        { type: 'application/json' })
      navigator.sendBeacon('/api/v1/analytics/track/duration', blob)
    } else {
      api.post('/analytics/track/duration', {
        view_id: viewId, duration_seconds: duration
      }).catch(() => {})
    }
    this.currentViewId = null
    this.enterAt = 0
  }

  _onHide(e) {
    if (e.type === 'pagehide' || document.visibilityState === 'hidden') {
      this._flushCurrent(true)
    }
  }
}

export const tracker = new AnalyticsTracker()
export default tracker
