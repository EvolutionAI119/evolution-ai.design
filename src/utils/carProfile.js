// 参数化车型侧围轮廓推导（纯函数，无 Three.js 依赖，可单测）
//
// 坐标约定（全局唯一，禁止混用）：
//   X+ 指向车头，X- 指向车尾；Y+ 竖直向上；地面 Y=0；单位均为「米」
//   输入原始参数为毫米（与 carPresets.js 一致），在本模块内统一换算为米
//
// 关键物理约束（对所有车型生效，违反即钳制）：
//   1. 前风挡顶端必须落在发动机舱端点之后
//   2. 车顶后缘必须位于后围/甲板起点之前，保留至少 0.15m 余量
//   3. 后窗下缘不得越过甲板起点（trunkStartX）→ 杜绝窗角突出车身形成「悬浮」
//   4. 皮卡为专属拓扑：短驾驶室 + 开放货箱，车顶不允许贯通
//
// 高度分层比例（LINE_RATIOS）为 2D/3D 共享唯一来源：
//   语义 = 该特征线「离地高度 / 整车高度 H」（行业侧视图惯例，官方参数可直接对照）
//   校准基准：sedan≈E级 / suv≈Cayenne / coupe≈911 / sport≈488 / mpv≈V级 / pickup≈F-150
export const LINE_RATIOS = {
  sedan:  { hood: 0.62, belt: 0.68, trunk: 0.60 },
  suv:    { hood: 0.64, belt: 0.68, trunk: 0.62 },
  coupe:  { hood: 0.60, belt: 0.66, trunk: 0.60 },
  sport:  { hood: 0.62, belt: 0.66, trunk: 0.62 },
  mpv:    { hood: 0.56, belt: 0.66, trunk: 0.62 },
  pickup: { hood: 0.62, belt: 0.66, bed: 0.58 }
}

// 轮拱开口包络车型表（校准基准与 LINE_RATIOS 同源，2D/3D 唯一来源）：
//   jounce   悬架上跳行程 mm（拱顶必须让开跳动后的轮胎顶）
//   gapTop   拱顶设计间隙 mm（sport 紧致 ≈488 / suv·pickup 越野余量 ≈Cayenne·F-150）
//   gapSide  拱侧设计间隙 mm（后轴 ×0.8 收紧——无转向扫掠）
//   steerDeg 前轮最大转向角（满舵侧视扫掠外扩 c_steer = 胎宽/2 · sin δ）
//   flatten  扁拱系数（横轴放大 1+0.5·flatten：0=圆拱，suv/pickup 方拱风格）
export const WHEEL_ENVELOPE = {
  sedan:  { jounce: 45, gapTop: 35, gapSide: 25, steerDeg: 33, flatten: 0.00 },
  suv:    { jounce: 80, gapTop: 60, gapSide: 40, steerDeg: 34, flatten: 0.25 },
  coupe:  { jounce: 35, gapTop: 30, gapSide: 22, steerDeg: 32, flatten: 0.00 },
  sport:  { jounce: 30, gapTop: 25, gapSide: 18, steerDeg: 30, flatten: 0.00 },
  mpv:    { jounce: 45, gapTop: 35, gapSide: 25, steerDeg: 32, flatten: 0.05 },
  pickup: { jounce: 90, gapTop: 75, gapSide: 50, steerDeg: 34, flatten: 0.35 }
}

/**
 * 轮拱开口包络椭圆（真实轮拱几何：开口处处避开「满舵转向 + 悬架跳动」轮胎包络）。
 *
 * 轮胎模型：半径 r、胎宽 ≈0.36·轮径 的圆柱；绕轮心竖轴转 δ 后侧视 X 向外扩
 *   c_steer = (胎宽/2)·sin(δ)；悬架压缩 Δj → 轮心上跳 Δj。
 * 开口 = 以静置轮心 (ax, r) 为心的椭圆（接地轮心，绝对高度 r）：
 *   ry = r + Δj + gapTop                     （拱顶 = 轮顶 + 跳动 + 顶隙）
 *   rx = (r + c_steer + gapSide) / √(1-(Δj/ry)²) · (1+0.5·flatten)
 *   √ 项 = 跳动膨胀补偿：跳动轮心高度处拱口仍须保持全宽（该处包络最宽）
 * 后轴无转向：rx_r 以 0.8·gapSide 收紧。开口两端以竖直拱唇落入裙边（真实翼子板拱唇）。
 * 钳位：拱顶不得越过腰带线下 40mm。
 */
