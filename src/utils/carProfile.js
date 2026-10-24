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

  // ---------- 11. 接近角 / 离去角（布置设计基准，2D/3D 同源，可按车型调节） ----------
  // 缺省 = 前（后）轮接地点与车身前（后）立面底角连线的最大坡度角 atan(gc/FO)、atan(gc/RO)；
  // 传入 approach_angle / departure_angle 则覆盖，驱动前后下部车身坡面几何（见 deriveEndRamps）。
  const defApproach = (Math.atan2(gc, FO) * 180) / Math.PI
  const defDeparture = (Math.atan2(gc, RO) * 180) / Math.PI
  const approachAngleDeg = num(p.approach_angle, defApproach)
  const departureAngleDeg = num(p.departure_angle, defDeparture)

  const P0 = {
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
    // 接近角 / 离去角（deg，布置设计基准，可被参数覆盖）
    approachAngleDeg, departureAngleDeg,
    defApproach, defDeparture,
    // 车型专属
    pickup, rails, wing
  }
  // 前后下部坡面（接近/离去角驱动的几何切角，默认角时退化为原始直角，零视觉变化）
  P0.ramps = deriveEndRamps(P0, approachAngleDeg, departureAngleDeg)
  return P0
}

/**
 * 接近角 / 离去角 → 前/后下部车身坡面切角（2D/3D 同源几何驱动）。
 * 坡面为「轮胎接地点 → 车身立面底角」的斜面：给定角度 θ，前（后）立面底角抬高到
 * cornerY = max(gc, FO·tanθ)，坡脚落在底线上 rampX = 立面 ∓ (cornerY-gc)/tanθ。
 * 默认 θ=atan(gc/FO) 时 cornerY=gc、rampX=立面 → 切角退化为原始直角（零回归）。
 * 钳位：cornerY 不超过机盖/甲板线，rampX 不侵入轮拱唇（保证轮廓不自交）。
 */
export function deriveEndRamps(P, approachDeg, departureDeg) {
  const RAD = Math.PI / 180
  const tA = Math.max(Math.tan(approachDeg * RAD), 1e-6)
  const tD = Math.max(Math.tan(departureDeg * RAD), 1e-6)
  // 前（X+ 车头）
  let cornerYf = Math.min(Math.max(P.bodyBottomY, tA * P.FO), P.hoodLineY - 0.02)
  let rampXf = P.frontX - (cornerYf - P.bodyBottomY) / tA
  rampXf = Math.min(Math.max(rampXf, P.frontWheelX + P.wheelArch.front.rx + 0.02), P.frontX)
  // 后（X- 车尾）
  let cornerYr = Math.min(Math.max(P.bodyBottomY, tD * P.RO), P.trunkLineY - 0.02)
  let rampXr = P.rearX + (cornerYr - P.bodyBottomY) / tD
  rampXr = Math.max(Math.min(rampXr, P.rearWheelX - P.wheelArch.rear.rx - 0.02), P.rearX)
  return { front: { cornerY: cornerYf, rampX: rampXf }, rear: { cornerY: cornerYr, rampX: rampXr } }
}

/**
 * 车顶区 G1 圆角集（2D 轮廓 / 3D 玻璃包裹的唯一真源）。
 * 常规车：front=风挡顶圆角、rear=车顶后缘圆角、cBase=C柱底圆角；
 * 皮卡：front=风挡顶、cabTop=驾驶室后壁顶、cabBase=驾驶室后壁底。
 * 返回 filletCorner 的 { a, ctrl, b }（路径 lineTo(a) → quadraticCurveTo(ctrl, b)），
 * 并附尾部锚点（tailCtrlX/tailCtrlY）供轮廓尾段与测试对照。
 */
