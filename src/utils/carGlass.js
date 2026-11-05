// 座舱玻璃划分纯函数（无 Three.js 依赖，可单测）
//
// 职责：由 deriveCarProfile 的结果派生 3D 座舱「玻璃 / 车身」两种状态的几何参数，
//       供 Car3D.vue 兜底路径（ExtrudeGeometry）构建玻璃网格与 B 柱使用。
//
// 拓扑约定（3D 玻璃按车身轮廓 G1 圆角修裁，2D Car2D windowPath 为理论框示意）：
//   前风挡带  hoodEndX/beltLineY → windshieldTopX/roofTopY（A 柱线），
//             底缘 bottomInset 沿带下退避开 COWL 直角 bevel 外扩角
//   后风挡带  rearWindowBottomX/beltLineY → rearWindowTopX/roofTopY（C 柱线，皮卡无）
//   侧窗 DLO  四角精确落于轮廓内：底前角在 A 柱斜线上、顶后角在车顶后缘圆角
//             （filletXAtY 解二次贝塞尔）、底后角沿 C 柱斜线上退避开圆角切线区
//   B 柱      windshieldTopX → dloTopRear 的 55% 分段（与 2D pillarX 同源），
//             顶端搭入 DLO 顶边之下（不悬浮于玻璃面外）
//
// 坐标约定同 carProfile.js：X+ 指向车头，Y+ 竖直向上，地面 Y=0，单位米。
import { filletCorner } from './carProfile.js'

/**
 * 车顶三角 G1 圆角半径单一真源（米）。Car3D.vue bodyShape 与 deriveCabinGlass
 * 共用同一组半径，保证 DLO/风挡带修裁量与轮廓圆角始终一致。
 * 常规车：A 柱顶 0.09 / 车顶后缘 0.09 / C 柱底 0.06；
 * 皮卡：驾驶室顶 0.09 / 后壁顶 0.05 / 后壁底 0.03。
 */
export const ROOF_FILLETS = {
  aPillarTop: 0.09,
  roofRear: 0.09,
  cPillarBottom: 0.06,
  pickupCabTop: 0.05,
  pickupCabBottom: 0.03
}

/**
 * 车身挤出倒角尺寸（米）：Car3D 的 ExtrudeGeometry bevelThickness / bevelSize 同值。
 * three.js 的 bevel 会把整个侧壁沿 X-Y 外扩该尺寸（实测：墙面的轮廓 = 原始轮廓 + bevelSize），
 * 因此车身真实壁面位于 ROOF 轮廓之外 BODY_BEVEL_SIZE 处——贴面玻璃的偏移量必须 ≥ 该值，
 * 否则整块风挡/后风挡会沉入车身内部不可见。
 */
export const BODY_BEVEL_SIZE = 0.012

/** 玻璃带相对 bevel 外扩壁面的贴面间隙（米）：仅避免与车身共面 z-fighting */
export const GLASS_SURFACE_GAP = 0.001

/**
 * 车身玻璃洞口相对玻璃覆盖区的内缩量（米）：洞口四缘各内缩该尺寸，
 * 关门时玻璃叠压洞口边缘 → 无漏缝（封闭）；开门后洞口保留完整孔洞。
 * deriveDloApertures 默认值与本常量同源，Car3D 计算门洞肩线亦用它。
 */
export const DLO_APERTURE_INSET = 0.012

/**
 * 侧玻璃倾角（tumblehome，度）：侧窗面顶部向车身中线内收的角度，决定前视车肩造型。
 * 2D 侧视图无法表达该维度，为 3D 专属参数；可用 carParams.side_glass_angle 显式覆盖。
 * 参考真车：911/488 ≈ 25°+（车肩窄），Cayenne ≈ 12°，V级 ≈ 10°，F-150 ≈ 8°（车肩宽）
 */
export const SIDE_GLASS_TILT = {
  sedan: 18,
  suv: 12,
  coupe: 24,
  sport: 26,
  mpv: 10,
  pickup: 8
}

/**
 * 侧玻璃桶面（barrel）：玻璃沿高度的圆弧弯曲参数，决定前视玻璃鼓肚（外凸）造型。
 * angle = 玻璃底缘→顶缘的圆弧张角（度，0 = 平直），radius = 圆弧半径（mm）。
 * 顶缘额外内收量 = radius × (1 − cos angle)；可用 carParams.glass_barrel_angle /
 * glass_barrel_radius 显式覆盖（非法值自动回退车型默认）。
 * 参考真车：911/488 ≈ 10°/900mm（鼓肚明显），F-150 ≈ 4°/2200mm（近平直）
 */
export const SIDE_GLASS_BARREL = {
  sedan: { angle: 8, radius: 1200 },
  suv: { angle: 6, radius: 1600 },
  coupe: { angle: 10, radius: 900 },
  sport: { angle: 10, radius: 900 },
  mpv: { angle: 5, radius: 2000 },
  pickup: { angle: 4, radius: 2200 }
}

/**
 * 斜面玻璃带几何。
 * 底缘 (x1,y1) → 顶缘 (x2,y2)，顶缘按 topInset 沿斜线下退（避开柱顶 G1 圆角），
 * 底缘按 bottomInset 沿斜线上退（避开 COWL 直角 bevel 外扩角），
 * 两端再沿外法线抬离 offset（贴合被 bevel 外扩的车身侧壁）。
 * 法线统一朝上（ny ≥ 0，指向外表面），与下坡方向无关。
 * @returns {{ a: number[], b: number[], normal: number[] }} 抬升后的两端点与单位法线
 */
