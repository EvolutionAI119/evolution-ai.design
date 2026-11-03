// 人机工程验证模块（评审整改闭环：B-1/B-2/B-3/A-1/A-2）
//
// 三个独立验证器，全部消费单一真源（deriveInteriorLayout / deriveIpConsoleLayout / deriveInteriorTrim），
// 不另立座舱几何数值；人体/材料常数集中在 ERGO_ANTHRO / MOUNT_SPEC，修改即复算。
//
// 1) deriveDisplayMountCheck   悬浮屏悬挑支架刚度校核（弯曲 + 偏载扭转 + 一阶固有频率）
// 2) deriveClusterOcclusion    SAE J941 眼椭圆遮罩分析（侧视 2D：眼椭圆 → 轮缘/轮毂遮罩 → 组合仪表可见率）
// 3) deriveHeadroomCheck       各排头部空间校核（5F/50M/95M 三体型 + 运动包络余量）

import { deriveInteriorLayout, deriveIpConsoleLayout, deriveInteriorTrim, INTERIOR_GEOM } from './carInteriorLayout.js'

/* ------------------------------ 人体与规范常数 ------------------------------ */
// 坐姿头高（H 点 → 头顶，含发量余量）：取自 GB/T 10000 成人坐姿数据回归（与 SAE J833 人体基准一致）
export const ERGO_ANTHRO = {
  female5: { label: '5th 百分位女性', headAboveH: 0.790 },
  male50: { label: '50th 百分位男性', headAboveH: 0.850 },
  male95: { label: '95th 百分位男性', headAboveH: 0.910 },
  motionMargin: 0.050,  // 头部运动包络余量（颠簸/侧倾/姿态调整，工程惯例 50mm）
  clearanceMin: 0.010   // 静态最小间隙（含运动余量后的判定线）
}

// SAE J941 眼椭圆（95th 百分位，座椅行程 >133mm，侧视 2D 简化）：
// 椭圆中心相对 H 点（ΔX 向后, ΔY 向上）与半轴长为标准表值，列为常数便于追溯复核。
export const EYELLIPSE_95 = {
  dx: -0.200,   // 中心在 H 点之后 200mm
  dy: 0.638,    // 中心在 H 点之上 638mm
  aX: 0.1032,   // X 向半轴（206.4mm 长轴）
  aY: 0.0466    // Y 向半轴（93.2mm 短轴）
}

/* ------------------------------ 1. 悬浮屏悬挑刚度 ------------------------------ */
// 整改方案规格（A-1 闭环）：单臂 80mm → 双臂对称（间距 160mm，单臂截面 30×8mm）
// 臂长 = 屏探出量（60mm，真源）；材料备选 PA66+GF50 / ADC12 压铸铝。
export const MOUNT_SPEC = {
  arms: 2,
  armSpacing: 0.16,          // 双臂 Z 向间距（屏宽 0.32 的 1/2，力矩臂最大化且不越出屏背）
  armSection: { b: 0.030, h: 0.008 }, // 截面宽×厚（m），弯曲绕弱轴为恶劣工况
  materials: {
    'PA66+GF50': { E: 11e9, density: 1610 },
    'ADC12': { E: 71e9, density: 2770 }
  },
  screenMass: 1.1,           // 12 英寸屏总成质量（kg，含支架前端件）
  pushForce: 100,            // 触控按压/误操作力（N，OEM 惯例上限）
  edgeForce: 30,             // 屏边缘单点偏载（N，偏航恶劣工况）
  deflectionMax: 0.0005,     // 屏端位移限值 0.5mm（触觉无感知阈值）
  yawDeflectionMax: 0.0010,  // 偏载下屏缘摆角位移限值 1.0mm
  naturalFreqMin: 50         // 一阶固有频率下限（Hz，高于怠速/路噪主激励带 20~40Hz）
}

/** 双臂支架刚度校核：纯力学校核模型（悬臂梁弯曲 δ=FL³/3EI、偏载力偶分配、端质量固有频率） */
export function deriveDisplayMountCheck(P) {
  const L = deriveInteriorLayout(P)
  const C = deriveIpConsoleLayout(P)
  if (!L || !C) return null
  const armLen = L.ip.rearX - C.display.x1   // 屏探出量（真源，当前 0.06m）
  const { b, h } = MOUNT_SPEC.armSection
  const I = (b * h ** 3) / 12
  const results = {}
  for (const [name, m] of Object.entries(MOUNT_SPEC.materials)) {
    const EI = m.E * I
    const kBend = (MOUNT_SPEC.arms * 3 * EI) / armLen ** 3          // 双臂并联弯曲刚度 N/m
    const deflection = MOUNT_SPEC.pushForce / kBend                  // 100N 按压屏端位移
    // 偏航：屏缘 30N 偏载 → 力偶 M=F·(屏宽/2)，由双臂差动弯曲抵抗，力臂 = 间距/2
    const torqueArm = C.display.z1 - C.display.z0
    const M = MOUNT_SPEC.edgeForce * (torqueArm / 2)
    const kArm = (3 * EI) / armLen ** 3
    const yaw = (M * (MOUNT_SPEC.armSpacing / 2)) / (2 * kArm * (MOUNT_SPEC.armSpacing / 2) ** 2 * (torqueArm / 2))
    const yawEdge = (M / (2 * kArm * (MOUNT_SPEC.armSpacing / 2)))   // 屏缘线位移
    void yaw
    // 一阶固有频率（端质量悬臂梁，双臂各承载一半屏质量）
    const fn = (1 / (2 * Math.PI)) * Math.sqrt((3 * EI) / ((MOUNT_SPEC.screenMass / 2) * armLen ** 3))
    results[name] = {
      armLen, I,
      deflectionMm: deflection * 1000,
      yawEdgeMm: yawEdge * 1000,
      naturalFreqHz: fn,
      pass: deflection <= MOUNT_SPEC.deflectionMax
        && yawEdge <= MOUNT_SPEC.yawDeflectionMax
        && fn >= MOUNT_SPEC.naturalFreqMin
    }
  }
  return results
}