export function roofFilletSet(P, carType, fillets) {
  const F = fillets || { aPillarTop: 0.09, roofRear: 0.09, cPillarBottom: 0.06, pickupCabTop: 0.05, pickupCabBottom: 0.03 }
  const {
    roofTopY, beltLineY, trunkLineY, hoodEndX, windshieldTopX,
    rearWindowTopX, rearWindowBottomX, rearX, pickup
  } = P
  const tailCtrlX = rearX + 0.02, tailCtrlY = trunkLineY - 0.016
  if (pickup) {
    const cabBotX = pickup.cabWindowBottomX
    return {
      front: filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, F.aPillarTop),
      cabTop: filletCorner(windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, cabBotX, pickup.bedWallY, F.pickupCabTop),
      cabBase: filletCorner(pickup.cabRearX, roofTopY, cabBotX, pickup.bedWallY, rearX - 0.024, pickup.bedWallY, F.pickupCabBottom),
      tailCtrlX, tailCtrlY
    }
  }
  return {
    front: filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, rearWindowTopX, roofTopY, F.aPillarTop),
    rear: filletCorner(windshieldTopX, roofTopY, rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, F.roofRear),
    cBase: filletCorner(rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, tailCtrlX, tailCtrlY, F.cPillarBottom),
    tailCtrlX, tailCtrlY
  }
}

/**
 * 侧围外轮廓命令序列（2D/3D 唯一真源，返回米制指令数组）。
 * 顶边：前脸→机盖→A柱顶/车顶后缘/C柱底三处 G1 圆角→尾部（沿用现锚点与 ROOF_FILLETS）。
 * 底边：自车尾向车头行进，绕前后轮拱各升起一个 notch（竖唇 + 半椭圆上缘 + 竖唇），
 *   使轮拱成为外轮廓真实边界（bevel 沿轮廓走，杜绝共线孔边的拱底残留薄片）；
 *   前后下角按 ramps（接近/离去角）切角，默认直角。
 * 指令类型：{k:'M'|'L',x,y}、{k:'Q',cx,cy,x,y}、{k:'A',cx,cy,rx,ry,a0,a1,cw}。
 * 消费方：Car3D 逐指令 moveTo/lineTo/quadraticCurveTo/absellipse 构建 Shape；
 *   Car2D 映射到 SVG（X 镜像换算）。carGlass 的 ROOF_FILLETS 由 fillets 参数注入避免循环依赖。
 */