export function bandGlassEndpoints(x1, y1, x2, y2, topInset = 0, offset = 0, bottomInset = 0) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  let tx1 = x1
  let ty1 = y1
  let tx2 = x2
  let ty2 = y2
  if (topInset > 0) {
    const t = Math.min(topInset / len, 0.9)
    tx2 -= dx * t
    ty2 -= dy * t
  }
  if (bottomInset > 0) {
    const t = Math.min(bottomInset / len, 0.9)
    tx1 += dx * t
    ty1 += dy * t
  }
  let nx = dy / len
  let ny = -dx / len
  if (ny < 0) { nx = -nx; ny = -ny }   // 法线统一朝上（外表面）
  return {
    a: [tx1 + nx * offset, ty1 + ny * offset],
    b: [tx2 + nx * offset, ty2 + ny * offset],
    normal: [nx, ny]
  }
}

/**
 * 斜面玻璃带脊柱线（自底向顶有序，米制，可单测）。
 * 无 fillet：退化为「底缘→顶缘」两点（与 bandGlassEndpoints 同语义）。
 * 有 fillet：直线段止于圆角切点 a → 二次贝塞尔采样包裹圆角 → 沿 b 点切向
 *   向车顶延伸 roofOverlap 搭接——玻璃随车身同一 G1 圆角弯曲，消除
 *   「平顶玻璃 vs 圆角车身」的台阶折痕（风挡顶/车顶后缘折痕拓扑修复）。
 * 约定：fillet 按行进方向给——a = 斜面侧切点（入口）、b = 车顶侧切点（出口）；
 *   roofFilletSet.rear 的 a/b 与行进方向相反，调用方需交换后传入。
 * 每点沿局部外法线抬离 offset（贴合被 bevel 外扩的车身壁面），法线统一 ny ≥ 0。
 *   offset 渐减：A 柱段（ny = baseNy）满 offset；圆角段随法线朝车顶旋转
 *   （ny↑）线性递减；车顶搭接段（ny=1）offset=0 → 玻璃与车顶齐平，
 *   消除「玻璃顶高出车顶 3cm」的台阶折痕。
 * @param {object} opts { topInset, bottomInset, offset, fillet: {a,ctrl,b}|null,
 *   filletSamples, roofOverlap, minOffsetRatio（默认 0；1 = 全程等距贴面） }
 * @returns {number[][]} [[x,y],…] 脊柱点（含 offset），底→顶
 */
export function bandGlassSpine(x1, y1, x2, y2, opts = {}) {
  const {
    topInset = 0, bottomInset = 0, offset = 0, fillet = null,
    filletSamples = 6, roofOverlap = 0.02, minOffsetRatio = 0
  } = opts
  const dx = x2 - x1, dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  let nx = dy / len, ny = -dx / len
  if (ny < 0) { nx = -nx; ny = -ny }   // 法线统一朝上（外表面）
  const baseNy = ny
  // offset 乘数：法线未朝上翘时（A 柱斜面）为 1；法线朝车顶（ny→1）时线性降到
  // minOffsetRatio（默认 0 → 玻璃顶与车顶齐平；传 1 → 全程等距贴面，保持 1~2mm
  // 恒定间隙，避免与车身共面产生 z-fighting）
  const offsetMult = (nYy) => {
    if (nYy <= baseNy) return 1
    if (nYy >= 1) return minOffsetRatio
    const t = (1 - nYy) / (1 - baseNy)
    return minOffsetRatio + (1 - minOffsetRatio) * t
  }
  const pts = []
  const push = (x, y, nX, nY) => {
    const m = offsetMult(nY)
    pts.push([x + nX * offset * m, y + nY * offset * m])
  }
  // 底点（bottomInset 沿斜线上退）
  let bx = x1, by = y1
  if (bottomInset > 0) {
    const t = Math.min(bottomInset / len, 0.9)
    bx += dx * t; by += dy * t
  }
  push(bx, by, nx, ny)
  if (!fillet) {
    let tx = x2, ty = y2
    if (topInset > 0) {
      const t = Math.min(topInset / len, 0.9)
      tx -= dx * t; ty -= dy * t
    }
    push(tx, ty, nx, ny)
    return pts
  }
  // 圆角包裹段：直线止于切点 a，贝塞尔采样至 b，再沿车顶切向搭接
  const { a, ctrl, b } = fillet
  push(a[0], a[1], nx, ny)
  const N = Math.max(2, Math.round(filletSamples))
  for (let i = 1; i <= N; i++) {
    const t = i / N
    const omt = 1 - t
    const px = omt * omt * a[0] + 2 * t * omt * ctrl[0] + t * t * b[0]
    const py = omt * omt * a[1] + 2 * t * omt * ctrl[1] + t * t * b[1]
    const dtx = 2 * omt * (ctrl[0] - a[0]) + 2 * t * (b[0] - ctrl[0])
    const dty = 2 * omt * (ctrl[1] - a[1]) + 2 * t * (b[1] - ctrl[1])
    const tl = Math.hypot(dtx, dty) || 1
    let fnx = dty / tl, fny = -dtx / tl
    if (fny < 0) { fnx = -fnx; fny = -fny }
    push(px, py, fnx, fny)
  }
  const ex = b[0] - ctrl[0], ey = b[1] - ctrl[1]
  const el = Math.hypot(ex, ey) || 1
  push(b[0] + (ex / el) * roofOverlap, b[1] + (ey / el) * roofOverlap, 0, 1)
  return pts
}

/**
 * 点是否落在闭合多边形内部（even-odd 射线法）。
 * 顶点可为 THREE.Vector2（{x,y}）或 [x,y] 数组；边界点按「不在内部」处理——
 * 车身外轮廓上的外皮三角形必须保留车身色，不能算作实体内部。
 * @param {number} x
 * @param {number} y
 * @param {Array<{x:number,y:number}|number[]>} poly 闭合多边形顶点
 * @returns {boolean}
 */
