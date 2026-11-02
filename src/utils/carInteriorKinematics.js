// 内饰运动件运动学模型（R-04 整改：调角器 / 遮阳板 / 扶手盖全行程扫掠）
//
// 与 carInteriorLayout 同一坐标系：X+ 车头、Y+ 向上、地面 Y=0，单位米。
// 设计原则：
//   1. 参数与实车物理参数一致（调角器行程 ±rad、遮阳板展长/翻转 180°、扶手盖 75° 开启）；
//   2. 运动轨迹按真实铰链逻辑：调角器绕 H 点、遮阳板绕顶棚前缘铰链、扶手盖绕中控台后端铰链；
//   3. 扫掠输出「逐角最小间隙 + 最大安全角」，调角器超行程时自动求限位角（与实车限位逻辑一致）。

import {
  INTERIOR_GEOM, cabinRearBound, deriveInteriorLayout, deriveInteriorTrim, deriveIpConsoleLayout,
  seatBackLean, seatSideEnvelope
} from './carInteriorLayout.js'

/** 运动件物理参数（实车对标值，禁止消费端另立） */
export const KINEMATICS_PARAMS = {
  // 调角器：绕 H 点旋转，前倒 ≈5.7° / 后倒 ≈11.5°（实车调角器典型行程）
  reclinerFwd: INTERIOR_GEOM.reclinerFwdRange,
  reclinerAft: INTERIOR_GEOM.reclinerAftRange,
  reclinerStep: 0.01,
  // 遮阳板：展长 190mm（实车 180~200），铰链直径余量 35mm，翻转 0（贴顶棚收纳）→ π（过竖直贴合风挡）
  sunVisorLength: 0.19,
  sunVisorPivotDrop: 0.035,
  sunVisorFlipMax: Math.PI,
  sunVisorStep: Math.PI / 36,
  // 扶手盖：有效盖长 ≤320mm（实车扶手盖 280~340），开启 0（关闭）→ 1.31rad（75°）
  armrestLidMaxLength: 0.32,
  armrestLidOpenMax: 1.31,
  armrestLidStep: 0.05,
  margin: INTERIOR_GEOM.seatTravelMargin
}

/** 点到线段最短距离（风挡玻璃干涉判定用） */
const distToSegment = (px, py, ax, ay, bx, by) => {
  const dx = bx - ax, dy = by - ay
  const len2 = dx * dx + dy * dy
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / len2))
  const cx = ax + t * dx, cy = ay + t * dy
  return Math.hypot(px - cx, py - cy)
}

/**
 * 调角器扫掠：靠背绕 H 点在 [design − fwd, design + aft] 内逐角旋转。
 * 障碍：前排 → B 柱前缘；中间排 → 下一排坐垫前缘；末排 → 座舱后界（后围板/行李舱隔板）。
 * 前排按实车限位器标定逻辑取「滑轨最后端」 worst case（滑轨后移 = 整个靠背随座后移）。
 * 输出最大安全后倒角（实车调角器限位角）：间隙首次跌破 margin 前的最后一个安全角。
 */
export const deriveReclinerSweep = (P) => {
  const G = INTERIOR_GEOM
  const K = KINEMATICS_PARAMS
  const L = deriveInteriorLayout(P)
  const design = seatBackLean(P)
  const rearBound = cabinRearBound(P)
  const results = []

  for (let i = 0; i < L.rows.length; i++) {
    const row = L.rows[i]
    const next = L.rows[i + 1] ?? null
    // 前排限位器按滑轨最后端标定（实车限位角为机械定值，必须覆盖最恶劣工况）
    const aftShift = i === 0 ? (L.travel?.aft ?? 0) : 0
    // 障碍面 X（X+ 朝车头，障碍均在靠背之后）：前排 B 柱前缘 / 下一排坐垫前缘 / 座舱后界
    const obstacleX = i === 0
      ? L.apertures.bPillarX1
      : (next ? next.x + G.cushionDepth - G.cushionFrontOffset : rearBound)
    // 障碍函数：给定倾角，返回该排靠背最后缘 → 障碍面的净间隙
    const gapAt = (lean) => {
      const env = seatSideEnvelope(row.x, row.hPointY, G, lean)
      const backRearX = Math.min(...env.backrest.points.map((p) => p[0])) - aftShift
      return backRearX - obstacleX
    }
    // 最不利倾角处的靠背后缘点（干涉点坐标）与干涉量
    const backRearAt = (lean) => {
      const env = seatSideEnvelope(row.x, row.hPointY, G, lean)
      const all = env.backrest.points.map((p) => ({ x: p[0] - aftShift, y: p[1] }))
      return all.reduce((a, b) => (b.x < a.x ? b : a))
    }
    const lo = design - K.reclinerFwd
    const hi = design + K.reclinerAft
    let minGap = Infinity
    let worstLean = design
    for (let a = lo; a <= hi + 1e-9; a += K.reclinerStep) {
      const g = gapAt(a)
      if (g < minGap) { minGap = g; worstLean = a }
    }
    // 最大安全后倒角（限位角）：自设计角向后步进，止于间隙跌破 margin 之前
    let maxSafeAft = design
    for (let a = design; a <= hi + 1e-9; a += K.reclinerStep) {
      if (gapAt(a) >= K.margin) maxSafeAft = a
      else break
    }
    const worstPt = backRearAt(worstLean)
    results.push({
      row: row.row,
      obstacle: i === 0 ? 'B 柱前缘' : (next ? `第 ${next.row} 排坐垫前缘` : '座舱后界（后围板/行李舱隔板）'),
      obstacleX,
      aftShift,
      design,
      fwdLimit: lo,
      aftLimitMax: hi,
      minGap,
      worstLean,
      // 干涉点（全行程最不利时刻的靠背后缘点）与干涉量：负间隙即有穿透
      interference: minGap < -1e-9
        ? { depth: -minGap, point: worstPt, obstacleX, parts: ['前排/该排靠背蒙皮', i === 0 ? 'B 柱' : (next ? `第 ${next.row} 排坐垫` : '后围板')] }
        : null,
      maxSafeAft,
      gapAtMaxSafe: gapAt(maxSafeAft),
      limited: maxSafeAft < hi - 1e-9,
      pass: maxSafeAft >= design - 1e-9 && gapAt(design) >= K.margin - 1e-9
    })
  }
  return results
}

