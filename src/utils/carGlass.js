// 座舱玻璃划分纯函数（无 Three.js 依赖，可单测）
//
// 职责：由 deriveCarProfile 的结果派生 3D 座舱「玻璃 / 车身」两种状态的几何参数，
//       供 Car3D.vue 兜底路径（ExtrudeGeometry）构建玻璃网格与 B 柱使用。
//
// 与 2D Car2D.vue 逐点同源（windowPath / pillarX）：
//   前风挡带  hoodEndX/beltLineY → windshieldTopX/roofTopY（A 柱线）
//   后风挡带  rearWindowBottomX/beltLineY → rearWindowTopX/roofTopY（C 柱线，皮卡无）
//   侧窗 DLO  windowPath 四点，顶部两角内收避开 G1 圆角
//   B 柱      windshieldTopX → dloTopRear 的 55% 分段（与 2D pillarX 同源）
//
// 坐标约定同 carProfile.js：X+ 指向车头，Y+ 竖直向上，地面 Y=0，单位米。

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
 * 两端再沿外法线抬离 offset（贴合被 bevel 外扩的车身侧壁）。
 * 法线统一朝上（ny ≥ 0，指向外表面），与下坡方向无关。
 * @returns {{ a: number[], b: number[], normal: number[] }} 抬升后的两端点与单位法线
 */
export function bandGlassEndpoints(x1, y1, x2, y2, topInset = 0, offset = 0) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  let tx2 = x2
  let ty2 = y2
  if (topInset > 0) {
    const t = Math.min(topInset / len, 0.9)
    tx2 -= dx * t
    ty2 -= dy * t
  }
  let nx = dy / len
  let ny = -dx / len
  if (ny < 0) { nx = -nx; ny = -ny }   // 法线统一朝上（外表面）
  return {
    a: [x1 + nx * offset, y1 + ny * offset],
    b: [tx2 + nx * offset, ty2 + ny * offset],
    normal: [nx, ny]
  }
}

/**
 * 由 deriveCarProfile 结果派生座舱玻璃面板布局（纯函数）。
 * @param {object} P deriveCarProfile 返回值
 * @param {object} [opts] 可选项：carType（车型，决定默认倾角/桶面）、
 *   sideGlassAngle（carParams.side_glass_angle 覆盖，非法值自动回退）、
 *   glassBarrelAngle（carParams.glass_barrel_angle 覆盖，0≤角≤20°）、
 *   glassBarrelRadius（carParams.glass_barrel_radius 覆盖，400≤半径≤5000mm）
 * @returns {{
 *   windshield: { x1, y1, x2, y2, width, topInset },
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

  return {
    // 前风挡：底缘 = COWL，顶缘 = 车顶前缘；顶缘下退 0.09m 留出车身色顶带
    windshield: {
      x1: hoodEndX, y1: beltLineY,
      x2: windshieldTopX, y2: roofTopY,
      width: W * 0.9, topInset: 0.09
    },
    // 后风挡：顶缘 = 车顶后缘，底缘 = 行李箱前缘
    rearWindow: pickup ? null : {
      x1: rearWindowBottomX, y1: beltLineY,
      x2: rearWindowTopX, y2: roofTopY,
      width: W * 0.88, topInset: 0.09
    },
    // 侧窗 DLO：与 2D windowPath 逐点同源，顶部两角内收避开 G1 圆角
    dlo: [
      [hoodEndX, beltLineY + 0.008],
      [windshieldTopX + 0.012, roofTopY - 0.035],
      [dloTopRear - 0.012, roofTopY - 0.035],
      [dloBotRear, beltLineY + 0.008]
    ],
    dloTopRear,
    dloBotRear,
    // B 柱：55% 分段处车身色立柱（叠于玻璃之上，与 2D B 柱线同位置）
    pillar: {
      x: windshieldTopX + (dloTopRear - windshieldTopX) * 0.55,
      topY: roofTopY - 0.05,
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