export function pointInPolygon(x, y, poly) {
  let inside = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const p = poly[i]
    const q = poly[j]
    const xi = p.x !== undefined ? p.x : p[0]
    const yi = p.y !== undefined ? p.y : p[1]
    const xj = q.x !== undefined ? q.x : q[0]
    const yj = q.y !== undefined ? q.y : q[1]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

/**
 * 点到多边形边界的最短距离（米）。
 * @param {number} x
 * @param {number} y
 * @param {Array<{x:number,y:number}|number[]>} poly 闭合多边形顶点
 * @returns {number}
 */
export function polygonEdgeDistance(x, y, poly) {
  let best = Infinity
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const p = poly[i]
    const q = poly[j]
    const xi = p.x !== undefined ? p.x : p[0]
    const yi = p.y !== undefined ? p.y : p[1]
    const xj = q.x !== undefined ? q.x : q[0]
    const yj = q.y !== undefined ? q.y : q[1]
    const ex = xj - xi
    const ey = yj - yi
    const l2 = ex * ex + ey * ey
    const t = l2 > 0 ? Math.min(Math.max(((x - xi) * ex + (y - yi) * ey) / l2, 0), 1) : 0
    const d = Math.hypot(x - (xi + ex * t), y - (yi + ey * t))
    if (d < best) best = d
  }
  return best
}

/**
 * 点是否属于车身内部的「洞口壁/洞口倒角环带」——用于洞壁内饰化。
 *
 * 车身整宽挤出且开倒角后，外皮侧壁位于轮廓线**外侧** BODY_BEVEL_SIZE 处，
 * 而洞口隧道壁、洞口倒角环带位于轮廓内部；二者在 X-Y 上都会被洞口口径矩形圈住，
 * 只看矩形无法区分（旧实现把车顶前缘/风挡边框一并染深，透视下呈黑色边带）。
 * 本判据：严格在轮廓内部 → true；轮廓线上或轮廓外侧（外皮/倒角外扩带）→ false。
 * 洞口多边形内的点不算「外侧」——洞口倒角环带恰落在洞口边界内侧，仍需改判内饰。
 * @param {number} x
 * @param {number} y
 * @param {Array} outline 外轮廓多边形
 * @param {number} [edgeTol] 轮廓线容差（米）
 * @returns {boolean}
 */
export function insideBodyMaterial(x, y, outline, edgeTol = 0.001) {
  if (polygonEdgeDistance(x, y, outline) <= edgeTol) return false
  return pointInPolygon(x, y, outline)
}

/**
 * 求圆角二次贝塞尔曲线上指定高度 y 处的 X 坐标。
 * filletCorner 的 ctrl = 角点本身，轮廓圆角实为二次贝塞尔
 * P(t) = (1−t)²a + 2t(1−t)ctrl + t²b；本函数解 y(t) = y 的参数 t ∈ [0,1]，
 * 再代入 x(t)。供 DLO 顶后角等修裁点精确贴合圆角轮廓（避免台阶/戳出）。
 * @param {{ a: number[], ctrl: number[], b: number[] }} f filletCorner 返回值
 * @param {number} y 目标高度（须在 a_y 与 b_y 之间，越界按端点钳位语义处理）
 * @returns {number|null} 该高度的 X；无 [0,1] 内的根（y 超出曲线高度范围）返回 null
 */
export function filletXAtY(f, y) {
  const [ax, ay] = f.a
  const [cx, cy] = f.ctrl
  const [bx, by] = f.b
  // y(t) = A2·t² + B2·t + C2，A2 = a_y − 2c_y + b_y，B2 = 2(c_y − a_y)，C2 = a_y − y
  const A2 = ay - 2 * cy + by
  const B2 = 2 * (cy - ay)
  const C2 = ay - y
  const EPS = 1e-12
  const roots = []
  if (Math.abs(A2) < EPS) {
    if (Math.abs(B2) > EPS) {
      roots.push(-C2 / B2)
    } else if (Math.abs(C2) < EPS) {
      roots.push(0)   // 整条曲线与 y 同高（全水平圆角）：取起点 t=0
    }
  } else {
    const D = B2 * B2 - 4 * A2 * C2
    if (D >= 0) {
      const sq = Math.sqrt(D)
      roots.push((-B2 - sq) / (2 * A2), (-B2 + sq) / (2 * A2))
    }
  }
  // 取 [0,1] 内离 t=0 最近的根（轮廓圆角 y 向单调，实际至多一个有效根）
  const valid = roots
    .filter((t) => t >= -EPS && t <= 1 + EPS)
    .map((t) => Math.min(Math.max(t, 0), 1))
    .sort((p, q) => p - q)
  if (!valid.length) return null
  const t = valid[0]
  const omt = 1 - t
  return omt * omt * ax + 2 * t * omt * cx + t * t * bx
}

/**
 * 由 deriveCarProfile 结果派生座舱玻璃面板布局（纯函数）。
 * @param {object} P deriveCarProfile 返回值
 * @param {object} [opts] 可选项：carType（车型，决定默认倾角/桶面）、
 *   sideGlassAngle（carParams.side_glass_angle 覆盖，非法值自动回退）、
 *   glassBarrelAngle（carParams.glass_barrel_angle 覆盖，0≤角≤20°）、
 *   glassBarrelRadius（carParams.glass_barrel_radius 覆盖，400≤半径≤5000mm）
 * @returns {{
 *   windshield: { x1, y1, x2, y2, width, topInset, bottomInset },
 *   rearWindow: { x1, y1, x2, y2, width, topInset } | null,  // 皮卡为 null（驾驶室后壁为车身）
 *   dlo: number[][],            // 侧窗四边形 [底前, 顶前, 顶后, 底后]
 *   dloTopRear: number,
 *   dloBotRear: number,
 *   pillar: { x, topY, botY },  // B 柱（车身色）中心线与上下端
 *   tiltDeg: number,            // 侧玻璃倾角（度，B 柱与侧窗共面同角）
 *   tiltInsetZ: number,         // 倾角单独引起的顶边 Z 内收（米）
 *   barrelAngle: number,        // 侧玻璃桶面角（度）
 *   barrelRadius: number,       // 侧玻璃桶面半径（米）
 *   dloTopInsetZ: number        // DLO 顶边相对底边的 Z 向总内收（米）= tiltInsetZ + 桶面内收
 * }}
 */
