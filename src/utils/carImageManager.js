// ============================================================================
// CarImageManager — 彻底解决 6品牌19款 车型"照片丢失"问题
// ----------------------------------------------------------------------------
// 五层兜底策略（优先级从高到低）：
//   ① 本地真实 JPG 照片 (/brands/xxx.jpg) — 真车照片，随项目打包，首选
//   ② 远程 AI 生成图 (text_to_image)       — 本地照片失败时降级
//   ③ 运行时内联 SVG (dataURL)            — 不需要任何外部请求（兜底）
//   ④ 全局通用兜底图                       — 万无一失的最后防线
//
// 失败记忆机制 (localStorage)：
//   - URL 失败后标记为 "不可用"，24h 内跳过，不再反复请求
//   - 刷新页面、重开浏览器后仍生效，避免"每次都失败又重试"
// ============================================================================

export const CAR_IMAGE_POLICY = Object.freeze({
  FAILURE_TTL_MS: 24 * 60 * 60 * 1000, // 24 小时
  STORAGE_KEY_FAILED: 'evo_brands_image_failed_v1',
  STORAGE_KEY_CACHE: 'evo_brands_image_cache_v1'
})

// ────────────────────────────────────────────────────────────────────────────
// 失败记忆读写
// ────────────────────────────────────────────────────────────────────────────
const readFailedSet = () => {
  try {
    const raw = localStorage.getItem(CAR_IMAGE_POLICY.STORAGE_KEY_FAILED)
    const arr = raw ? JSON.parse(raw) : []
    const now = Date.now()
    return arr
      .filter(x => typeof x === 'object' && x && x.url && x.ts)
      .filter(x => (now - x.ts) < CAR_IMAGE_POLICY.FAILURE_TTL_MS)
  } catch {
    return []
  }
}

const writeFailedSet = (list) => {
  try {
    localStorage.setItem(CAR_IMAGE_POLICY.STORAGE_KEY_FAILED, JSON.stringify(list))
  } catch { /* ignore */ }
}

export const isUrlMarkedFailed = (url) => {
  if (!url) return false
  // /brands/* 静态照片随项目打包 -> 永远可用，不允许 dev 环境偶发 abort / 404 / 网络抖动
  // 把它们"误记为失败"。只对远程图 / data: 以外的 URL 做记忆。
  if (url.startsWith('/brands/')) return false
  return readFailedSet().some(x => x.url === url)
}

export const markUrlFailed = (url) => {
  if (!url) return
  // /brands/* 是打包产物，随项目发布，永远不进失败名单。
  if (url.startsWith('/brands/')) return
  if (url.startsWith('data:')) return
  const list = readFailedSet().filter(x => x.url !== url)
  list.push({ url, ts: Date.now() })
  // 限制上限 200 条
  const trimmed = list.slice(-200)
  writeFailedSet(trimmed)
}

export const clearFailedMarks = () => {
  try { localStorage.removeItem(CAR_IMAGE_POLICY.STORAGE_KEY_FAILED) } catch {}
}

// ────────────────────────────────────────────────────────────────────────────
// 本地真实照片路径（/brands/{brand}/{model}.jpg）— 首选图片源，随项目打包
// 这些 .jpg 是从 Bing 图片搜索下载的真实车型照片，无需网络请求，永远可用。
// ────────────────────────────────────────────────────────────────────────────
export const getStaticPhotoPath = (brandKey, modelKey) => {
  if (!brandKey || !modelKey) return null
  return `/brands/${encodeURIComponent(brandKey)}/${encodeURIComponent(modelKey)}.jpg`
}

// 兼容旧引用
export const getStaticSvgPath = getStaticPhotoPath

// ────────────────────────────────────────────────────────────────────────────
// 兜底运行时内联 SVG dataURL（第 4 层）
// ────────────────────────────────────────────────────────────────────────────
export const BRAND_COLORS = Object.freeze({
  'rolls-royce': '#4ade80',
  'bentley':     '#3b82f6',
  'bugatti':     '#f59e0b',
  'porsche':     '#ef4444',
  'ferrari':     '#dc2626',
  'lamborghini': '#f97316',
  'aston-martin': '#22c55e',
  'mclaren':     '#facc15'
})