function deriveWheelArch(wheelR, gc, beltLineY, carType) {
  const env = WHEEL_ENVELOPE[carType] || WHEEL_ENVELOPE.sedan
  const tireW = wheelR * 2 * 0.36
  const cSteer = (tireW / 2) * Math.sin((env.steerDeg * Math.PI) / 180)
  const j = env.jounce / 1000, gt = env.gapTop / 1000, gs = env.gapSide / 1000
  const cy = wheelR
  let ry = wheelR + j + gt
  // 拱顶钳位：≤ 腰带线 - 40mm（保护门/玻璃锚点与特征线契约）
  ry = Math.min(ry, Math.max(beltLineY - 0.04 - cy, wheelR * 0.04))
  const denom = Math.sqrt(Math.max(1 - (j / ry) ** 2, 0.25))
  const grow = 1 + 0.5 * env.flatten
  const rxOf = (side) => ((wheelR + cSteer * side + gs * side) / denom) * grow
  const chordOf = (rx) => rx * Math.sqrt(Math.max(1 - ((cy - gc) / ry) ** 2, 0))
  return {
    cy, ry, flatten: env.flatten,
    style: env.flatten >= 0.15 ? 'square' : 'round',
    front: { rx: rxOf(1), ry, chord: chordOf(rxOf(1)) },
    rear:  { rx: rxOf(0.8), ry, chord: chordOf(rxOf(0.8)) }
  }
}
export function deriveCarProfile(rawParams, carType = 'sedan') {
  const p = rawParams || {}
  const num = (v, d) => (Number.isFinite(+v) ? +v : d)

  // ---------- 1. 参数读取（mm → m） ----------
  const W = num(p.overall_width, 1880) / 1000
  const H = num(p.overall_height, 1460) / 1000
  const WB = num(p.wheelbase ?? p.wheel_base, 2890) / 1000
  const track = num(p.track_width, 1600) / 1000
  const gc = num(p.ground_clearance, 140) / 1000
  const hoodLen = num(p.hood_length, 1050) / 1000
  const wheelDia = num(p.wheel_diameter, 680) / 1000
  const wAngleDeg = num(p.windshield_angle, 35)
  const rAngleDeg = num(p.rear_window_angle, 28)
  const rSlantDeg = num(p.rear_slant_angle, 18)
  const FO = num(p.front_overhang, 950) / 1000
  const RO = num(p.rear_overhang, 1110) / 1000

  const wheelR = wheelDia / 2
  const halfTrack = track / 2

  // ---------- 2. 锚点：车轮与车身外轮廓 X ----------
  const frontWheelX = WB / 2
  const rearWheelX = -WB / 2
  const frontX = frontWheelX + FO
  const rearX = rearWheelX - RO

  // ---------- 3. 高度（m，自地面起） ----------
  // 官方语义：overall_height = 离地总高（含离地间隙），车顶 Y = H；
  // 特征线离地高度 = H × LINE_RATIOS（与 2D Car2D.vue 同源，禁止再加 bodyBottomY）
  const bodyBottomY = gc
  const roofTopY = H
  const lineRatios = LINE_RATIOS[carType] || LINE_RATIOS.sedan
  const beltLineY = H * lineRatios.belt
  const hoodLineY = H * lineRatios.hood
  const trunkLineY = H * (lineRatios.trunk ?? lineRatios.bed ?? 0.60)

  // ---------- 4. 发动机舱与后甲板 X 锚点 ----------
  const hoodEndX = frontX - hoodLen
  const trunkLength = Math.min(RO * 0.6, hoodLen * 0.5)
  const trunkStartX = rearX + trunkLength

  // ---------- 4.5 Cowl 斜坡（2D/3D 共享）：机盖面在风挡底之前上升至腰带线 ----------
  const cowlRise = beltLineY - hoodLineY                      // 引擎盖→腰带的升高量（正值）
  const cowlRun = Math.min(0.14, Math.max(cowlRise * 0.9, 0.02))
  const cowlStartX = Math.min(hoodEndX + cowlRun, frontX - 0.03)

  // ---------- 5. 前风挡（锚点：hoodEnd → 车顶） ----------
  const wAngle = (wAngleDeg * Math.PI) / 180
  const windshieldHeight = roofTopY - beltLineY
  const windshieldTopX = hoodEndX - windshieldHeight / Math.tan(wAngle)

  // ---------- 6. 车顶长度 + 约束 2 ----------
  const slantFactor = Math.min(Math.max(rSlantDeg / 60, 0), 1)
  const maxRoofLength = windshieldTopX - trunkStartX
  let roofLen = Math.max(maxRoofLength * (1 - slantFactor * 0.6), 0.15)
  roofLen = Math.min(roofLen, Math.max(maxRoofLength - 0.15, 0.15))

  // ---------- 7. 后窗 + 约束 3 ----------
  const rAngle = (rAngleDeg * Math.PI) / 180
  let rearWindowTopX = windshieldTopX - roofLen
  const rearWindowHeightRatio = 0.5 + slantFactor * 0.35
  const rearWindowHeight = (roofTopY - beltLineY) * rearWindowHeightRatio
  let rearWindowBottomX = Math.max(
    rearWindowTopX - rearWindowHeight / Math.tan(rAngle),
    trunkStartX
  )

  // ---------- 8. 皮卡专属拓扑（覆盖通用车顶/后窗推导） ----------
  let pickup = null
  if (carType === 'pickup') {
    // 货箱栏板上沿 = H × bed 比例（≈F-150 栏板高 1.09m，高于轮拱、低于腰带线）
    const bedWallY = H * (lineRatios.bed ?? 0.58)
    // 驾驶室后壁在后轮中心朝车头 0.5m（F-150：货箱前端位于后轴上方）；
    // 若轴距过小则向前收，保证货箱 ≥0.5m
    const cabRearX = Math.max(rearWheelX + 0.5, rearX + 0.38)
    const cabWindowBottomX = cabRearX + 0.12            // 驾驶室后窗下沿微向前收
    pickup = {
      bedWallY,
      cabRearX,
      cabWindowBottomX,
      bedFrontX: cabRearX + 0.18,
      bedRearX: rearX - 0.12,
      bedInteriorHalfZ: W / 2 - 0.16,
      wallTopRearX: rearX + 0.02
    }
    roofLen = windshieldTopX - cabRearX
    rearWindowTopX = cabRearX
    rearWindowBottomX = cabWindowBottomX
  }

  // ---------- 9. 车顶行李架（仅 SUV / MPV，沿车长方向、半嵌车顶） ----------
  let rails = null
  if (carType === 'suv' || carType === 'mpv') {
    const railFrontX = windshieldTopX - 0.08
    const railRearX = Math.min(rearWindowTopX + 0.08, railFrontX - 0.3)
    rails = {
      length: railFrontX - railRearX,
      xCenter: (railFrontX + railRearX) / 2,
      y: roofTopY - 0.008,
      z: halfTrack - 0.12
    }
  }

  // ---------- 10. GT 尾翼（仅 sport，支柱必须落在后甲板实体上） ----------
  let wing = null
  if (carType === 'sport') {
    wing = {
      span: W * 0.9,
      chord: 0.28,
      thickness: 0.045,
      x: trunkStartX + 0.05,
      y: trunkLineY + 0.3,
      strutZ: W * 0.28,
      deckY: trunkLineY + 0.04
    }
    wing.supportH = wing.y - wing.deckY
  }

  // 轮拱包络椭圆（依赖 beltLineY，返回值前派生）
  const wheelArch = deriveWheelArch(wheelR, gc, beltLineY, carType)

  // ---------- 11. 接近角 / 离去角（布置设计基准，2D/3D 同源） ----------
  // 定义：前（后）轮接地点与车身前（后）立面底角连线的最大坡度角。
  // 本模型前立面底角 = (frontX, gc)、后立面底角 = (rearX, gc)，
  // 接地点与立面底角水平距离恰为前悬 FO / 后悬 RO → tan = gc / FO、gc / RO。
  const approachAngleDeg = (Math.atan2(gc, FO) * 180) / Math.PI
  const departureAngleDeg = (Math.atan2(gc, RO) * 180) / Math.PI

  return {
    // 尺寸（m）
    W, H, WB, track, gc, hoodLen, wheelDia, wheelR, halfTrack, FO, RO,
    // 锚点 X
    frontWheelX, rearWheelX, frontX, rearX,
    // 高度 Y
    bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY,
    // 侧围关键点
    hoodEndX, cowlStartX, trunkLength, trunkStartX,
    windshieldHeight, windshieldTopX,
    slantFactor, roofLen,
    rearWindowTopX, rearWindowHeight, rearWindowBottomX,
    // 轮拱：转向+跳动包络椭圆（拱心=静置接地轮心；竖唇落裙边；见 deriveWheelArch）
    wheelArch,
    wheelArchRadius: wheelArch.front.rx, // 前拱开口半宽（兼容旧消费方）
    archY: wheelR,         // 兼容字段 = 轮心高度（历史值 gc+wheelR 为错位拱心，已修正）
    // 轮胎名义断面宽（与包络椭圆 c_steer 同源：0.36 × 轮径）
    tireWidth: wheelR * 2 * 0.36,
    // 接近角 / 离去角（deg，布置设计基准）
    approachAngleDeg, departureAngleDeg,
    // 车型专属
    pickup, rails, wing
  }
}