export function deriveCabinGlass(P, opts = {}) {
  const {
    W, roofTopY, beltLineY, hoodEndX, windshieldTopX,
    rearWindowTopX, rearWindowBottomX, pickup
  } = P

  // 皮卡专属拓扑：驾驶室后壁为车身，无后风挡；DLO 止于驾驶室后壁
  const dloTopRear = pickup ? pickup.cabRearX : rearWindowTopX
  const dloBotRear = pickup ? pickup.cabWindowBottomX : rearWindowBottomX

  // 侧玻璃倾角：显式覆盖优先（0<角<45° 合法），否则按车型默认
  const raw = Number(opts.sideGlassAngle)
  const carType = opts.carType || (pickup ? 'pickup' : 'sedan')
  const tiltDeg = (Number.isFinite(raw) && raw > 0 && raw < 45)
    ? raw
    : (SIDE_GLASS_TILT[carType] ?? 15)

  // 侧玻璃桶面：显式覆盖优先（角 0~20°、半径 400~5000mm 合法），否则按车型默认
  const barrelDefault = SIDE_GLASS_BARREL[carType] ?? { angle: 8, radius: 1200 }
  const rawBA = Number(opts.glassBarrelAngle)
  const rawBR = Number(opts.glassBarrelRadius)
  const barrelAngle = (Number.isFinite(rawBA) && rawBA >= 0 && rawBA <= 20)
    ? rawBA
    : barrelDefault.angle
  const barrelRadiusMm = (Number.isFinite(rawBR) && rawBR >= 400 && rawBR <= 5000)
    ? rawBR
    : barrelDefault.radius
  const barrelRadius = barrelRadiusMm / 1000

  const dloTopY = roofTopY - 0.035
  const dloBotY = beltLineY + 0.008
  const tiltInsetZ = (dloTopY - dloBotY) * Math.tan((tiltDeg * Math.PI) / 180)
  const barrelInsetZ = barrelRadius * (1 - Math.cos((barrelAngle * Math.PI) / 180))
  const dloTopInsetZ = tiltInsetZ + barrelInsetZ

  // ---- 车顶三角 G1 圆角（与 Car3D.vue bodyShape 同参同源，ROOF_FILLETS 单一真源）----
  // f2 = 车顶后缘圆角（DLO 顶后角修裁量依据）；f3 = C 柱底圆角（DLO 底后角修裁量依据）
  const f2 = pickup
    ? filletCorner(windshieldTopX, roofTopY, pickup.cabRearX, roofTopY,
        pickup.cabBaseX, pickup.bedWallY, ROOF_FILLETS.pickupCabTop)
    : filletCorner(windshieldTopX, roofTopY, rearWindowTopX, roofTopY,
        rearWindowBottomX, beltLineY, ROOF_FILLETS.roofRear)
  const f3 = pickup
    ? null   // 皮卡 DLO 底后角审计干净，无需修裁
    : (() => {
        const tailCtrlX = P.rearX + 0.02
        const tailCtrlY = P.trunkLineY - 0.016
        return filletCorner(rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY,
          tailCtrlX, tailCtrlY, ROOF_FILLETS.cPillarBottom)
      })()

  // DLO 顶后角 X：精确落于车顶后缘圆角轮廓内侧 6mm（filletXAtY 解贝塞尔）；
  // y 超出圆角范围（null）时回退：角点 → 底后角直线插值（轮廓无该圆角的几何退化）
  const f2xAtTop = filletXAtY(f2, dloTopY)
  const dlo2X = f2xAtTop !== null
    ? f2xAtTop + 0.006
    : dloTopRear + (dloBotRear - dloTopRear) * ((roofTopY - dloTopY) / ((roofTopY - beltLineY) || 1))

  // DLO 底后角：非皮卡沿 C 柱斜线上退 min(r3+0.014, 斜线长×0.45) 避开圆角切线区，
  // 再向车头方向内移 4mm 落入轮廓内；
  // 皮卡：底后角精确落在驾驶室后壁直线上（按后壁直线方程在 dloBotY 高度插值）
  let dlo3X = dloBotRear
  let dlo3Y = dloBotY
  if (pickup) {
    const frac = (roofTopY - dloBotY) / (pickup.cabWallDrop || 1)
    dlo3X = pickup.cabRearX - pickup.cabWallRun * frac
    dlo3Y = dloBotY
  } else {
    const cdx = rearWindowTopX - rearWindowBottomX
    const cdy = roofTopY - beltLineY
    const clen = Math.hypot(cdx, cdy) || 1
    const back = Math.min(ROOF_FILLETS.cPillarBottom + 0.014, clen * 0.45)
    dlo3X = rearWindowBottomX + (cdx / clen) * back + 0.004
    dlo3Y = beltLineY + (cdy / clen) * back
  }

  // DLO 底前角：精确落于 A 柱斜线上再向车尾内移 4mm（原锚 hoodEndX 角点
  // 在 y=dloBotY 高度已越过斜线轮廓 6~20mm）
  const guardSpan = (roofTopY - beltLineY) || 1
  const rakeAtBot = hoodEndX + (windshieldTopX - hoodEndX) * ((dloBotY - beltLineY) / guardSpan)

  return {
    // 前风挡：底缘 = COWL，顶缘 = 车顶前缘；顶缘下退留出车身色顶带（A 柱顶圆角），
    // 底缘下退避开 COWL 直角 bevel 外扩角（cowl 面板裸露符合真车）
    windshield: {
      x1: hoodEndX, y1: beltLineY,
      x2: windshieldTopX, y2: roofTopY,
      width: W * 0.9, topInset: ROOF_FILLETS.aPillarTop, bottomInset: 0.06
    },
    // 后风挡：顶缘 = 车顶后缘，底缘 = 行李箱前缘
    rearWindow: pickup ? null : {
      x1: rearWindowBottomX, y1: beltLineY,
      x2: rearWindowTopX, y2: roofTopY,
      width: W * 0.88, topInset: ROOF_FILLETS.roofRear
    },
    // 侧窗 DLO：四角按轮廓 G1 圆角修裁（3D 拓扑合法；2D windowPath 为理论框示意）
    dlo: [
      [rakeAtBot - 0.004, dloBotY],
      [windshieldTopX + 0.012, dloTopY],
      [dlo2X, dloTopY],
      [dlo3X, dlo3Y]
    ],
    dloTopRear,
    dloBotRear,
    // B 柱：55% 分段处车身色立柱（叠于玻璃之上，与 2D B 柱线同位置）；
    // 顶端搭入 DLO 顶边之下 2mm（原 roofTopY−0.05 悬浮于玻璃面外 15mm）
    pillar: {
      x: windshieldTopX + (dloTopRear - windshieldTopX) * 0.55,
      topY: dloTopY + 0.002,
      botY: beltLineY + 0.035
    },
    tiltDeg,
    tiltInsetZ,
    barrelAngle,
    barrelRadius,
    dloTopInsetZ
  }
}