export const buildRuntimeSvgDataUrl = (model, brandKey) => {
  try {
    const p = model?.params || {}
    const FO = p.front_overhang   ?? 1000
    const RO = p.rear_overhang    ?? 1000
    const WB = p.wheel_base       ?? 3000
    const overall_length  = FO + WB + RO   // 用 FO+WB+RO 精确，避免字段缺漏
    const overall_height  = p.overall_height ?? 1500
    const wheel_diameter  = p.wheel_diameter ?? 720
    const hood_length     = p.hood_length    ?? 1200
    const ground_clearance = p.ground_clearance ?? 150
    const windshield_angle = p.windshield_angle ?? 30
    const rear_window_angle = p.rear_window_angle ?? 25
    const rear_slant_angle  = p.rear_slant_angle  ?? 15

    const color = BRAND_COLORS[brandKey] || BRAND_COLORS['rolls-royce']

    // --- Car2D.vue 严格对齐的数学模型 (FIX: groundClearanceLine + 轮井弧线) ---
    const SVG_W = 320
    const SVG_H = 160
    const offsetX = 20
    const groundLineY = SVG_H - 12   // 轮胎最低点正好压在这条线
    const dimTextY  = SVG_H - 3

    const scale = (SVG_W - offsetX * 2) / overall_length
    const s = (v) => v * scale
    const frontX = 0
    const rearX  = s(overall_length)

    const groundClearanceLine_Y = groundLineY - s(ground_clearance)   // 车身底板
    const beltLineY = groundClearanceLine_Y - s(overall_height * 0.76) // 腰线（车窗下沿）
    const hoodLineY = groundClearanceLine_Y - s(overall_height * 0.62) // 引擎盖高度
    const trunkLineY = groundClearanceLine_Y - s(overall_height * 0.66)// 后备箱高度
    const roofTopY   = groundClearanceLine_Y - s(overall_height)       // 车顶最高线

    const hoodEndX = s(hood_length)
    const trunkLength = Math.min(s(RO * 0.6), s(hood_length * 0.5))
    const trunkStartX = rearX - trunkLength
    const waRad = windshield_angle * Math.PI / 180
    const rwRad = rear_window_angle * Math.PI / 180
    const rsRad = rear_slant_angle  * Math.PI / 180

    const windshieldHeight = beltLineY - roofTopY
    const windshieldTopX = hoodEndX + windshieldHeight / Math.tan(waRad)
    const maxRoofLength = trunkStartX - windshieldTopX
    const slantFactor = Math.min(Math.max(rear_slant_angle / 60, 0), 1)
    const roofLen = Math.max(maxRoofLength * (1 - slantFactor * 0.6), s(800))
    const rearWindowTopX = windshieldTopX + roofLen
    const rearWindowVertHeight = beltLineY - roofTopY
    const rearWindowHeightRatio = 0.5 + slantFactor * 0.35
    const rearWindowHeight = rearWindowVertHeight * rearWindowHeightRatio
    const rearWindowBottomX = rearWindowTopX + rearWindowHeight / Math.tan(rwRad)

    const wheelRadius = s(wheel_diameter / 2)
    const wheelCenterY = groundLineY - wheelRadius   // 轮胎底部正好 = groundLineY
    const frontWheelCx = offsetX + s(FO)
    const rearWheelCx  = offsetX + s(FO + WB)

    // ---- 前翼子板：从保险杠底平滑曲线到引擎盖高度（消除垂直悬崖） ----
    const bodyHeightPx = s(overall_height)
    const frontFenderEndX = frontX + offsetX + s(FO) * 0.85
    const frontFenderCtlX = frontX + offsetX + s(FO) * 0.35
    const frontFenderCtlY = groundClearanceLine_Y - bodyHeightPx * 0.40

    // ---- 后翼子板：从后备箱高度平滑曲线到保险杠底 ----
    const rearFenderStartX = rearX + offsetX - s(RO) * 0.85
    const rearFenderEndX = rearX + offsetX - s(RO) * 0.4
    const rearFenderEndY = groundClearanceLine_Y - bodyHeightPx * 0.08

    // ---- 车窗梯形顶点 ----
    const aBaseX = hoodEndX + offsetX
    const aBaseY = beltLineY
    const aTopX  = windshieldTopX + offsetX
    const aTopY  = roofTopY
    const cTopX  = rearWindowTopX + offsetX
    const cTopY  = roofTopY
    const cBaseX = rearWindowBottomX + offsetX
    const cBaseY = beltLineY

    // ---- 轮井弧线 ----
    const underY = groundClearanceLine_Y - 4
    const halfCutR = wheelRadius + 3
    const rearBumperX = rearX + offsetX
    const rearWellR_X = rearWheelCx + halfCutR
    const rearWellL_X = rearWheelCx - halfCutR
    const rearWellMidX = rearWheelCx
    const rearWellMidY = underY + wheelRadius * 1.1
    const frontWellR_X = frontWheelCx + halfCutR
    const frontWellL_X = frontWheelCx - halfCutR
    const frontWellMidX = frontWheelCx
    const frontWellMidY = underY + wheelRadius * 1.1
    const frontBumperX = frontX + offsetX

    // 闭合车身路径：平滑前翼子板 → 引擎盖 → A柱 → 车顶 → C柱 → 后备箱 → 平滑后翼子板 → 底板+轮井
    const bodyPath = [
      `M${frontBumperX.toFixed(2)},${groundClearanceLine_Y.toFixed(2)}`,
      `Q${frontFenderCtlX.toFixed(2)},${frontFenderCtlY.toFixed(2)} ${frontFenderEndX.toFixed(2)},${hoodLineY.toFixed(2)}`,
      `L${(hoodEndX + offsetX).toFixed(2)},${hoodLineY.toFixed(2)}`,
      `L${(hoodEndX + offsetX).toFixed(2)},${beltLineY.toFixed(2)}`,
      `L${(windshieldTopX + offsetX).toFixed(2)},${roofTopY.toFixed(2)}`,
      `L${(rearWindowTopX + offsetX).toFixed(2)},${roofTopY.toFixed(2)}`,
      `L${(rearWindowBottomX + offsetX).toFixed(2)},${beltLineY.toFixed(2)}`,
      `L${(rearWindowBottomX + offsetX).toFixed(2)},${trunkLineY.toFixed(2)}`,
      `Q${rearFenderStartX.toFixed(2)},${(trunkLineY + bodyHeightPx * 0.23).toFixed(2)} ${rearFenderEndX.toFixed(2)},${rearFenderEndY.toFixed(2)}`,
      `L${rearBumperX.toFixed(2)},${groundClearanceLine_Y.toFixed(2)}`,
      `L${rearWellR_X.toFixed(2)},${underY.toFixed(2)}`,
      `Q${rearWellMidX.toFixed(2)},${rearWellMidY.toFixed(2)} ${rearWellL_X.toFixed(2)},${underY.toFixed(2)}`,
      `L${frontWellR_X.toFixed(2)},${underY.toFixed(2)}`,
      `Q${frontWellMidX.toFixed(2)},${frontWellMidY.toFixed(2)} ${frontWellL_X.toFixed(2)},${underY.toFixed(2)}`,
      `L${frontBumperX.toFixed(2)},${underY.toFixed(2)}`,
      'Z'
    ].join(' ')

    // 车窗梯形
    const windowPath = `M${aBaseX.toFixed(2)},${aBaseY.toFixed(2)} L${aTopX.toFixed(2)},${aTopY.toFixed(2)} L${cTopX.toFixed(2)},${cTopY.toFixed(2)} L${cBaseX.toFixed(2)},${cBaseY.toFixed(2)} Z`

    // 阴影椭圆
    const shadowCx = offsetX + (frontX + rearX) / 2
    const shadowCy = groundLineY + 2
    const shadowRx = s(overall_length * 0.48)
    const shadowRy = 4

    const name = (model?.name || 'Car').replace(/[^A-Za-z0-9 -]/g, '').slice(0, 20)

    const svg = `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0f172a"/>
      <stop offset="1" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="bd" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0"   stop-color="${color}" stop-opacity="0.95"/>
      <stop offset="0.5" stop-color="${color}" stop-opacity="0.78"/>
      <stop offset="1"   stop-color="${color}" stop-opacity="0.52"/>
    </linearGradient>
    <linearGradient id="gl" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1e293b" stop-opacity="0.90"/>
      <stop offset="1" stop-color="#0f172a" stop-opacity="0.96"/>
    </linearGradient>
    <radialGradient id="sh" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="#000" stop-opacity="0.4"/>
      <stop offset="1" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="rm" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#e2e8f0"/>
      <stop offset="0.5" stop-color="#94a3b8"/>
      <stop offset="1" stop-color="#64748b"/>
    </linearGradient>
  </defs>
  <rect width="${SVG_W}" height="${SVG_H}" fill="url(#bg)"/>
  <ellipse cx="${shadowCx.toFixed(2)}" cy="${shadowCy}" rx="${Math.max(20,shadowRx).toFixed(2)}" ry="${shadowRy}" fill="url(#sh)"/>
  <line x1="10" y1="${groundLineY+1}" x2="${SVG_W-10}" y2="${groundLineY+1}" stroke="${color}" stroke-width="0.6" opacity="0.3"/>
  <path d="${bodyPath}" fill="url(#bd)" stroke="${color}" stroke-width="1.0" stroke-linejoin="round"/>
  <path d="${windowPath}" fill="url(#gl)" stroke="${color}" stroke-width="0.5" opacity="0.92"/>
  <g>
    <circle cx="${frontWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${wheelRadius.toFixed(2)}" fill="#020617" stroke="#000" stroke-width="1.2"/>
    <circle cx="${frontWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.55).toFixed(2)}" fill="url(#rm)" stroke="#334155" stroke-width="0.6"/>
    <circle cx="${frontWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.22).toFixed(2)}" fill="#1e293b"/>
    <circle cx="${frontWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.09).toFixed(2)}" fill="${color}"/>
    <circle cx="${rearWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${wheelRadius.toFixed(2)}" fill="#020617" stroke="#000" stroke-width="1.2"/>
    <circle cx="${rearWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.55).toFixed(2)}" fill="url(#rm)" stroke="#334155" stroke-width="0.6"/>
    <circle cx="${rearWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.22).toFixed(2)}" fill="#1e293b"/>
    <circle cx="${rearWheelCx.toFixed(2)}" cy="${wheelCenterY.toFixed(2)}" r="${(wheelRadius*0.09).toFixed(2)}" fill="${color}"/>
  </g>
  <text x="${SVG_W-6}" y="${dimTextY}" text-anchor="end" fill="${color}" font-size="7" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" opacity="0.82" font-weight="600">${name}  L${overall_length}mm</text>
</svg>`

    const b64 = typeof btoa === 'function'
      ? btoa(unescape(encodeURIComponent(svg)))
      : (typeof Buffer !== 'undefined' ? Buffer.from(svg, 'utf8').toString('base64') : '')
    if (!b64) return null
    return `data:image/svg+xml;base64,${b64}`
  } catch (e) {
    return null
  }
}

