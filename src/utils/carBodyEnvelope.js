// 车身包络校验（内饰件「不得穿出车身外表面」的唯一判据）
//
// 为什么需要这一层：
//   内饰布置是按语义矩形（AABB）派生的，而车身外表面是溜背/尾门斜面 + 轮拱腔体。
//   矩形块若直接把 topY 取到 roofTopY、或把 x 铺到车头/车尾全段，就会从斜面上穿出去
//   （外观视角能看到黑色内饰楔形块）。仅比较 roofTopY 的旧断言在高度方向是盲区：
//   车顶最高点合规不代表尾段（车顶已下落 0.6m）也合规。
//
// 判据（全部为米，P 坐标系 X+ 车头 / Y+ 向上 / Z+ 副驾侧）：
//   1) 纵向：[rearX, frontX] 之内
//   2) 上界：y ≤ bodyTopAt(x)（沿侧视轮廓逐 x 取顶边，天然覆盖溜背与尾门斜面）
//   3) 下界：y ≥ bodyBottomY（车身底板；轮拱缺口不影响中线地板）
//   4) 横向：|z| ≤ shellHalfZAt(y)（车顶收窄后的真实侧壁）
//   5) 轮拱腔体：|z| ≥ archInnerZ 且落在轮拱椭圆内 → 进入轮腔（会从轮口看到）
//
// 与 carErgoVerification 的分工：那边判人机指标（间距/遮罩/头部余量），这边只判「越出车身」。

import { bodySideOutline } from './carProfile.js'
import { deriveCabinGlass, buildDloFrame, shellHalfZAt, BODY_BEVEL_SIZE, ROOF_FILLETS } from './carGlass.js'

/** 侧视轮廓采样为多边形（弧段细分 32，Q 曲线细分 16） */
export function bodyOutlinePolygon(P, carType = P?.carType) {
  // 第三个参数是「圆角半径默认值表」，不是已解析的圆角几何——
  // 传已解析结果会让 bodySideOutline 内部的 roofFilletSet 取不到半径，产出空命令。
  const cmds = bodySideOutline(P, carType, ROOF_FILLETS, P?.ramps ?? null)
  const pts = []
  let cur = null
  for (const c of cmds) {
    if (c.k === 'M' || c.k === 'L') {
      pts.push([c.x, c.y]); cur = [c.x, c.y]
    } else if (c.k === 'Q') {
      for (let i = 1; i <= 16; i++) {
        const t = i / 16, u = 1 - t
        pts.push([
          u * u * cur[0] + 2 * u * t * c.cx + t * t * c.x,
          u * u * cur[1] + 2 * u * t * c.cy + t * t * c.y
        ])
      }
      cur = [c.x, c.y]
    } else if (c.k === 'A') {
      const n = 32
      for (let i = 1; i <= n; i++) {
        const t = i / n
        const a = c.cw ? c.a0 - (c.a0 - c.a1) * t : c.a0 + (c.a1 - c.a0) * t
        pts.push([c.cx + c.rx * Math.cos(a), c.cy + c.ry * Math.sin(a)])
      }
      cur = pts[pts.length - 1]
    }
  }
  return pts
}

/** 侧视轮廓在 x 处的上边界（不存在实体时返回 -Infinity） */
export function bodyTopAt(poly, x) {
  let top = -Infinity
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [x1, y1] = poly[j], [x2, y2] = poly[i]
    if ((x - x1) * (x - x2) > 0) continue
    if (Math.abs(x2 - x1) < 1e-12) { top = Math.max(top, y1, y2); continue }
    const t = (x - x1) / (x2 - x1)
    if (t < -1e-9 || t > 1 + 1e-9) continue
    top = Math.max(top, y1 + (y2 - y1) * t)
  }
  return top
}

/** 侧视轮廓在 x 处的下边界（含轮拱缺口，用于兜底判定） */
export function bodyBottomAt(poly, x) {
  let bot = Infinity
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [x1, y1] = poly[j], [x2, y2] = poly[i]
    if ((x - x1) * (x - x2) > 0) continue
    if (Math.abs(x2 - x1) < 1e-12) { bot = Math.min(bot, y1, y2); continue }
    const t = (x - x1) / (x2 - x1)
    if (t < -1e-9 || t > 1 + 1e-9) continue
    bot = Math.min(bot, y1 + (y2 - y1) * t)
  }
  return bot
}

/** 轮拱腔体（两侧对称）：椭圆缺口 + 侧壁内缘 |z| ≥ archInnerZ + 轮胎横向遮挡区间 */
export function archCavities(P) {
  const halfTrack = P?.halfTrack ?? 0.80
  const tireW = P?.tireWidth ?? 0.25
  const archInnerZ = Math.max(0.20, halfTrack - tireW / 2 - 0.02)
  const tireInnerZ = Math.max(0, halfTrack - tireW / 2)
  const out = []
  for (const side of ['front', 'rear']) {
    const ax = side === 'front' ? P?.frontWheelX : P?.rearWheelX
    const a = P?.wheelArch?.[side]
    if (ax == null || !a) continue
    out.push({
      side, cx: ax, cy: P.archY ?? 0, rx: a.rx, ry: a.ry,
      archInnerZ, tireInnerZ, tireOuterZ: halfTrack + tireW / 2
    })
  }
  return out
}