/**
 * DLO 玻璃面在高度 y 处的 Z 坐标（tumblehome 线性内收 + barrel 圆弧鼓肚）。
 * 内收量 inset(t) = t × tiltInsetZ + radius × (1 − cos(barrelRad × t))，t ∈ [0,1]：
 *   - barrelRad/barrelRadius 缺省或为 0 时退化为纯倾角线性内收（向后兼容）；
 *   - 桶面使中段相对端点连线外凸（真车玻璃鼓肚），顶边总内收 = tiltInsetZ + radius×(1−cos barrelRad)。
 * 底边（y = dloYBot）位于 dloZBase，超出 [dloYBot, dloYBot + dloYSpan] 的高度按边界钳位。
 * 框架参数兼容两种写法：tiltInsetZ（纯倾角内收）优先，缺省回退 dloTopInsetZ（总内收）。
 * zSide=1 为左片（+Z），zSide=-1 为右片镜像。
 * @param {number} y 目标高度
 * @param {{ dloYBot: number, dloYSpan: number, tiltInsetZ?: number, dloTopInsetZ?: number,
 *           barrelRad?: number, barrelRadius?: number, dloZBase: number }} f DLO 框架参数
 * @param {1|-1} zSide 侧别
 * @returns {number} 该高度的 Z 坐标（带侧别符号）
 */
export function dloZAt(y, f, zSide) {
  const span = f.dloYSpan || 1
  const t = Math.min(Math.max((y - f.dloYBot) / span, 0), 1)
  const tiltInset = f.tiltInsetZ ?? f.dloTopInsetZ ?? 0
  const br = f.barrelRad || 0
  const bR = f.barrelRadius || 0
  const barrel = (br > 0 && bR > 0) ? bR * (1 - Math.cos(br * t)) : 0
  return zSide * (f.dloZBase - t * tiltInset - barrel)
}

/**
 * B 柱定位与姿态（底部锚定 DLO 玻璃面在 pillar.botY 高度处的 Z，与 dloZAt 同公式保证共面），
 * 绕底旋转 tiltDeg（rotation.x = -zSide × tiltRad）。
 * @returns {{ x, botY, height, baseZ, tiltRad }} baseZ 为 zSide=1 时底部 |Z|
 */
export function pillarPlacement(cabin, dloYBot, dloYSpan, dloZBase) {
  const span = dloYSpan || 1
  const baseZ = Math.abs(dloZAt(cabin.pillar.botY, {
    dloYBot,
    dloYSpan,
    dloZBase,
    tiltInsetZ: span * Math.tan((cabin.tiltDeg * Math.PI) / 180),
    barrelRad: ((cabin.barrelAngle || 0) * Math.PI) / 180,
    barrelRadius: cabin.barrelRadius || 0
  }, 1))
  return {
    x: cabin.pillar.x,
    botY: cabin.pillar.botY,
    height: cabin.pillar.topY - cabin.pillar.botY,
    baseZ,
    tiltRad: (cabin.tiltDeg * Math.PI) / 180
  }
}

/**
 * DLO 条带网格框架（由 deriveCabinGlass 结果 + 底边 Z 基准构建），
 * 供 dloZAt / buildDloStrip 消费：角度→弧度换算在此集中完成。
 * @param {object} cabin deriveCabinGlass 返回值
 * @param {number} zBase DLO 底边 Z 基准（米，车身侧壁外表面）
 * @returns {{ dloYBot, dloYSpan, tiltInsetZ, barrelRad, barrelRadius, dloZBase }}
 */
export function buildDloFrame(cabin, zBase) {
  return {
    dloYBot: cabin.dlo[0][1],
    dloYSpan: cabin.dlo[1][1] - cabin.dlo[0][1],
    tiltInsetZ: cabin.tiltInsetZ,
    barrelRad: ((cabin.barrelAngle || 0) * Math.PI) / 180,
    barrelRadius: cabin.barrelRadius || 0,
    dloZBase: zBase
  }
}