// 终极兜底（第 5 层）：极简通用汽车占位
export const UNIVERSAL_FALLBACK = `data:image/svg+xml;base64,${
  typeof btoa === 'function'
    ? btoa(unescape(encodeURIComponent(
        '<svg viewBox="0 0 320 160" xmlns="http://www.w3.org/2000/svg"><rect width="320" height="160" fill="#1e293b"/><path d="M40 120 L50 90 Q80 70 160 70 Q230 70 270 90 L280 120 Z" fill="#4ade80" fill-opacity="0.7" stroke="#4ade80" stroke-width="1.2"/><circle cx="95" cy="130" r="14" fill="#0f172a" stroke="#64748b" stroke-width="2"/><circle cx="225" cy="130" r="14" fill="#0f172a" stroke="#64748b" stroke-width="2"/></svg>'
      )))
    : ''
}`

// ────────────────────────────────────────────────────────────────────────────
// 统一入口：normalizeCarImageUrl(model, brandKey) → 4 层兜底
// 优先级：① 本地真实 JPG 照片 → ② 远程 AI 生成图 → ③ 运行时 SVG → ④ 通用兜底
// ────────────────────────────────────────────────────────────────────────────
const LAYER_NAMES = {
  1: '本地真实 JPG 照片',
  2: '远程 AI 生成图 (text_to_image)',
  3: '运行时内联 SVG',
  4: '终极通用兜底图',
}