/**
 * 遮阳板翻转扫掠：铰链在顶棚前缘下方 35mm，板体展长 190mm，自「贴顶棚收纳」(θ=0) 向前翻转。
 * 实车逻辑：板尖触及风挡玻璃面即被玻璃挡住（接触角 contactTheta），其后行程物理不可达——
 * 因此有效行程 = [0, contactTheta]，而非无条件扫到 π。
 * 干涉判定：① 全程板尖不得穿透顶棚内表面；② 有效行程内板尖不得越到玻璃外侧；
 *           ③ contactTheta ≥ π/2（遮阳板至少能翻到竖直，否则不具备遮阳功能）。
 */
export const deriveSunVisorSweep = (P) => {
  const K = KINEMATICS_PARAMS
  const T = deriveInteriorTrim(P)
  const pivotX = T.headliner.x1 - 0.03
  const pivotY = T.headliner.y0 - K.sunVisorPivotDrop
  // 风挡玻璃线段：底部（机盖端点、腰带线）→ 顶部（windshieldTopX、车顶）
  const glassA = { x: P.hoodEndX ?? P.frontX, y: P.beltLineY }
  const glassB = { x: P.windshieldTopX ?? P.roofTopY, y: P.roofTopY }
  // 风挡面法向（舱内一侧）：风挡自下向上往车尾倾斜，舱内侧为「风挡线的左下侧」
  const glassSide = (px, py) => {
    const dx = glassB.x - glassA.x, dy = glassB.y - glassA.y
    // 叉积 > 0 → 点在线的左侧（舱内一侧）
    return dx * (py - glassA.y) - dy * (px - glassA.x)
  }

  let minHeadlinerGap = Infinity
  let minGlassDist = Infinity      // 有效行程 [0, contactTheta] 内的最小玻璃距离
  let worstTheta = 0
  let headlinerPenetration = false
  let contactTheta = K.sunVisorFlipMax
  let contactFound = false
  for (let th = 0; th <= K.sunVisorFlipMax + 1e-9; th += K.sunVisorStep) {
    const tipX = pivotX - K.sunVisorLength * Math.cos(th)
    const tipY = pivotY - K.sunVisorLength * Math.sin(th)
    const gH = T.headliner.y0 - tipY              // 板尖不得高于顶棚内表面
    if (gH < minHeadlinerGap) minHeadlinerGap = gH
    if (gH < -1e-9) headlinerPenetration = true
    if (contactFound) continue                    // 接触玻璃后的行程物理不可达，不再统计
    if (glassSide(tipX, tipY) < -1e-9) {
      // 本步首次越到玻璃外侧：上一格为最后可达角
      contactTheta = Math.max(0, th - K.sunVisorStep)
      contactFound = true
    } else {
      const gG = distToSegment(tipX, tipY, glassA.x, glassA.y, glassB.x, glassB.y)
      if (gG < minGlassDist) { minGlassDist = gG; worstTheta = th }
    }
  }
  return {
    pivot: { x: pivotX, y: pivotY },
    length: K.sunVisorLength,
    flipMax: K.sunVisorFlipMax,
    contactTheta,                    // 板尖触玻璃的有效翻转上限（实车玻璃即限位）
    contactFound,
    contactPoint: {
      x: pivotX - K.sunVisorLength * Math.cos(contactTheta),
      y: pivotY - K.sunVisorLength * Math.sin(contactTheta)
    },
    minHeadlinerGap,
    minGlassDist,
    worstTheta,
    penetration: headlinerPenetration,
    // 干涉点：板尖穿透顶棚内表面时给出坐标与干涉量（玻璃接触属设计限位，不计干涉）
    interference: headlinerPenetration
      ? {
          depth: -minHeadlinerGap,
          point: { x: pivotX - K.sunVisorLength * Math.cos(worstTheta), y: pivotY - K.sunVisorLength * Math.sin(worstTheta) },
          parts: ['遮阳板板体', '顶棚内衬']
        }
      : null,
    pass: !headlinerPenetration && contactTheta >= Math.PI / 2 && minGlassDist >= -0.002
  }
}