/**
 * DLO 条带网格顶点序列（沿高度 rows 段细分，每段两三角形，表达桶面曲率）。
 * 四角 X 边界（dlo = [底前, 顶前, 顶后, 底后]）随高度线性收拢（与原四边形边界一致），
 * Z 由 dloZAt 按行插值（倾角 + 桶面）。每行 6 顶点 × 3 分量 = 18 个数值。
 * @param {number[][]} dlo 四角坐标
 * @param {object} frame buildDloFrame 返回值
 * @param {number} rows 细分行数（≥1）
 * @param {1|-1} zSide 侧别
 * @returns {number[]} 长度 = rows × 18 的顶点序列（x,y,z 交错）
 */
export function buildDloStrip(dlo, frame, rows, zSide) {
  const bfx = dlo[0][0]
  const tfx = dlo[1][0]
  const brxB = dlo[3][0]
  const trx = dlo[2][0]
  const positions = []
  for (let r = 0; r < rows; r++) {
    const t0 = r / rows
    const t1 = (r + 1) / rows
    const y0 = frame.dloYBot + t0 * frame.dloYSpan
    const y1 = frame.dloYBot + t1 * frame.dloYSpan
    const z0 = dloZAt(y0, frame, zSide)
    const z1 = dloZAt(y1, frame, zSide)
    const fx0 = bfx + (tfx - bfx) * t0
    const fx1 = bfx + (tfx - bfx) * t1
    const rx0 = brxB + (trx - brxB) * t0
    const rx1 = brxB + (trx - brxB) * t1
    positions.push(
      fx0, y0, z0, rx0, y0, z0, fx1, y1, z1,
      rx0, y0, z0, rx1, y1, z1, fx1, y1, z1
    )
  }
  return positions
}

/**
 * DLO 条带网格「按门缝纵向切片」版本（侧窗分片供车门联动）。
 * 与 buildDloStrip 同一套行插值/Z 公式，仅把每行的水平跨度裁到 [xFront, xRear]：
 *   xFront/xRear 为世界 X（米，X+ 朝车头）；null 表示取该行的 DLO 前/后缘（A/C 柱边界）。
 * 裁切界为「竖直线」——给定 X 逐行夹到该行跨度内，越出时贴合 A/C 柱斜边，
 * 因此门缝在玻璃上是竖直的，两端随 A/C 柱收口。
 * @param {number[][]} dlo 四角坐标 [底前, 顶前, 顶后, 底后]
 * @param {object} frame buildDloFrame 返回值
 * @param {number} rows 细分行数（≥1）
 * @param {1|-1} zSide 侧别
 * @param {number|null} xFront 前边界世界 X（null = DLO 前缘）
 * @param {number|null} xRear 后边界世界 X（null = DLO 后缘）
 * @returns {number[]} 长度 = rows × 18 的顶点序列（x,y,z 交错）
 */
export function buildDloStripRange(dlo, frame, rows, zSide, xFront = null, xRear = null) {
  const bfx = dlo[0][0]
  const tfx = dlo[1][0]
  const brxB = dlo[3][0]
  const trx = dlo[2][0]
  const clampX = (x, fx, rx) => Math.min(Math.max(x, rx), fx)   // 前缘 X 更大
  const positions = []
  for (let r = 0; r < rows; r++) {
    const t0 = r / rows
    const t1 = (r + 1) / rows
    const y0 = frame.dloYBot + t0 * frame.dloYSpan
    const y1 = frame.dloYBot + t1 * frame.dloYSpan
    const z0 = dloZAt(y0, frame, zSide)
    const z1 = dloZAt(y1, frame, zSide)
    const fx0 = bfx + (tfx - bfx) * t0
    const rx0 = brxB + (trx - brxB) * t0
    const fx1 = bfx + (tfx - bfx) * t1
    const rx1 = brxB + (trx - brxB) * t1
    const ax0 = xFront == null ? fx0 : clampX(xFront, fx0, rx0)
    const ax1 = xFront == null ? fx1 : clampX(xFront, fx1, rx1)
    const bx0 = xRear == null ? rx0 : clampX(xRear, fx0, rx0)
    const bx1 = xRear == null ? rx1 : clampX(xRear, fx1, rx1)
    positions.push(
      ax0, y0, z0, bx0, y0, z0, ax1, y1, z1,
      bx0, y0, z0, bx1, y1, z1, ax1, y1, z1
    )
  }
  return positions
}

/**
 * 侧窗 DLO 分片划分（Car3D 消费端纯函数）
 *
 * 侧窗按车门分缝切成 4 片/侧：A 柱前固定片 → 前门片 → 后门片 → C 柱后固定片。
 * 分缝两侧各让出半个缝宽，使相邻两片之间恰好留出一个缝宽的空隙——
 * 玻璃上的门缝因此与 2D 分缝线、车身门缝同位同宽。
 * 双门车型（coupe/sport）与皮卡无后门：doorLayout.rearSeamX 为 null，
 * 此时后门片不存在，后固定片直接从 B 柱接缝之后起算。
 *
 * @param {{ frontSeamX: number, midSeamX: number, rearSeamX: number|null }} doorLayout
 *        deriveDoorLayout 返回值（X+ 朝车头，前缘 X 更大）
 * @param {number} seamWidthMM 门缝宽度（毫米），与车身门缝同一参数
 * @returns {Array<{ key: string, xFront: number|null, xRear: number|null, hingeKey: string|null }>}
 *          xFront/xRear 为世界 X；null 表示该片直接贴到 DLO 前/后缘（由 buildDloStripRange 夹取）
 */
export function deriveDloPaneRanges(doorLayout, seamWidthMM = 8) {
  const gap = Math.min(Math.max(seamWidthMM, 2), 20) / 2000
  const { frontSeamX, midSeamX, rearSeamX } = doorLayout
  const panes = [
    { key: 'fixedFront', xFront: null, xRear: frontSeamX + gap, hingeKey: null },
    { key: 'front', xFront: frontSeamX - gap, xRear: midSeamX + gap, hingeKey: 'front' }
  ]
  if (rearSeamX !== null) {
    panes.push({ key: 'rear', xFront: midSeamX - gap, xRear: rearSeamX + gap, hingeKey: 'rear' })
  }
  panes.push({
    key: 'fixedRear',
    xFront: rearSeamX === null ? midSeamX - gap : rearSeamX - gap,
    xRear: null,
    hingeKey: null
  })
  return panes
}

