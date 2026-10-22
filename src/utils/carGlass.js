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
        pickup.cabWindowBottomX, pickup.bedWallY, ROOF_FILLETS.pickupCabTop)
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
  // 再向车头方向内移 4mm 落入轮廓内（皮卡保持驾驶室后壁锚点不变）
  let dlo3X = dloBotRear
  let dlo3Y = dloBotY
  if (!pickup) {
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
