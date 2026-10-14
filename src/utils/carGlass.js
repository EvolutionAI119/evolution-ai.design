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
 * @param {object} [opts] 可选项：carType（车型，决定默认倾角）、
 *   sideGlassAngle（carParams.side_glass_angle 显式覆盖，非法值自动回退）
 * @returns {{
 *   windshield: { x1, y1, x2, y2, width, topInset },
 *   rearWindow: { x1, y1, x2, y2, width, topInset } | null,  // 皮卡为 null（驾驶室后壁为车身）
 *   dlo: number[][],            // 侧窗四边形 [底前, 顶前, 顶后, 底后]
 *   dloTopRear: number,
 *   dloBotRear: number,
 *   pillar: { x, topY, botY },  // B 柱（车身色）中心线与上下端
 *   tiltDeg: number,            // 侧玻璃倾角（度，B 柱与侧窗共面同角）
 *   dloTopInsetZ: number        // DLO 顶边相对底边的 Z 向内收量（米，正值=向内）
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
  const dloTopY = roofTopY - 0.035
  const dloBotY = beltLineY + 0.008
  const dloTopInsetZ = (dloTopY - dloBotY) * Math.tan((tiltDeg * Math.PI) / 180)

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
    dloTopInsetZ
  }
}

/**
 * DLO 倾斜面在高度 y 处的 Z 坐标（tumblehome 线性内收）。
 * 底边（y = dloYBot）位于 dloZBase，顶边（y = dloYBot + dloYSpan）内收 dloTopInsetZ，
 * 超出 [dloYBot, dloYBot + dloYSpan] 的高度按边界钳位（不外扩）。
 * zSide=1 为左片（+Z），zSide=-1 为右片镜像。
 * @param {number} y 目标高度
 * @param {{ dloYBot: number, dloYSpan: number, dloTopInsetZ: number, dloZBase: number }} f DLO 框架参数
 * @param {1|-1} zSide 侧别
 * @returns {number} 该高度的 Z 坐标（带侧别符号）
 */
export function dloZAt(y, f, zSide) {
  const span = f.dloYSpan || 1
  const t = Math.min(Math.max((y - f.dloYBot) / span, 0), 1)
  return zSide * (f.dloZBase - t * f.dloTopInsetZ)
}

/**
 * B 柱定位与姿态（与侧窗 DLO 共面同倾角）。
 * 底部锚定 DLO 面在 pillar.botY 高度处的 Z（与 dloZAt 同公式，保证共面），
 * 绕底旋转 tiltDeg（rotation.x = -zSide × tiltRad）。
 * @returns {{ x, botY, height, baseZ, tiltRad }} baseZ 为 zSide=1 时底部 |Z|
 */
export function pillarPlacement(cabin, dloYBot, dloYSpan, dloZBase) {
  const span = dloYSpan || 1
  const pillarT = (cabin.pillar.botY - dloYBot) / span
  return {
    x: cabin.pillar.x,
    botY: cabin.pillar.botY,
    height: cabin.pillar.topY - cabin.pillar.botY,
    baseZ: dloZBase - pillarT * cabin.dloTopInsetZ,
    tiltRad: (cabin.tiltDeg * Math.PI) / 180
  }
}