/* ------------------------------ 2. SAE J941 眼椭圆遮罩分析 ------------------------------ */
/**
 * 侧视 2D 遮罩模型（ documented simplification ）：
 *  - 眼点：95th 眼椭圆边界 72 采样（EYELLIPSE_95）
 *  - 遮挡物：方向盘轮缘环（外半径 r、环宽 30mm）+ 轮毂（直径 64mm）在轮面 X 处的投影带；
 *    轮面倾角取真源 steerWheel.tiltDeg。穿过轮缘环开口的视线视为可见（符合实车「透过轮缘看仪表」）。
 *  - 目标：组合仪表竖向区间 21 采样（真源 cluster AABB）。
 * 输出：可见率 min/mean（全体眼点），以及最恶劣眼点位置。
 */
export function deriveClusterOcclusion(P) {
  const L = deriveInteriorLayout(P)
  const C = deriveIpConsoleLayout(P)
  if (!L || !C) return null
  const sw = L.steerWheel
  const cluster = C.cluster
  const row1 = L.rows[0]
  const tilt = (sw.tiltDeg * Math.PI) / 180
  const rOut = sw.r
  const rIn = sw.r - 0.030          // 轮缘环宽 30mm（实车典型 28~32mm）
  const hubHalf = 0.032             // 轮毂半径（真源 createSteeringWheel 0.032）
  const cosT = Math.cos(tilt)

  const eyeCx = row1.x + EYELLIPSE_95.dx
  const eyeCy = row1.hPointY + EYELLIPSE_95.dy
  const N = 72, M = 21
  let minVisible = 1
  let sumVisible = 0
  let worst = null
  for (let i = 0; i < N; i++) {
    const a = (i / N) * 2 * Math.PI
    const ex = eyeCx + EYELLIPSE_95.aX * Math.cos(a)
    const ey = eyeCy + EYELLIPSE_95.aY * Math.sin(a)
    let visible = 0
    for (let j = 0; j < M; j++) {
      const ty = cluster.y0 + ((cluster.y1 - cluster.y0) * j) / (M - 1)
      // 眼点 → 仪表采样点连线在轮面 x=sw.x 处的穿越高度
      const k = (sw.x - ex) / (cluster.x0 - ex)
      const yc = ey + (ty - ey) * k
      const dy = Math.abs(yc - sw.y)
      const inRim = dy <= rOut * cosT && dy >= rIn * cosT   // 轮缘环带（上/下两段）
      const inHub = dy <= hubHalf                           // 轮毂
      if (!inRim && !inHub) visible++
    }
    const ratio = visible / M
    sumVisible += ratio
    if (ratio < minVisible) {
      minVisible = ratio
      worst = { ex, ey }
    }
  }
  return {
    eyeCx, eyeCy,
    minVisibleRatio: minVisible,
    meanVisibleRatio: sumVisible / N,
    worstEye: worst,
    clusterY0: cluster.y0,
    clusterY1: cluster.y1
  }
}

/* ------------------------------ 3. 后排头部空间校核 ------------------------------ */
/**
 * 各排头部间隙 = 顶棚内衬下表面 −（排 H 点 + 坐姿头高）− 运动包络余量。
 * 头点纵向位置按靠背后倾角后移（真源 lean），顶棚取下表面（deriveInteriorTrim.headliner.y0）。
 * 输出三体型（5F/50M/95M）间隙；判定线 ERGO_ANTHRO.clearanceMin。
 */
export function deriveHeadroomCheck(P) {
  const L = deriveInteriorLayout(P)
  const T = deriveInteriorTrim(P)
  if (!L || !T) return null
  const linerY = T.headliner.y0
  return L.rows.map((row) => {
    const perType = {}
    for (const [key, a] of Object.entries(ERGO_ANTHRO)) {
      if (key === 'motionMargin' || key === 'clearanceMin') continue
      const clearance = linerY - (row.hPointY + a.headAboveH) - ERGO_ANTHRO.motionMargin
      perType[key] = { clearance, pass: clearance >= ERGO_ANTHRO.clearanceMin }
    }
    return { row: row.row, x: row.x, hPointY: row.hPointY, linerY, perType }
  })
}