export const normalizeCarImageUrl = (model, brandKey, opts = {}) => {
  const { preferRemote = false } = opts
  const key = model?.key || 'unknown'
  const bk  = brandKey || 'default'

  // ① 本地真实 JPG 照片 — 首选！真车照片，随项目打包，无需网络请求
  const staticPath = getStaticPhotoPath(bk, key)
  if (staticPath && !isUrlMarkedFailed(staticPath)) {
    console.log(`[CarImage] L1 ${LAYER_NAMES[1]} | ${bk}/${key} | ${staticPath}`)
    return { src: staticPath, layer: 1, key, brandKey: bk }
  }
  if (staticPath && isUrlMarkedFailed(staticPath)) {
    console.log(`[CarImage] L1 已标记失败，跳过 | ${bk}/${key} | ${staticPath}`)
  }

  // ② 远程 AI 生成图 (text_to_image API) — 本地照片失败时降级
  if (model?.image && !isUrlMarkedFailed(model.image)) {
    console.log(`[CarImage] L2 ${LAYER_NAMES[2]} | ${bk}/${key} | ${model.image.substring(0, 80)}`)
    return { src: model.image, layer: 2, key, brandKey: bk }
  }
  if (model?.image && isUrlMarkedFailed(model.image)) {
    console.log(`[CarImage] L2 已标记失败，跳过 | ${bk}/${key}`)
  }

  // ③ 运行时内联 SVG — 无网络请求的兜底
  const runtimeUrl = buildRuntimeSvgDataUrl(model, bk)
  if (runtimeUrl) {
    console.log(`[CarImage] L3 ${LAYER_NAMES[3]} | ${bk}/${key} | dataURL(${runtimeUrl.length} chars)`)
    return { src: runtimeUrl, layer: 3, key, brandKey: bk }
  }

  // ④ 终极兜底
  console.log(`[CarImage] L4 ${LAYER_NAMES[4]} | ${bk}/${key} | universal fallback`)
  return { src: UNIVERSAL_FALLBACK, layer: 4, key, brandKey: bk }
}