/**
 * 轮拱椭圆在高度 y 处的后缘 X（腔体自该 X 向前延伸）。
 * y 超出拱顶/拱底时该高度无腔体 → 返回 -Infinity（表示「不需要因该拱收短」）。
 * 用于把 IP 下体等矩形件的前缘收短到腔体边界。
 */
export function archRearEdgeX(arch, y) {
  const v = (y - arch.cy) / arch.ry
  if (Math.abs(v) >= 1) return -Infinity
  return arch.cx - arch.rx * Math.sqrt(1 - v * v)
}

/**
 * 轮胎在该 X 处的顶面高度（圆柱轮胎：轮心 (wheelX, archY)、半径 wheelR）。
 * 轮胎是轮腔里唯一的实体遮挡物：低于该高度且 |z| 落在轮胎横向区间的点，
 * 从车外被轮胎挡住，属于「几何上在腔体内但外观不可见」。
 * X 超出轮胎覆盖段 → 返回 -Infinity（无遮挡）。
 */
export function tireTopAt(P, x, side) {
  const wx = side === 'front' ? P?.frontWheelX : P?.rearWheelX
  const r = P?.wheelR ?? P?.archY
  const cy = P?.archY
  if (wx == null || r == null || cy == null) return -Infinity
  const dx = x - wx
  if (Math.abs(dx) >= r) return -Infinity
  return cy + Math.sqrt(r * r - dx * dx)
}

/**
 * 车身包络求值器（一次构建，多次判定；六车型各建一份）
 * @param {object} P deriveCarProfile 输出
 */
export function bodyEnvelope(P) {
  const carType = P?.carType
  const poly = bodyOutlinePolygon(P, carType)
  const glass = deriveCabinGlass(P)
  const bodyExtentZ = (P?.W ?? 1.88) / 2
  const frame = buildDloFrame(glass, bodyExtentZ + 0.002)
  const halfZAt = (y) => shellHalfZAt(y, frame, bodyExtentZ)
  const arches = archCavities(P)
  const bodyBottomY = P?.bodyBottomY ?? 0.20
  const rearX = P?.rearX ?? 0
  const frontX = P?.frontX ?? 0
  return { P, poly, bodyExtentZ, halfZAt, arches, bodyBottomY, rearX, frontX }
}

/**
 * 单点判定。返回穿出类型（null = 合规）。
 * tol 默认取挤出倒角尺寸（BODY_BEVEL_SIZE）——bevel 使车身外表面比轮廓外扩该值。
 * 轮拱命中额外给出 visible：|z| 在轮胎横向区间内且低于该 X 处轮胎顶面 → 被轮胎遮挡，
 * 外观不可见（几何上仍应尽量归位，但不算「穿模露黑」）。
 */
export function pointOutside(env, x, y, z, tol = BODY_BEVEL_SIZE + 0.002) {
  const { poly, halfZAt, arches, bodyBottomY, rearX, frontX, P } = env
  const ax = Math.abs(z)
  if (x > frontX + tol || x < rearX - tol) return { kind: 'x' }
  const top = bodyTopAt(poly, x)
  if (y > top + tol) return { kind: 'top', over: y - top }
  if (y < bodyBottomY - tol) return { kind: 'bottom', over: bodyBottomY - y }
  const hz = halfZAt(y)
  if (ax > hz + tol) return { kind: 'z', over: ax - hz }
  for (const a of arches) {
    if (ax < a.archInnerZ - tol) continue          // 中线区不受轮拱缺口影响
    const u = (x - a.cx) / a.rx, v = (y - a.cy) / a.ry
    if (u * u + v * v <= 1 - 1e-6) {
      const tTop = tireTopAt(P, x, a.side)
      const inTireZ = ax >= a.tireInnerZ - 0.005 && ax <= a.tireOuterZ + 0.005
      const visible = !(inTireZ && tTop > -Infinity && y < tTop - 0.01)
      return { kind: 'arch', side: a.side, visible, over: tTop > -Infinity ? y - tTop : 0 }
    }
  }
  return null
}

/** 矩形件（8 角点）判定：任一角点穿出即算；可见命中优先作为 worst */
export function boxOutside(env, box, tol) {
  const res = []
  for (const x of [box.x0, box.x1]) {
    for (const y of [box.y0, box.y1]) {
      for (const z of [box.z0, box.z1]) {
        const v = pointOutside(env, x, y, z, tol)
        if (v) res.push({ x, y, z, ...v })
      }
    }
  }
  if (!res.length) return null
  const visible = res.filter((r) => r.kind === 'arch' && r.visible)
  const pick = (arr) => arr.reduce((a, b) => ((b.over ?? 0) > (a.over ?? 0) ? b : a), arr[0])
  const worst = visible.length ? pick(visible) : pick(res)
  return { worst, count: res.length, visibleCount: visible.length }
}

/** 沿 x 分段取顶边最小值：把斜面下落的舱体按段收口（衬板/内板建模用） */
export function topEnvelopeOver(poly, x0, x1, stations = 6) {
  let top = Infinity
  for (let i = 0; i <= stations; i++) {
    const x = x0 + (x1 - x0) * i / stations
    top = Math.min(top, bodyTopAt(poly, x))
  }
  return top
}
