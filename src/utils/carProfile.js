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

  return {
    // 尺寸（m）
    W, H, WB, track, gc, hoodLen, wheelDia, wheelR, halfTrack, FO, RO,
    // 锚点 X
    frontWheelX, rearWheelX, frontX, rearX,
    // 高度 Y
    bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY,
    // 侧围关键点
    hoodEndX, trunkLength, trunkStartX,
    windshieldHeight, windshieldTopX,
    slantFactor, roofLen,
    rearWindowTopX, rearWindowHeight, rearWindowBottomX,
    // 轮拱
    wheelArchRadius: wheelR + 0.05,
    archY: gc + wheelR,
    // 车型专属
    pickup, rails, wing
  }
}