/**
 * 车轮装配配合（2D/3D 同源判据）：轮胎外侧面必须收进车身侧壁之内，
 * 杜绝侧视「轮胎压过拱唇/裙边」的干涉观感。bodyThickness 与 Car3D 拉伸 bevel 一致。
 */
export function deriveWheelFitment(P, bodyThickness = 0.03, margin = 0.02) {
  const wall = (P.W + bodyThickness * 2) / 2          // 车身侧壁外表面（含 bevel 外扩）
  const tireW = P.tireWidth
  const wheelZ = wall - tireW / 2 - margin            // 轮心 Z：胎外侧面藏于侧壁内 margin
  return { wall, tireW, wheelZ, tireOuter: wheelZ + tireW / 2, linerR: Math.max(P.wheelArch.front.rx, P.wheelArch.front.ry) + 0.015 }
}

/**
 * 角点圆角（G1 切线连续）：在角点 P 处，沿 PA / PB 两段各取距 P 为 r 的切点，
 * 返回 { a, ctrl, b } —— 路径 lineTo(a) → quadraticCurveTo(ctrl=P, b)。
 * 切线连续性由构造保证：曲线 t=0 端方向 = a→P = 原直线方向；t=1 端方向 = P→b = 原直线方向。
 * 短段保护：r 超过段长 45% 时钳位，切点不越过段中点，杜绝回折。
 */
export function filletCorner(ax, ay, px, py, bx, by, r) {
  const dAP = Math.hypot(px - ax, py - ay)
  const dPB = Math.hypot(bx - px, by - py)
  const safe = (d) => (d > 1e-9 ? d : 1e-9)
  const t = Math.min(r / safe(dAP), 0.45)
  const u = Math.min(r / safe(dPB), 0.45)
  return {
    a: [px + (ax - px) * t, py + (ay - py) * t],
    ctrl: [px, py],
    b: [px + (bx - px) * u, py + (by - py) * u]
  }
}