/**
 * 侧窗分片玻璃「洞口」多边形（Car3D 车身挖洞纯函数，可单测）
 *
 * 玻璃要成为真透明件，车身侧围必须在玻璃覆盖区开出真实孔洞（挤出 holes 沿 Z
 * 贯通左右侧壁）；关门时玻璃盖住洞口封闭，开门时门片玻璃随门外摆、原位置
 * 留下全空通透的孔洞。本函数给每片玻璃生成对应的洞口多边形：
 *   · 洞口整体内缩 inset（玻璃四缘各叠压 inset → 关门无漏缝 = 封闭）；
 *   · 贴 DLO 缘的片（fixedFront/fixedRear 的 null 界）洞口边**随 A/C 柱斜边**，
 *     与玻璃逐行 clamp 的覆盖界同形（buildDloStripRange 前/后缘逐行贴合斜边），
 *     保证每个高度上洞口都落在玻璃覆盖之内；
 *   · 斜边片呈上窄下宽：若顶部有效宽不足 minWidth，洞口顶边下裁到
 *     有效宽 = minWidth 的高度（梯形截顶），仍保持处处密封；
 *   · 相邻洞口之间保留车身色竖条 = A/B/C 柱剪影与车顶横梁（车身色顶部边界
 *     与玻璃因此清晰区分，不再是玻璃贴在整片车身色壁上）。
 * 退化守卫：底部有效宽已 < minWidth（极端参数）时跳过该片（不挖洞，玻璃贴实体，
 * 不产生拓扑破面）。
 *
 * @param {number[][]} dlo 侧窗四角 [底前, 顶前, 顶后, 底后]（deriveCabinGlass.dlo）
 * @param {Array<{ key:string, xFront:number|null, xRear:number|null }>} paneRanges
 *        deriveDloPaneRanges 返回值（xFront/xRear 为玻璃竖直裁切界，null=贴 DLO 缘）
 * @param {number} [inset=DLO_APERTURE_INSET] 洞口相对玻璃覆盖的内缩（米）
 * @param {number} [minWidth=0.03] 洞口最小有效宽度（米），不足则截顶/跳过
 * @returns {Array<{ key:string, points:number[][] }>} 洞口多边形 [[x,y]×4]
 *          点序：底前→顶前→顶后→底后（供 THREE.Path 按序连线）
 */
export function deriveDloApertures(dlo, paneRanges, inset = DLO_APERTURE_INSET, minWidth = 0.03) {
  const [bf, tf, tr, br] = dlo
  const yBot0 = bf[1]
  const yTop0 = tf[1]
  const span = Math.max(yTop0 - yBot0, 1e-6)
  const t0 = inset / span
  const t1 = 1 - inset / span
  if (t1 - t0 < 0.02) return []
  const yAt = (t) => yBot0 + t * span
  // DLO 前/后斜边在高度比例 t 处的 X（与 buildDloStripRange 行插值同公式）
  const fxAt = (t) => bf[0] + (tf[0] - bf[0]) * t
  const rxAt = (t) => br[0] + (tr[0] - br[0]) * t
  const out = []
  for (const pane of paneRanges) {
    // 前/后覆盖界：显式缝界为竖直线；null 界随 DLO 斜边（玻璃逐行贴合）
    const F = (t) => (pane.xFront == null ? fxAt(t) : pane.xFront)
    // C 柱顶后角设计间隙仅 6mm（deriveCabinGlass 圆角修裁）：贴 C 柱斜边的
    // 洞口后缘内缩取 6mm 上限，防止洞口顶后角戳出侧围轮廓（holes 越界会打破
    // 挤出三角化）
    const insetR = pane.xRear == null ? Math.min(inset, 0.006) : inset
    const R = (t) => (pane.xRear == null ? rxAt(t) : pane.xRear)
    // 玻璃前缘实为「竖缝 + A 柱斜边」两段：低于斜边交点处贴缝，高于交点贴斜边。
    // 洞口前界必须同样逐段内缩——显式缝界若直通顶边，A 柱根部（dlo 顶边已高于
    // 侧围轮廓处）会把洞口戳出车身外轮廓，挤出三角化随即在轮廓外生成洞壁，
    // 从车外看就是风挡上方一块外凸的深色厚板。
    const Feff = (t) => (pane.xFront == null ? fxAt(t) : Math.min(pane.xFront, fxAt(t)))
    const widthAt = (t) => Feff(t) - inset - (R(t) + insetR)
    if (widthAt(t0) < minWidth) continue          // 底部已退化：整片跳过
    // 顶部有效宽不足时截顶（width 沿 t 线性 → 单调，直接线性插值求临界高度）
    let tTop = t1
    if (widthAt(t1) < minWidth) {
      const w0 = widthAt(t0)
      const w1 = widthAt(t1)
      tTop = t0 + (t1 - t0) * ((w0 - minWidth) / (w0 - w1))
    }
    const points = [[Feff(t0) - inset, yAt(t0)]]
    // 显式竖缝与 A 柱斜边的交点（位于洞口高度范围内时补折点，保持每段都内缩）：
    // 交点处竖缝 X = 斜边 X，等同 fxAt(t) = pane.xFront
    if (pane.xFront != null) {
      const dx = tf[0] - bf[0]
      if (Math.abs(dx) > 1e-9) {
        const tKink = (pane.xFront - bf[0]) / dx
        if (tKink > t0 + 1e-9 && tKink < tTop - 1e-9) {
          points.push([pane.xFront - inset, yAt(tKink)])
        }
      }
    }
    points.push(
      [Feff(tTop) - inset, yAt(tTop)],
      [R(tTop) + insetR, yAt(tTop)],
      [R(t0) + insetR, yAt(t0)]
    )
    out.push({ key: pane.key, points })
  }
  return out
}