// ────────────────────────────────────────────────────────────────────────────
// 静态 JPG 清单：用 Vite import.meta.glob 在构建期一次性枚举真实文件
// → 0 网络请求 / 0 fetch HEAD / 0 ERR_ABORTED 控制台刷屏
// glob 返回 key 形如 "/public/brands/rolls-royce/phantom.jpg"，
// 映射到浏览器访问路径 "/brands/rolls-royce/phantom.jpg"。
// ────────────────────────────────────────────────────────────────────────────
let _staticPhotoSetPromise = null
const getStaticPhotoSet = async () => {
  // Vite/rollup 严格禁止对 import.meta 做可选链（`import?.meta`），
  // 这里直接访问 import.meta.env / import.meta.glob；SSR 构建由 Vite 提供对应 env。
  const isSSR = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.SSR
  if (typeof window === 'undefined' && isSSR) return new Set()
  if (typeof import.meta.glob !== 'function') return new Set()
  if (!_staticPhotoSetPromise) {
    _staticPhotoSetPromise = (async () => {
      try {
        const files = import.meta.glob('/public/brands/**/*.jpg', { eager: false })
        const keys = Object.keys(files || {})
        const set = new Set()
        for (const k of keys) {
          const browserPath = k.replace(/^\/public/, '')
          set.add(browserPath)
          // 同时接受不带 encodeURIComponent 的形式作为 key，与 getStaticPhotoPath 输出对齐
          set.add(decodeURIComponent(browserPath))
        }
        return set
      } catch {
        return new Set()
      }
    })()
  }
  return _staticPhotoSetPromise
}

// ────────────────────────────────────────────────────────────────────────────
// 批量验证：静态 JPG 照片是否存在（纯内存查表，无任何网络请求）
// 旧版 fetch HEAD 会在 Vite 冷启动并发下触发大量 net::ERR_ABORTED 控制台刷屏，
// 现改为基于构建期 glob 清单匹配，保证 0 错误日志。
// ────────────────────────────────────────────────────────────────────────────
export const verifyAllStaticPhotos = async (brands) => {
  const set = await getStaticPhotoSet()
  const total = []
  let ok = 0
  for (const b of brands || []) {
    for (const m of b.models || []) {
      const p = getStaticPhotoPath(b.key, m.key)
      const exists = set.size === 0
        ? null   // 非 Vite 环境：不判断，留给浏览器 img.onerror 兜底
        : (set.has(p) || set.has(decodeURIComponent(p)))
      const stat = exists === null ? 'skip (no-glob env)' : (exists ? 'ok' : 'not-found-in-glob')
      if (exists === true) ok++
      else if (exists === null) ok++ // 非 Vite：默认跳过不计数缺失
      total.push({ brand: b.key, model: m.key, path: p, status: stat })
    }
  }
  return { total, ok, expected: total.length }
}