export function bodySideOutline(P, carType, fillets, ramps = null) {
  const F = fillets || { aPillarTop: 0.09, roofRear: 0.09, cPillarBottom: 0.06, pickupCabTop: 0.05, pickupCabBottom: 0.03 }
  const {
    bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY,
    hoodEndX, cowlStartX, trunkStartX, windshieldTopX, rearWindowTopX, rearWindowBottomX,
    frontX, rearX, frontWheelX, rearWheelX, wheelArch, archY, pickup
  } = P
  const R = ramps || { front: { cornerY: bodyBottomY, rampX: frontX }, rear: { cornerY: bodyBottomY, rampX: rearX - 0.036 } }
  const tailEndY = trunkLineY - 0.056
  const cmd = []
  const M = (x, y) => cmd.push({ k: 'M', x, y })
  const L = (x, y) => cmd.push({ k: 'L', x, y })
  const Q = (cx, cy, x, y) => cmd.push({ k: 'Q', cx, cy, x, y })
  const A = (cx, cy, rx, ry, a0, a1, cw) => cmd.push({ k: 'A', cx, cy, rx, ry, a0, a1, cw })
  // 轮拱 notch（沿底边 +X 行进：后唇→上缘→前唇）
  const archNotch = (ax, a) => {
    L(ax - a.rx, bodyBottomY); L(ax - a.rx, archY)
    A(ax, archY, a.rx, a.ry, Math.PI, 0, true)
    L(ax + a.rx, bodyBottomY)
  }

  if (pickup) {
    const cabBotX = pickup.cabWindowBottomX
    const fs = roofFilletSet(P, carType, F)
    const f1 = fs.front, f2 = fs.cabTop, f3 = fs.cabBase
    M(R.front.rampX, bodyBottomY); L(frontX, R.front.cornerY)
    Q(frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
    L(cowlStartX, hoodLineY); L(hoodEndX, beltLineY)
    L(f1.a[0], f1.a[1]); Q(f1.ctrl[0], f1.ctrl[1], f1.b[0], f1.b[1])
    L(f2.a[0], f2.a[1]); Q(f2.ctrl[0], f2.ctrl[1], f2.b[0], f2.b[1])
    L(f3.a[0], f3.a[1]); Q(f3.ctrl[0], f3.ctrl[1], f3.b[0], f3.b[1])
    L(rearX - 0.024, pickup.bedWallY)
    Q(rearX, pickup.bedWallY - 0.008, rearX, pickup.bedWallY - 0.048)
    L(rearX, bodyBottomY + 0.026)
    Q(rearX, bodyBottomY, R.rear.rampX, R.rear.cornerY)
    L(R.rear.rampX, bodyBottomY)
    archNotch(rearWheelX, wheelArch.rear)
    archNotch(frontWheelX, wheelArch.front)
    L(R.front.rampX, bodyBottomY)
  } else {
    const fs = roofFilletSet(P, carType, F)
    const f1 = fs.front, f2 = fs.rear, f3 = fs.cBase
    const { tailCtrlX, tailCtrlY } = fs
    M(R.front.rampX, bodyBottomY); L(frontX, R.front.cornerY)
    Q(frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
    L(cowlStartX, hoodLineY); L(hoodEndX, beltLineY)
    L(f1.a[0], f1.a[1]); Q(f1.ctrl[0], f1.ctrl[1], f1.b[0], f1.b[1])
    L(f2.a[0], f2.a[1]); Q(f2.ctrl[0], f2.ctrl[1], f2.b[0], f2.b[1])
    L(f3.a[0], f3.a[1]); Q(f3.ctrl[0], f3.ctrl[1], f3.b[0], f3.b[1])
    Q(tailCtrlX, tailCtrlY, rearX, tailEndY)
    L(rearX, bodyBottomY + 0.026)
    Q(rearX, bodyBottomY, R.rear.rampX, R.rear.cornerY)
    L(R.rear.rampX, bodyBottomY)
    archNotch(rearWheelX, wheelArch.rear)
    archNotch(frontWheelX, wheelArch.front)
    L(R.front.rampX, bodyBottomY)
  }
  return cmd
}

/**
 * 车门分缝线 / B柱宽度 / 门把手布置（2D/3D 同源，米制）。
 * 缝位按实车包络规则推导：前门前沿贴前轮拱后唇、后门后沿贴后轮拱前唇，
 * B 柱按前门占门模块的比例（0.52）定位；把手高度按腰带线→底板的落差比例、
 * X 取门尾段（紧邻分缝）。默认值对应 B柱≈75mm、把手距腰带线≈50mm（实车区间内）。
 */
export function deriveDoorLayout(P, cabin, opts = {}) {
  const {
    bPillarWidthRatio = 0.16,   // × 座舱高：轿车 ≈75mm、SUV ≈91mm（实车 60~120mm）
    handleDropRatio = 0.10,     // 把手中线距腰带线：≈50mm（实车 30~70mm）
    handleXRatio = 0.15,        // 把手距门后沿占比（实车把手靠门尾、紧邻分缝）
    frontDoorShare = 0.52,      // 前门占「门模块」长度比（实车 0.5~0.55，B 柱略偏后）
    carType = null              // 车型：coupe/sport 为双门车（无后门缝，长前门）
  } = opts
  // 双门车（911/488 基准）：无后门与后门缝，单一长前门 + B 柱后固定三角窗；
  // B 柱占门模块 66%（实车双门车门长 1.1~1.3m，B 柱大幅后移）
  const twoDoor = carType === 'coupe' || carType === 'sport'
  // 门模块 = 前拱后唇 → 后拱前唇（两侧留 40mm 安全间隙，门板绝不覆盖轮腔开口）
  const frontBound = P.frontWheelX - P.wheelArch.front.rx - 0.04
  const rearBound = P.rearWheelX + P.wheelArch.rear.rx + 0.04
  // 真车分缝规则：前门前沿贴前轮拱后唇；后门后沿贴后轮拱前唇
  const frontSeamX = frontBound
  const midSeamX = P.pickup
    ? rearBound                                              // 单排皮卡：门尾 = 驾驶室后壁
    : twoDoor
      ? frontSeamX - 0.66 * (frontSeamX - rearBound)         // 双门：B 柱后移，长前门
      : frontSeamX - frontDoorShare * (frontSeamX - rearBound) // B 柱：前门占门模块 52%
  const rearSeamX = (P.pickup || twoDoor) ? null : rearBound
  const bWidth = bPillarWidthRatio * (P.roofTopY - P.beltLineY)
  const handleY = P.beltLineY - handleDropRatio * (P.roofTopY - P.beltLineY)  // 距腰带线，按座舱高比例
  // 把手布置：位于各门尾段（前后门分别紧邻 B 柱 / C 柱侧分缝）
  const frontHandleX = midSeamX + handleXRatio * (frontSeamX - midSeamX)
  const rearHandleX = rearSeamX === null ? null : rearSeamX + handleXRatio * (midSeamX - rearSeamX)
  return { frontSeamX, midSeamX, rearSeamX, frontBound, rearBound, bWidth, handleY, frontHandleX, rearHandleX }
}

/**
 * 底盘上升装置布置（2D/3D 同源，6~8 个）。
 * 布置约束（真车工程口径）：
 *   1. 只能落在「底盘封闭段」——前后轮腔开口之间的实体地板区间；
 *   2. 分布以轴距中心为对称轴等距铺开（左右两列严格镜像，列间距一致），
 *      不再随前后悬差偏心——保证视觉与受力的均匀分布；
 *   3. 奇数个时在中线补一台；
 *   4. 装置外缘与地板边缘留 edgeInset，避免悬空在侧裙外侧。
 * 返回米制坐标；y 为装置安装面（略低于车身底面，形成下沉式风道口）。
 */
export function deriveLiftDevices(P, count = 6) {
  const n = Math.min(Math.max(Math.round(Number(count) || 6), 6), 8)
  const margin = 0.10
  const xMin = P.rearWheelX + P.wheelArch.rear.rx + margin     // 封闭段尾端（后拱前唇之后）
  const xMax = P.frontWheelX - P.wheelArch.front.rx - margin    // 封闭段首端（前拱后唇之前）
  const span = Math.max(xMax - xMin, 0.30)
  const r = Math.min(0.22, span * 0.14)
  const zOuter = Math.max(P.W / 2 - r - 0.10, r + 0.02)
  // 以封闭段中心为对称轴的均匀网格：列位置 = xMid ± (i+0.5)·step，
  // 左右两列严格镜像 z=±zOuter，列间距恒等 → 视觉与受力均匀分布。
  const xMid = (xMin + xMax) / 2
  const nPairs = Math.max(1, Math.floor(n / 2))   // 纵向列数（每列左右两台）
  const step = span / nPairs
  const devices = []
  for (let i = 0; i < nPairs; i++) {
    const off = (i + 0.5) * step - span / 2       // 中心对称：±step/2, ±3step/2 …
    const x = xMid + off
    devices.push({ x, z: zOuter, r, side: 'left' })
    devices.push({ x, z: -zOuter, r, side: 'right' })
  }
  if (n % 2 === 1) devices.push({ x: xMid, z: 0, r, side: 'center' })
  return {
    count: n,
    devices,
    r,
    xMin,
    xMax,
    y: P.bodyBottomY - 0.012   // 风道口略低于底面（下沉式，不形成额外最低点）
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
  return { wall, tireW, wheelZ, tireOuter: wheelZ + tireW / 2 }
}

/**
 * 轮腔内衬轮廓（绝对坐标 [x,y] 折线，2D/3D 同源）：与 archHole 拱口同形——
 * 半椭圆上缘（拱心 archY，半轴 rx/ry）+ 两侧竖直唇落至车身底板 bodyBottomY。
 * 整体按 inset 内缩，保证内衬严格位于拱口空腔之内，杜绝圆形筒对椭圆拱口的
 * 前后壁/顶部互穿（拓扑破面）。返回首尾均为底板端点，供拉伸成开壳。
 */
export function archLinerProfile(P, side = 'front', inset = 0.012, N = 16) {
  const a = P.wheelArch[side]
  const ax = side === 'front' ? P.frontWheelX : P.rearWheelX
  const rx = a.rx - inset
  const ry = a.ry - inset
  const yBot = P.bodyBottomY - P.archY   // 竖直唇底（相对拱心 archY，负值）
  const pts = [[-rx, yBot], [-rx, 0]]
  for (let i = 1; i < N; i++) {
    const t = Math.PI - (Math.PI * i) / N
    pts.push([rx * Math.cos(t), ry * Math.sin(t)])
  }
  pts.push([rx, 0], [rx, yBot])
  return pts.map(([x, y]) => [ax + x, P.archY + y])
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