/**
 * 车门合并洞口多边形（Car3D 车身挖洞纯函数，可单测）
 *
 * 门洞（腰带线以下）与门片玻璃洞口（腰带线以上）各挖一个孔时，两者之间必然残留
 * 一条 20~30mm 的车身色横带——开门后即门洞里横贯两侧的「腰带横条」，既遮挡
 * 通透性，又让车身色越过了「只允许出现在车顶/柱」的视觉边界。本函数把二者合并成
 * 一个简单多边形：肩线 shoulderY 处水平连通，两块门片玻璃洞口在肩上形成两个塔楼，
 * 塔楼之间（B 柱位置）保持肩线高度，门洞其余部分仍是矩形。
 * 退出条件：塔楼底边必须恰在肩线、X 范围严格落在门洞内且彼此不重叠，任一不满足
 * 即返回 null（调用方退回纯门洞矩形，绝不产生自交 holes）。
 *
 * @param {object} o
 * @param {number} o.frontEdge 门洞前缘 X（米，X+ 朝车头，数值较大）
 * @param {number} o.rearEdge 门洞后缘 X（米，数值较小）
 * @param {number} o.bottomY 门洞底缘 Y（米）
 * @param {number} o.shoulderY 肩线 Y（米）= 玻璃洞口底边 Y（= DLO 底边 + 内缩量）
 * @param {Array<number[][]>} [o.panes] 门片玻璃洞口四点多边形（deriveDloApertures.points）
 * @returns {number[][]|null} 多边形顶点（底后→底前→肩线→塔楼…），首点不重复
 */
export function buildDoorAperturePolygon({ frontEdge, rearEdge, bottomY, shoulderY, panes = [] }) {
  if (!(frontEdge > rearEdge) || !(shoulderY > bottomY)) return null
  const EPS = 1e-6
  const towers = []
  for (const pts of panes) {
    if (!pts || pts.length < 4) continue
    const xs = pts.map((p) => p[0])
    const ys = pts.map((p) => p[1])
    const xMin = Math.min(...xs)
    const xMax = Math.max(...xs)
    const yBot = Math.min(...ys)
    const yTop = Math.max(...ys)
    if (Math.abs(yBot - shoulderY) > EPS) return null      // 塔楼底与肩线不齐：无法合并
    if (xMin < rearEdge + EPS || xMax > frontEdge - EPS) return null
    if (yTop <= shoulderY + EPS) return null               // 塔楼过矮：退化
    towers.push({ xMin, xMax, yTop, points: pts })
  }
  towers.sort((a, b) => b.xMax - a.xMax)                   // 前缘→后缘，与走向一致
  for (let i = 1; i < towers.length; i++) {
    if (towers[i].xMax > towers[i - 1].xMin + EPS) return null   // 塔楼 X 重叠
  }
  const pts = [[rearEdge, bottomY], [frontEdge, bottomY], [frontEdge, shoulderY]]
  // 塔楼按自身多边形轮廓接入（底前→前缘折点→顶前→顶后→底后），
  // 保留 A 柱斜边折点——若按 X 包围盒还原成矩形，塔楼顶前角会再次戳出侧围轮廓
  for (const t of towers) {
    for (const p of t.points) pts.push([p[0], p[1]])
  }
  pts.push([rearEdge, shoulderY])
  return pts
}

/**
 * 车身 greenhouse 在高度 y 处的侧壁内收量（米）。
 * 与 DLO 玻璃面同公式（倾角线性 + 桶面圆弧，t 按 [dloYBot, dloYBot+dloYSpan] 钳位），
 * 供车身挤出体/玻璃带做 Z 向收窄变形——车身侧壁、车顶、柱剪影随玻璃角度联动，
 * 玻璃面（dloZAt，基准 dloZBase）始终位于收窄后车身外侧同一间隙。
 * @param {number} y 目标高度
 * @param {object} frame buildDloFrame 返回值
 * @returns {number} 内收量（≥0，底边处为 0）
 */
export function greenhouseInsetAt(y, frame) {
  return frame.dloZBase - Math.abs(dloZAt(y, frame, 1))
}

/**
 * 车身外壳在高度 y 处的侧向半宽（米）——车身收窄与全部玻璃共用的唯一 Z 公式。
 *
 * 任意以 baseHalfZ 为「腰带线处半宽」的壳层，其侧壁半宽 = baseHalfZ − greenhouseInsetAt(y)。
 * 车身（baseHalfZ = bodyExtentZ）、风挡带（baseHalfZ = band 半宽）、DLO 玻璃
 * （baseHalfZ = dloZBase）因此共享同一条内收曲线，不存在两套基准：
 *   - DLO 玻璃：|dloZAt| − shellHalfZAt(y, frame, bodyExtentZ) ≡ 2mm（buildDloFrame 的 +0.002）
 *   - 风挡带：halfZ = bandHalfZ × taper 恒小于车身半宽 → 不可能越界成薄片
 * 下限 minRatio 防止极端倾角把壳层压穿中线。
 * @param {number} y 目标高度
 * @param {object} frame buildDloFrame 返回值
 * @param {number} baseHalfZ 腰带线处的基准半宽（米）
 * @param {number} [minRatio=0.35] 最小收缩比例
 * @returns {number} 该高度的外壳半宽（米）
 */
export function shellHalfZAt(y, frame, baseHalfZ, minRatio = 0.35) {
  return Math.max(baseHalfZ - greenhouseInsetAt(y, frame), baseHalfZ * minRatio)
}