/**
 * 扶手盖开合扫掠：铰链在中控台后端顶面，盖长按实车 ≤320mm，
 * 自关闭（φ=0，平躺在中控顶面）开启到 75°。
 * 干涉判定：① Z 向与前排座椅错层（盖体 |z| ≤ 通道半宽，座椅内缘之外）；
 *           ② 开启全程盖尖不得进入仪表台 AABB；③ 不得撞顶棚（物理上不可能，作兜底断言）。
 */
export const deriveArmrestLidSweep = (P) => {
  const K = KINEMATICS_PARAMS
  const L = deriveInteriorLayout(P)
  const T = deriveInteriorTrim(P)
  const C = deriveIpConsoleLayout(P)
  const hinge = { x: L.console.rearX, y: L.console.topY }
  // 盖长取交付模型的实际扶手盖（deriveIpConsoleLayout.armrestLid），上限仍受实车 320mm 约束
  const lidLen = Math.min(K.armrestLidMaxLength,
    C?.armrestLid ? C.armrestLid.x1 - C.armrestLid.x0 : (L.console.frontX - L.console.rearX) * 0.6)
  // Z 向错层间隙：盖体随通道（|z| ≤ tunnel.halfZ），座椅内缘在其外
  const seatInner = Math.min(...L.rows[0].seat.centers.map((z) => Math.abs(z))) - L.rows[0].seat.width / 2
  const zClearance = seatInner - T.tunnel.halfZ

  let minIpGap = Infinity
  let minRoofGap = Infinity
  let worstPhi = 0
  for (let phi = 0; phi <= K.armrestLidOpenMax + 1e-9; phi += K.armrestLidStep) {
    const tipX = hinge.x + lidLen * Math.cos(phi)
    const tipY = hinge.y + lidLen * Math.sin(phi)
    // 盖尖 → 仪表台 AABB（[ip.rearX, ip.frontX] × [ip.bottomY, ip.topY]）的间隙
    const inX = tipX >= L.ip.rearX && tipX <= L.ip.frontX
    const inY = tipY >= L.ip.bottomY && tipY <= L.ip.topY
    const gIp = (inX && inY)
      ? -Math.min(tipX - L.ip.rearX, L.ip.frontX - tipX, tipY - L.ip.bottomY, L.ip.topY - tipY)
      : Math.min(
          Math.max(L.ip.rearX - tipX, 0) + Math.max(tipX - L.ip.frontX, 0),
          Math.max(L.ip.bottomY - tipY, 0) + Math.max(tipY - L.ip.topY, 0)
        ) || Math.hypot(
          Math.max(L.ip.rearX - tipX, 0, tipX - L.ip.frontX),
          Math.max(L.ip.bottomY - tipY, 0, tipY - L.ip.topY)
        )
    const gRoof = T.headliner.y0 - tipY
    if (gIp < minIpGap) { minIpGap = gIp; worstPhi = phi }
    if (gRoof < minRoofGap) minRoofGap = gRoof
  }
  return {
    hinge,
    lidLen,
    openMax: K.armrestLidOpenMax,
    zClearance,
    minIpGap,
    minRoofGap,
    worstPhi,
    // 干涉点：盖尖在最不利角度的坐标 + 干涉量（间隙为负时即穿透仪表台/顶棚）
    interference: minIpGap < -1e-9
      ? {
          depth: -minIpGap,
          point: { x: hinge.x + lidLen * Math.cos(worstPhi), y: hinge.y + lidLen * Math.sin(worstPhi) },
          parts: ['中央扶手盖蒙皮', '仪表台 IP 本体']
        }
      : null,
    pass: zClearance >= 0 && minIpGap >= 0 && minRoofGap >= K.margin
  }
}

/** 三个运动件全行程扫掠汇总（验收/整改报告取数口） */
export const deriveKinematics = (P) => ({
  recliner: deriveReclinerSweep(P),
  sunVisor: deriveSunVisorSweep(P),
  armrestLid: deriveArmrestLidSweep(P)
})
