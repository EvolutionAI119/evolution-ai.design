// 内饰布置层（2D 侧视布置图与 3D 网格的唯一数据源）
//
// 为什么单独拆一层：2D 布置图与 3D 模型若各自推导坐标，必然产生漂移。
// 本模块把「几何常量 → 逐排定位 → 侧视包络 → 人机工程度量」全部收口，
// carInterior.js（3D）与 Car2D.vue（2D）都只消费它的输出，因此坐标天然一致。
//
// 坐标系与 carProfile 完全一致：X+ 车头、Y+ 向上、Z+ 副驾侧，地面 Y=0，单位米。
//
// 人机工程基准（SAE / 实车布置经验值，供 carInteriorLayout.spec.js 直接断言）：
//   H 点离地：轿车 0.52 / SUV 0.64 / MPV 0.68（见 carProfile.SEAT_LAYOUT）
//   坐垫面到地板   0.22 ~ 0.34 m（地板由车身底板 + 结构厚度推导，不直接取车身底板）
//   H 点 → 仪表板面 0.48 m（前排腿部操作空间，含 40mm 膝部余量）
//   方向盘中心 → H 点 0.52 m（水平），方向盘中心高出坐垫面 0.25 m
//   头枕顶 → 车顶 ≥ 0.05 m（头部余量）
//   座椅纵向基准：以前/后门洞为锚点（门洞位置与外观 deriveDoorLayout 同源），
//   而不是「方向盘后 520mm」——后者会让坐垫整个压在前门洞前缘，乘员无处落脚。

import { deriveDoorLayout } from './carProfile.js'

/** 内饰几何常量（2D 绘图与 3D 网格共用同一组数值，禁止在消费端另立数值） */
export const INTERIOR_GEOM = {
  // ---- 座椅单座（3D 网格 + 2D 侧视包络共用）----
  cushionDepth: 0.50,    // 坐垫进深
  cushionThick: 0.12,    // 坐垫厚度（自 H 点向下）
  backHeight: 0.56,      // 靠背高度（自 H 点向上）
  backThick: 0.13,       // 靠背厚度
  backLean: 0.18,        // 靠背后倾角（rad，正 = 顶部向车尾）
  headGap: 0.075,        // 头枕与靠背顶间隙
  headHeight: 0.19,      // 头枕侧视高度
  headThick: 0.10,       // 头枕侧视厚度
  headWidthRatio: 0.55,  // 头枕宽 / 单座宽（仅 3D 用）
  bolsterW: 0.07,        // 侧翼宽（仅 3D 用）
  bolsterExtraH: 0.05,   // 侧翼高出坐垫量（仅 3D 用）
  cushionFrontOffset: 0.06, // 坐垫前端相对 H 点的后缩量

  // ---- 座舱地板（由车身底板 + 结构厚度推导，且受坐垫面高度约束）----
  floorAboveBodyBottom: 0.10,     // 地板面高出车身底板（门槛/地板结构厚度）
  cushionAboveFloorMin: 0.22,     // 坐垫面到地板下限（低于此人会「蹲坐」）
  cushionAboveFloorMax: 0.34,     // 坐垫面到地板上限（高于此人大腿承托不足）

  // ---- 仪表台 IP ----
  ipDepth: 0.30,         // 仪表台最大进深
  ipMinDepth: 0.12,      // 仪表台最小进深（薄于此则无法容纳仪表/出风口）
  hipToDashFront: 0.48,  // 前排 H 点 → 仪表板面水平距离（含膝部余量）
  ipTopInset: 0.02,      // 仪表台上沿相对腰带线的内缩
  ipBottomAboveHPoint: 0.22, // 仪表台膝部护板下沿 = 坐垫面 + 该值
  ipRearToCowl: 0.03,    // 仪表台前缘相对发动机舱端点的内缩
  ipMinHeight: 0.16,     // 仪表台最小侧视高度

  // ---- 中控总成 CONSOLE ----
  consoleHeight: 0.30,   // 中控台扶手面距地板高度
  consoleFrontOverlap: 0.10, // 中控台前伸进入仪表台下方的量
  consoleRearGapToFrontSeat: 0.20, // 中控台后端相对前排 H 点的后缩（A-2 整改：0.30→0.20，释放扶手盖长度至 ≥0.20m，座垫前缘余量仍有 0.14m）
  consoleMinHeight: 0.15, // 中控台最小高度（低于此无法布置扶手/储物）
  consoleBelowHPoint: 0.04, // 扶手面低于坐垫面的量（保证驾驶员侧向肘部不顶撞）

  // ---- 门板 DOOR PANELS ----
  doorPanelBottomAboveFloor: 0.10,   // 门板下沿距地板高
  doorPanelArmrestBelowHPoint: 0.08, // 扶手面低于坐垫面（侧向肘部自然下垂高度）
  doorPanelTopAboveArmrest: 0.12,    // 门板示意带上沿高出扶手面

  // ---- 方向盘 ----
  steerWheelToHPoint: 0.52,   // 方向盘中心 → 前排 H 点（水平）
  steerWheelAboveHPoint: 0.25, // 方向盘中心高出坐垫面
  steerWheelRadius: 0.17,     // 方向盘半径（2D 圆 + 3D 圆环同值）
  steerWheelTiltDeg: 22,      // 轮面相对竖直面倾角（SAE 人机惯例：乘用车 20~25°，轮顶前倾、轮面朝向后上方对准驾驶员胸腹部）
  steerColumnLength: 0.22,    // 转向柱可见段长（轮毂 → IP 面）

  // ---- 横向（Z）布置：横断面（Z-Y 右视图）与 3D 座椅横向分布共用 ----
  bodyTrimThickness: 0.08,      // 门板内表面相对车身半宽的厚度（断面内壁位置）
  seatToWallClearance: 0.05,    // 座椅外缘 → 门内壁净距（肩肘不得贴死门板）
  seatMaxWidth: 0.56,           // 单座最大宽度（超过则肩部支撑冗余、通道变窄）
  seatMinWidth: 0.40,           // 独立双座最小宽度（低于此侧向支撑不足）
  consoleWidth: 0.20,           // 中控台宽度（前排双座之间）
  seatToConsoleClearance: 0.02, // 座椅内缘 → 中控台净距（小于此则膝盖/肘部顶撞）
  steerWheelFromTrack: 0.08,    // 方向盘中心相对半轮距的内缩（驾驶侧 Z-）

  // ---- 座椅纵向（X）布置基准：以门洞为锚点（门洞由外观 deriveDoorLayout 同源推导）----
  seatEntryClearance: 0.16,      // 前排坐垫前缘 → 前门洞前缘（上下车脚部通行余量）
  kneeClearanceMin: 0.03,        // 坐垫前缘 → 仪表板面最小膝部余量（短头车型的封顶依据）
  rearHPointFromRearSeam: 0.42,  // 后排 H 点 → 后门洞后缘（乘客处于后门洞中段）
  rearCushionGapToBPillar: 0.06, // 后排坐垫前缘 → B 柱后缘（后排膝部不顶柱）
  minRowPitch: 0.58,             // 相邻排 H 点最小间距（靠背厚 0.13 + 后排最小腿部空间 0.45）

  // ---- 座椅滑轨全行程安全约束（R-01~R-03 整改：行程由布置几何联动收窄，而非沿用车型表全量值）----
  seatTravelMargin: 0.01,          // 滑轨/调角器端点最小安全余量（端点处不得贴死障碍）

  // ---- 调角器行程（R-04 运动学模型参数，实车调角器典型范围）----
  reclinerFwdRange: 0.10,          // 前倒行程 rad（≈5.7°）
  reclinerAftRange: 0.20,          // 后倒行程 rad（≈11.5°）

  // ---- 剩余内饰件（门板内饰 / 中央通道 / 顶棚 / 地毯 / 安全带固定点）----
  doorTrimThickness: 0.03,       // 门板内饰厚度（内表面贴 halfInterior）
  doorTrimXInset: 0.02,          // 门板内饰相对门洞分缝的内缩（不压分缝）
  armrestDepthInward: 0.06,      // 扶手相对门内壁向舱内的凸出量
  armrestHalfLength: 0.15,       // 扶手沿 X 的半长
  armrestThickness: 0.08,        // 扶手上下厚度
  carpetThickness: 0.010,        // 地毯厚度（地板面之上）
  headlinerThickness: 0.020,     // 顶棚厚度（车顶内表面之下）
  headlinerZInset: 0.12,         // 顶棚半宽相对内壁的内缩（车顶侧倾收边，不得穿出侧窗）
  tunnelRearHeight: 0.10,        // 后排中央通道（连通前后）高出地板
  seatBeltAnchorInset: 0.055,    // 安全带上固定点相对门内壁的内缩
  seatBeltUpperAboveBelt: 0.06,   // 安全带上固定点高出腰带线

  // ---- IP/CONSOLE 功能模块（细化设计：全部模块由 deriveInteriorLayout 的 ip/console/steerWheel 锚点派生）----
  ipClusterW: 0.26,          // 组合仪表宽（Z 向，方向盘正前方）
  ipClusterH: 0.13,          // 组合仪表高（上沿贴 IP 顶）
  ipDisplayW: 0.32,          // 中控显示屏宽（Z 向，座舱中线）
  ipDisplayH: 0.18,          // 中控显示屏高
  ipVentW: 0.12,             // 出风口宽
  ipVentH: 0.06,             // 出风口高
  ipGloveboxW: 0.44,         // 手套箱宽（副驾侧 IP 下部）
  ipGloveboxH: 0.20,         // 手套箱高
  shifterW: 0.10,            // 换挡模块占位（X 向）
  shifterH: 0.09,            // 换挡模块高（高出中控扶手面）
  cupDiameter: 0.075,        // 杯托直径（双杯 Z 向并排，沉台设计）
  wirelessPadW: 0.16,        // 无线充电板宽（Z 向，中控台最前段斜面托盘）
  wirelessPadD: 0.075,       // 无线充电板进深（X 向）
  armrestLidMaxLen: 0.32,    // 中控扶手盖长（与运动学扫掠 K.armrestLidMaxLength 同源上限）

  // ---- 行李舱内饰（前行李舱 frunk / 后行李舱 / 皮卡货箱衬里）----
  luggageWallT: 0.02,        // 舱壁衬板厚度（PP 蜂窝板）
  luggageFloorAbove: 0.12,   // 行李舱地板高出车身底板下限
  luggageSideInset: 0.10,    // 侧围衬板外缘相对车内壁的内缩
  trunkTopInset: 0.05,       // 舱顶内衬相对甲板线/车顶的下沉
  luggageLampAbove: 0.35,    // 舱内照明灯中心距地板高度（右侧壁 LED）
  luggageHookAbove: 0.02,    // 系留锚钩距地板高度（地板四角）
  cargoNetAnchorAbove: 0.35, // 储物网锚点距地板高度（侧壁）
  luggageUnderfloorDepth: 0.15, // 地板下储物井深度（随车工具/补胎套件）
  wagonArchClearance: 0.04   // 旅行式货舱轮拱饰盒与轮胎包络的间隙
}

/**
 * 靠背后倾角（rad，正 = 顶部向车尾）：驾驶坐姿按车型定位取值。
 * 轿车/SUV ≈19~20°、双门轿跑 ≈18°、跑车 ≈17°、MPV/皮卡 ≈21°（均落在 SAE 舒适区间）。
 * 具体车型的姿态全部由此表解析，2D 包络与 3D 靠背枢轴共用同一数值（禁止各取一份）。
 */
export const SEAT_BACK_LEAN_BY_TYPE = {
  sedan: 0.36,
  suv: 0.34,
  coupe: 0.33,
  sport: 0.30,
  mpv: 0.38,
  pickup: 0.38
}

/** 解析某车型的靠背倾角（未登记车型回退基础常量） */
export const seatBackLean = (P) => SEAT_BACK_LEAN_BY_TYPE[P?.carType] ?? INTERIOR_GEOM.backLean

/** 绕 Z 轴旋转（与 Three.js rotation.z = lean 同一约定） */
const rotate = (px, py, lean) => [
  px * Math.cos(lean) - py * Math.sin(lean),
  px * Math.sin(lean) + py * Math.cos(lean)
]

/** 单座侧视包络：坐垫矩形 + 靠背四角 + 头枕四角（全部为 P 坐标系的绝对米值）
 *  lean 必须由 seatBackLean(P) 解析后传入，2D 与 3D 不得各取一份。 */
export const seatSideEnvelope = (x, hPointY, G = INTERIOR_GEOM, lean = G.backLean) => {
  const cushionX0 = x - G.cushionFrontOffset
  const cushionX1 = cushionX0 + G.cushionDepth
  const cushionY0 = hPointY - G.cushionThick
  const cushionY1 = hPointY

  const backLocal = [
    [-G.backThick / 2, 0],
    [G.backThick / 2, 0],
    [G.backThick / 2, G.backHeight],
    [-G.backThick / 2, G.backHeight]
  ]
  const backPoints = backLocal.map(([px, py]) => {
    const [rx, ry] = rotate(px, py, lean)
    return [x + rx, hPointY + ry]
  })

  const headCy = G.backHeight + G.headGap + G.headHeight / 2
  const headLocal = [
    [-G.headThick / 2, headCy - G.headHeight / 2],
    [G.headThick / 2, headCy - G.headHeight / 2],
    [G.headThick / 2, headCy + G.headHeight / 2],
    [-G.headThick / 2, headCy + G.headHeight / 2]
  ]
  const headPoints = headLocal.map(([px, py]) => {
    const [rx, ry] = rotate(px, py, lean)
    return [x + rx, hPointY + ry]
  })

  return {
    cushion: { x0: cushionX0, x1: cushionX1, y0: cushionY0, y1: cushionY1 },
    backrest: { points: backPoints },
    headrest: { points: headPoints },
    topY: Math.max(...headPoints.map((p) => p[1]))
  }
}

/**
 * 单座宽与横向中心：按每排座数自适应车身内宽（2D 横断面与 3D 完全同一套算法）。
 *
 * 旧算法把双座按「内宽 × 0.44」摆开，两座之间只剩 ~0.13m，
 * 前排中控台（宽 0.20m）必然与座椅相撞——侧视图看不出，横断面一剖即暴露。
 * 新算法显式让出中控台宽度 + 净距，再在剩余槽位内居中，从几何上杜绝重叠。
 */
export const rowSeatLayout = (P, count) => {
  const G = INTERIOR_GEOM
  const halfBody = Math.max((P?.W ?? 1.88) / 2, 0.60)
  const halfInterior = Math.max(halfBody - G.bodyTrimThickness, 0.15)

  if (count >= 3) {
    // 整体长椅：三座连续贴合（不留虚伪缝），外缘统一留门内壁净距
    const outerZ = Math.max(halfInterior - G.seatToWallClearance, 0.30)
    const width = Math.min(G.seatMaxWidth, (outerZ * 2) / 3)
    return { width, centers: [-width, 0, width], halfBody, halfInterior }
  }

  // 独立双座：内侧让出「中控台半宽 + 净距」，外侧留门内壁净距，余量在槽位内居中
  const innerZ = G.consoleWidth / 2 + G.seatToConsoleClearance
  const outerZ = Math.max(halfInterior - G.seatToWallClearance, innerZ + G.seatMinWidth)
  const slot = outerZ - innerZ
  const width = Math.min(G.seatMaxWidth, slot)
  const center = innerZ + slot / 2
  return {
    width,
    centers: [-center, center],
    halfBody, halfInterior,
    consoleHalf: G.consoleWidth / 2
  }
}

/** 座舱后界（X）：任何一排都不得越出；导出供运动学模型作末排调角器障碍 */
export const cabinRearBound = (P) => (P.pickup
  ? Math.min(P.pickup.cabRearX - 0.10, P.rearX)
  : Math.max((P.rearWindowBottomX ?? P.trunkStartX) + 0.06, P.trunkStartX))

/**
 * 车门分缝与门洞（X 向）——与外观 deriveDoorLayout 同一真源，本函数只做几何组装。
 * 门洞 = 相邻分缝之间：前门洞 [midSeamX, frontSeamX]，后门洞 [rearSeamX, midSeamX]；
 * B 柱以分缝线为中心、宽 bWidth（内饰件与座椅的干涉判定都用这一组值）。
 */
export const deriveDoorAperturesX = (P) => {
  const dl = deriveDoorLayout(P, null, { carType: P?.carType })
  const bHalf = dl.bWidth / 2
  return {
    frontSeamX: dl.frontSeamX,
    midSeamX: dl.midSeamX,
    rearSeamX: dl.rearSeamX,
    bWidth: dl.bWidth,
    bPillarX0: dl.midSeamX - bHalf,
    bPillarX1: dl.midSeamX + bHalf,
    front: { x0: dl.midSeamX, x1: dl.frontSeamX },
    rear: dl.rearSeamX === null ? null : { x0: dl.rearSeamX, x1: dl.midSeamX },
    twoDoor: dl.rearSeamX === null
  }
}

/**
 * 前排 H 点 X —— 座椅纵向基准（核心修复）。
 * 锚点 = 前门洞前缘 − 坐垫纵向跨度 − 上下车通行余量：坐垫前缘不再压住门洞前缘，
 * 乘员上车时脚有落脚区，且整块坐垫落在前门洞范围内。
 * 封顶 = 「仪表台最小进深」下的膝部余量：短头车型（sport 中置）坐垫不得后退到顶膝。
 */
export const deriveFrontRowX = (P) => {
  const G = INTERIOR_GEOM
  const span = G.cushionDepth - G.cushionFrontOffset
  const apertureAnchor = deriveDoorAperturesX(P).frontSeamX - span - G.seatEntryClearance
  const ipFrontX = (P.hoodEndX ?? P.frontX) - G.ipRearToCowl
  const dashLimit = ipFrontX - G.ipMinDepth - span - G.kneeClearanceMin
  return Math.min(apertureAnchor, dashLimit)
}

/** 方向盘中心 X：由前排 H 点 + 设计手伸距离推导（方向盘装在仪表台上、向舱内凸出） */
export const steerWheelX = (P) => deriveFrontRowX(P) + INTERIOR_GEOM.steerWheelToHPoint

/**
 * 逐排 H 点 X（2D 布置图与 3D createSeatRow 的唯一取数口）。
 *   1 排：门洞锚点（见 deriveFrontRowX）
 *   2 排（四门车）：「后门洞后缘前 0.42m」与「B 柱后缘让 0.06m」取更靠前者，
 *                   保证后排乘客处于后门洞中段、坐垫不侵入 B 柱
 *   2 排（双门车）：无后门洞可锚，按 seatRowPitch 后移
 *   2 排（皮卡）：贴驾驶室后壁
 *   3 排及以后：按 pitch 递减，且不越过座舱后界、不与前一排互穿
 */
export const deriveRowPositions = (P) => {
  const G = INTERIOR_GEOM
  const A = deriveDoorAperturesX(P)
  const span = G.cushionDepth - G.cushionFrontOffset
  const totalRows = Math.max(1, Math.round(P?.seatRows ?? 1))
  const counts = Array.isArray(P?.seatRowCounts) ? P.seatRowCounts : [2, 0, 0]
  const pitch = Math.max(0.55, P.seatRowPitch ?? 0.78)
  const out = []

  for (let r = 1; r <= totalRows; r++) {
    const count = Math.max(0, Math.round(counts[r - 1] ?? 0))
    if (count === 0) {
      out.push({ row: r, count: 0, x: null, pitch })
      continue
    }
    let x
    if (r === 1) {
      x = deriveFrontRowX(P)
    } else if (P.pickup && r === 2) {
      x = P.pickup.cabRearX + 0.28
    } else if (r === 2 && A.rear) {
      x = Math.min(
        A.rear.x0 + G.rearHPointFromRearSeam,
        A.bPillarX0 - G.rearCushionGapToBPillar - span
      )
    } else {
      const prev = out[r - 2]?.x
      x = prev == null ? deriveFrontRowX(P) - (r - 1) * pitch : prev - pitch
    }
    if (r > 1) {
      const prev = out[r - 2]?.x
      if (prev != null) x = Math.min(x, prev - G.minRowPitch)
      x = Math.max(x, cabinRearBound(P) + 0.22)
    }
    out.push({ row: r, count, x, pitch })
  }
  return out
}

/**
 * 单排定位（2D 布置图与 3D createSeatRow 的唯一取数口）
 * X：见 deriveRowPositions；Y：第一排 seatHPointFront，其后 seatHPointRear（缺失时按前排兜底）
 */
export const deriveRowPlacement = (P, rowIndex) => {
  const totalRows = Math.max(1, Math.round(P?.seatRows ?? 1))
  if (rowIndex < 1 || rowIndex > totalRows) return null
  const pos = deriveRowPositions(P)[rowIndex - 1]
  if (!pos || pos.count === 0) return null

  const hPointY = rowIndex === 1
    ? (P.seatHPointFront ?? 0.32)
    : (P.seatHPointRear || P.seatHPointFront || 0.32)

  return { row: rowIndex, count: pos.count, x: pos.x, hPointY, pitch: pos.pitch, seat: rowSeatLayout(P, pos.count) }
}

/**
 * 座舱地板高度（m）：地板面 = 车身底板 + 结构厚度，并被「坐垫面到地板 0.22~0.34m」夹住。
 * 直接取 bodyBottomY 会把地板压到车底以下，导致中控台只有 2cm 高（历史缺陷）。
 */
export const deriveFloorY = (P, hPointFront) => {
  const G = INTERIOR_GEOM
  const base = (P.bodyBottomY ?? 0) + G.floorAboveBodyBottom
  const low = hPointFront - G.cushionAboveFloorMax
  const high = hPointFront - G.cushionAboveFloorMin
  return Math.min(high, Math.max(base, low))
}

/**
 * 完整内饰布置（2D 布置图与 3D 模型共用）。
 * 返回值全部为 P 坐标系绝对米值；人机工程度量随同输出，供检查清单直接断言。
 */
export function deriveInteriorLayout(P) {
  const G = INTERIOR_GEOM
  if (!P) return null
  const lean = seatBackLean(P)

  const rows = []
  const totalRows = Math.max(1, Math.round(P?.seatRows ?? 1))
  for (let r = 1; r <= totalRows; r++) {
    const p = deriveRowPlacement(P, r)
    if (!p) continue
    rows.push({ ...p, backLean: lean, envelope: seatSideEnvelope(p.x, p.hPointY, G, lean) })
  }
  if (!rows.length) return null
  const front = rows[0]

  const floorY = deriveFloorY(P, front.hPointY)

  // ---- 仪表台 IP：前缘贴发动机舱端点，后缘按「H 点 → 板面 0.48m」，
  //      再夹在 [最小进深, 最大进深] 之间（sport 等短头车型按最小进深收敛，不得压成薄片）----
  const cowlX = P.hoodEndX ?? P.frontX
  const ipFrontX = cowlX - G.ipRearToCowl
  const ipRearX = Math.max(
    ipFrontX - G.ipDepth,
    Math.min(front.x + G.hipToDashFront, ipFrontX - G.ipMinDepth)
  )
  const ipTopY = (P.beltLineY ?? P.H * 0.68) - G.ipTopInset
  const ipBottomY = Math.min(front.hPointY + G.ipBottomAboveHPoint, ipTopY - G.ipMinHeight)

  // ---- 中控总成 CONSOLE：自仪表台后缘前伸 100mm 起，向前排 H 点后方收尾 ----
  const consoleFrontX = ipRearX + G.consoleFrontOverlap
  const consoleRearX = Math.max(consoleFrontX - 0.50, front.x - G.consoleRearGapToFrontSeat) // 台面长上限 0.50（A-2 整改：0.40→0.50，扶手盖 ≥0.20m）
  const consoleTopY = Math.min(front.hPointY - G.consoleBelowHPoint, floorY + G.consoleHeight)
  const consoleBottomY = floorY

  // ---- 门板 DOOR PANELS：沿座舱段（仪表板前缘 → 最后一排后方）的扶手带 ----
  const cabinFrontX = (P.hoodEndX ?? P.frontX) - 0.08
  const cabinRearX = cabinRearBound(P)
  const armrestY = front.hPointY - G.doorPanelArmrestBelowHPoint
  const doorPanel = {
    x0: Math.max(cabinRearX, rows[rows.length - 1].x - 0.45),
    x1: Math.min(cabinFrontX, front.x + 0.60),
    y0: floorY + G.doorPanelBottomAboveFloor,
    y1: armrestY + G.doorPanelTopAboveArmrest,
    armrestY
  }

  // ---- 方向盘：与 3D 圆环同一锚点（X 同向、Y 同高、Z 同侧、半径同值）----
  const steerWheel = {
    x: steerWheelX(P),
    y: front.hPointY + G.steerWheelAboveHPoint,
    z: -(P.halfTrack ?? 0.80) + G.steerWheelFromTrack,
    r: G.steerWheelRadius,
    tiltDeg: G.steerWheelTiltDeg,
    columnLen: G.steerColumnLength
  }

  // ---- 人机工程 / 门洞匹配度量（检查清单直接断言这些值）----
  const apertures = deriveDoorAperturesX(P)
  const cushionSpan = G.cushionDepth - G.cushionFrontOffset
  const cushionFrontX = front.x + cushionSpan
  const headRoom = (P.roofTopY ?? P.H) - Math.max(...rows.map((r) => r.envelope.topY))
  const hipToDash = ipRearX - front.x
  const kneeClearance = ipRearX - cushionFrontX
  const legRoomRear = rows.length > 1 ? Math.abs(rows[0].x - rows[1].x) - G.backThick : null
  const cushionAboveFloor = front.hPointY - floorY
  const seatToRoof = (P.roofTopY ?? P.H) - front.hPointY
  // 上下车通行余量：前排坐垫前缘 → 前门洞前缘（乘员落脚区）
  const entryClearance = apertures.frontSeamX - cushionFrontX
  // 前排靠背后缘（含后倾）→ B 柱前缘：不得侵入 B 柱。
  // 只取靠背本体：头枕高出腰带线、位于 B 柱玻璃区之后（不同 Z 层，不会实体相交），
  // 纳入判定会把正常后倾误报为干涉。
  const backRearX = Math.min(...front.envelope.backrest.points.map((p) => p[0]))
  const bPillarGap = backRearX - apertures.bPillarX1
  // 后排坐垫前缘 → B 柱后缘：后排膝部不顶柱
  const rearCushionToBPillar = rows.length > 1 && apertures.rear
    ? apertures.bPillarX0 - (rows[1].x + cushionSpan)
    : null

  // ---- 滑轨有效行程（R-01~R-03 整改核心）----
  // 根因：车型表 seatTrackLength 是全量机械行程，门洞锚定后 H 点变化，
  //       全量行程端点会顶膝（coupe/sport）或侵入 B 柱（suv/sedan）。
  // 修复：前向行程由「膝部余量 − 端点安全余量」收窄，后向行程由「靠背↔B 柱 − 端点安全余量」收窄，
  //       有效行程 = 前向 + 后向，任何车型端点余量都 ≥ seatTravelMargin。
  const trackDesign = P.seatTrackLength ?? 0.24
  const trackHalf = trackDesign / 2
  const trackFwd = Math.max(0, Math.min(trackHalf, kneeClearance - G.seatTravelMargin))
  const trackAft = Math.max(0, Math.min(trackHalf, bPillarGap - G.seatTravelMargin))
  const travel = {
    design: trackDesign, half: trackHalf,
    fwd: trackFwd, aft: trackAft,
    effective: trackFwd + trackAft,
    margin: G.seatTravelMargin,
    limited: trackFwd + trackAft < trackDesign - 1e-9
  }

  return {
    floorY,
    rows,
    apertures,
    travel,
    ip: { frontX: ipFrontX, rearX: ipRearX, topY: ipTopY, bottomY: ipBottomY },
    console: { frontX: consoleFrontX, rearX: consoleRearX, topY: consoleTopY, bottomY: consoleBottomY },
    doorPanel,
    steerWheel,
    metrics: {
      floorY, headRoom, hipToDash, kneeClearance, legRoomRear,
      cushionAboveFloor, seatToRoof, backLean: lean,
      entryClearance, bPillarGap, rearCushionToBPillar,
      hPointToWheel: steerWheel.x - front.x,
      ipDepth: ipFrontX - ipRearX,
      ipHeight: ipTopY - ipBottomY,
      consoleHeight: consoleTopY - consoleBottomY
    }
  }
}

/** 滑轨有效行程取数口（2D/3D/检查报告统一消费，禁止各端另算） */
export const deriveSeatTrackTravel = (P) => deriveInteriorLayout(P)?.travel ?? null

/**
 * 横断面布置（Z-Y 平面）＝「右视图 / A-A 断面」。
 *
 * 为什么必须单独出一张：侧视（X-Y）把中控台投到前排坐垫的正后方，
 * 无论绘制顺序怎么调都会被坐垫遮挡——这是投影维度缺失，不是画法问题。
 * 断面沿 A-A（过前排 H 点）剖切：中控台夹在双座之间，横向净距才第一次可见、可测量。
 *
 * 单一真源约束：Y 值全部取自 deriveInteriorLayout（与侧视逐值同源），
 * Z 值全部取自 rowSeatLayout（与 3D 座椅分布逐值同源），本函数只做「选取 + 组装」，
 * 不引入任何新的宽度/高度公式。
 */
export function deriveSectionLayout(P) {
  const L = deriveInteriorLayout(P)
  if (!L || !P) return null
  const G = INTERIOR_GEOM

  const halfBody = Math.max((P.W ?? 1.88) / 2, 0.30)
  const halfInterior = Math.max(halfBody - G.bodyTrimThickness, 0.15)
  const consoleZ0 = -G.consoleWidth / 2
  const consoleZ1 = G.consoleWidth / 2

  const rows = L.rows.map((r) => ({
    row: r.row,
    x: r.x,
    hPointY: r.hPointY,
    seatWidth: r.seat.width,
    // 断面里每座只是一个 Z 区间：坐垫顶面 = H 点，靠背顶 = H 点 + 靠背高，头枕顶取侧视包络顶
    cushionY0: r.envelope.cushion.y0,
    cushionY1: r.envelope.cushion.y1,
    backTopY: r.hPointY + G.backHeight,
    headrestY0: r.hPointY + G.backHeight + G.headGap,
    headrestTopY: r.envelope.topY,
    headrestWidth: r.seat.width * G.headWidthRatio,
    seats: r.seat.centers.map((z) => ({
      z,
      z0: z - r.seat.width / 2,
      z1: z + r.seat.width / 2,
      isDriver: r.row === 1 && z < 0
    }))
  }))
  const front = rows[0]

  // 中控台两侧实时净距：前排每座内侧边缘到中控台边缘的最小值
  const gaps = []
  for (const s of front.seats) {
    if (s.z0 > consoleZ1) gaps.push(s.z0 - consoleZ1)
    else if (s.z1 < consoleZ0) gaps.push(consoleZ0 - s.z1)
  }
  const seatToConsoleGap = gaps.length ? Math.min(...gaps) : null
  const seatToTrimGap = halfInterior
    - Math.max(...front.seats.map((s) => Math.max(Math.abs(s.z0), Math.abs(s.z1))))
  const trim = deriveInteriorTrim(P)

  return {
    width: P.W,
    halfBody,
    halfInterior,
    floorY: L.floorY,
    bodyBottomY: P.bodyBottomY ?? 0,
    beltLineY: P.beltLineY ?? P.H * 0.68,
    roofTopY: P.roofTopY ?? P.H,
    headlinerY: trim.headliner.y0,
    carpetY: trim.carpet.y1,
    console: { z0: consoleZ0, z1: consoleZ1, topY: L.console.topY, bottomY: L.console.bottomY },
    door: {
      halfZ: halfInterior,
      bottomY: L.doorPanel.y0,
      armrestY: L.doorPanel.armrestY,
      armrestTopY: L.doorPanel.y1
    },
    steerWheel: { ...L.steerWheel },
    rows,
    metrics: {
      cabinWidth: halfInterior * 2,
      consoleWidth: G.consoleWidth,
      consoleHeight: L.metrics.consoleHeight,
      seatToConsoleGap,
      seatToTrimGap,
      headRoom: L.metrics.headRoom,
      seatWidth: front.seatWidth
    }
  }
}

/**
 * 剩余内饰件布置（门板内饰 / 中央通道 / 顶棚 / 地毯 / 安全带固定点）。
 *
 * 单一真源约束：全部锚点取自 deriveInteriorLayout 与 deriveDoorAperturesX，
 * 本函数不另立任何宽度/高度公式；2D 侧视图与 3D 网格都只消费这里的米值。
 * 所有部件都按「座舱内表面」布置（|Z| ≤ halfInterior），因此不会穿出车身。
 */
export function deriveInteriorTrim(P) {
  const L = deriveInteriorLayout(P)
  if (!L || !P) return null
  const G = INTERIOR_GEOM
  const A = L.apertures
  const halfBody = Math.max((P.W ?? 1.88) / 2, 0.30)
  const halfInterior = Math.max(halfBody - G.bodyTrimThickness, 0.15)
  const roofTopY = P.roofTopY ?? P.H
  const beltLineY = P.beltLineY ?? P.H * 0.68
  const floorY = L.floorY
  // 皮卡的座舱后界是驾驶室后壁（cabinRearBound 对皮卡取 min 是为了封住货箱，不能用作舱内边界）
  const cabinRearX = P.pickup ? P.pickup.cabRearX - 0.02 : cabinRearBound(P)
  const lastRow = L.rows[L.rows.length - 1]

  // 地毯：地板面之上，自座舱后壁铺到前围（仪表台前缘），前后排脚坑都覆盖
  const carpet = {
    x0: Math.min(cabinRearX + 0.02, lastRow.x - 0.45),
    x1: L.ip.frontX,
    y0: floorY,
    y1: floorY + G.carpetThickness,
    halfZ: halfInterior - 0.01
  }

  // 顶棚：车顶内表面之下，自风挡顶（车顶起点）到座舱后界（皮卡到驾驶室后壁）
  const headliner = {
    x0: P.pickup
      ? P.pickup.cabRearX - 0.02
      : Math.max((P.rearWindowTopX ?? P.rearWindowBottomX ?? cabinRearX) + 0.02, cabinRearX + 0.10),
    x1: (P.windshieldTopX ?? P.roofTopY) - 0.02,
    y0: roofTopY - G.headlinerThickness,
    y1: roofTopY - 0.004,
    halfZ: halfInterior - G.headlinerZInset
  }
  // x 方向规范化：短舱车型（sport）可能使 x0 > x1，按实际跨度取小值
  if (headliner.x0 >= headliner.x1) headliner.x0 = headliner.x1 - 0.30

  // 中央通道：前排中控台本体 + 向后连通后排的低通道（不侵入两侧座椅的 Z 区间）
  const tunnel = {
    halfZ: G.consoleWidth / 2,
    console: { x0: L.console.rearX, x1: L.console.frontX, y0: floorY, y1: L.console.topY },
    rear: {
      x0: Math.max(cabinRearX + 0.05, lastRow.x - 0.55),
      x1: L.console.rearX,
      y0: floorY,
      y1: floorY + G.tunnelRearHeight
    }
  }
  if (tunnel.rear.x0 > tunnel.rear.x1) tunnel.rear.x0 = tunnel.rear.x1

  // 门板内饰：沿每个门洞（前门 / 后门）两侧，从地板到腰带线，内表面贴 halfInterior
  const doors = []
  const armrests = []
  for (const side of [-1, 1]) {
    for (const [key, ap] of [['front', A.front], ['rear', A.rear]]) {
      if (!ap) continue
      doors.push({
        key,
        side,
        x0: ap.x0 + G.doorTrimXInset,
        x1: ap.x1 - G.doorTrimXInset,
        y0: Math.max(floorY + 0.02, L.doorPanel.y0),
        y1: beltLineY - 0.02,
        z0: side > 0 ? halfInterior - G.doorTrimThickness : -halfInterior,
        z1: side > 0 ? halfInterior : -(halfInterior - G.doorTrimThickness)
      })
      const mid = (ap.x0 + ap.x1) / 2
      armrests.push({
        key,
        side,
        x0: mid - G.armrestHalfLength,
        x1: mid + G.armrestHalfLength,
        y0: L.doorPanel.armrestY - G.armrestThickness / 2,
        y1: L.doorPanel.armrestY + G.armrestThickness / 2,
        z0: side > 0 ? halfInterior - G.armrestDepthInward : -halfInterior,
        z1: side > 0 ? halfInterior : -(halfInterior - G.armrestDepthInward)
      })
    }
  }

  // 安全带固定点：上固定点在 B 柱（前排）/ C 柱侧（后排），下固定点在地板侧、靠近门内壁
  const upperY = Math.min(beltLineY + G.seatBeltUpperAboveBelt, roofTopY - 0.12)
  const belts = []
  for (const row of L.rows) {
    const upperX = row.row === 1
      ? A.bPillarX1 + 0.005
      : (A.rear ? Math.min(A.rear.x0 + 0.06, row.x - 0.30) : row.x - 0.30)
    for (const side of [-1, 1]) {
      const z = side * (halfInterior - G.seatBeltAnchorInset)
      belts.push({ row: row.row, side, kind: 'upper', x: upperX, y: upperY, z })
      belts.push({ row: row.row, side, kind: 'lower', x: row.x - 0.10, y: floorY + 0.10, z })
    }
  }

  return {
    halfBody,
    halfInterior,
    floorY,
    roofTopY,
    beltLineY,
    cabinRearX,
    carpet,
    headliner,
    tunnel,
    doors,
    armrests,
    belts
  }
}

/* ============================== IP/CONSOLE 细化布置 ============================== */

/**
 * IP/CONSOLE 功能模块布置（组合仪表 / 中控屏 / 出风口×4 / 手套箱 / 膝部护板 / 副驾气囊盖板 /
 * 换挡模块 / 双杯托 / 扶手盖 / 无线充电托盘 / 后排风口）。
 *
 * 单一真源约束：全部锚点取自 deriveInteriorLayout 的 ip / console / steerWheel / floorY / rows，
 * 本函数只做模块级派生，不另立任何座舱基准数值。每个模块输出语义化 AABB（米，P 坐标系），
 * 3D 网格（createIpConsole）、设计文档标注图与人机验证（spec 断言）共用同一取数口。
 */
export function deriveIpConsoleLayout(P) {
  const L = deriveInteriorLayout(P)
  if (!L || !P) return null
  const G = INTERIOR_GEOM
  const { ip, console: con, steerWheel } = L
  const front = L.rows[0]
  const halfInterior = Math.max((P.W ?? 1.88) / 2 - G.bodyTrimThickness, 0.15)
  const mk = (x0, x1, y0, y1, z0, z1) => ({ x0, x1, y0, y1, z0, z1 })
  const face = ip.rearX   // IP 后面板（面向乘员），模块自此向舱内（X 减小方向）凸出

  // ---- IP 本体分件：上体（软质搪塑）/ 下体（硬质注塑），供材质规格与 3D 分层 ----
  const splitY = ip.bottomY + (ip.topY - ip.bottomY) * 0.55
  const shells = {
    upper: mk(face - 0.02, ip.frontX, splitY, ip.topY, -halfInterior, halfInterior),
    lower: mk(face - 0.02, ip.frontX, ip.bottomY, splitY, -halfInterior, halfInterior)
  }

  // ---- 驾驶信息区：组合仪表在方向盘正前方（驾驶侧 Z-），上沿贴 IP 顶 ----
  const cluster = mk(face - 0.04, face,
    ip.topY - 0.02 - G.ipClusterH, ip.topY - 0.02,
    steerWheel.z - G.ipClusterW / 2, steerWheel.z + G.ipClusterW / 2)

  // ---- 信息娱乐区：中控屏座舱中线，悬浮式安装（探出 IP 面 60mm，缩短手伸距、减轻视觉厚重感）----
  const display = mk(face - 0.10, face - 0.04,
    ip.topY - 0.02 - G.ipDisplayH, ip.topY - 0.02,
    -G.ipDisplayW / 2, G.ipDisplayW / 2)

  // ---- 空调出风区：中央风口×2 夹屏幕两侧，侧风口×2 贴近左右门内壁（除霜指向侧窗）----
  const ventY0 = display.y0 + 0.03
  const ventCenter = [1, -1].map((s) => {
    const zc = s * (G.ipDisplayW / 2 + 0.03 + G.ipVentW / 2)
    return mk(face - 0.03, face, ventY0, ventY0 + G.ipVentH, zc - G.ipVentW / 2, zc + G.ipVentW / 2)
  })
  const ventSide = [1, -1].map((s) => {
    const zc = s * (halfInterior - 0.10)
    return mk(face - 0.03, face, ventY0, ventY0 + G.ipVentH, zc - G.ipVentW / 2, zc + G.ipVentW / 2)
  })

  // ---- 副驾储物区：手套箱（副驾侧 IP 下部）+ 副驾气囊隐形盖板（IP 顶面，设计标注件）----
  // 高度自适配 IP 竖向带：低顶车型（sport/coupe）带高不足时自动收浅，不得越出 IP 下/上沿
  const gbZc = halfInterior * 0.55
  const gbY0 = ip.bottomY + 0.04
  const gbH = Math.max(0.08, Math.min(G.ipGloveboxH, ip.topY - 0.02 - gbY0 - 0.02))
  const glovebox = mk(face - 0.05, face,
    gbY0, gbY0 + gbH,
    gbZc - G.ipGloveboxW / 2, gbZc + G.ipGloveboxW / 2)
  const airbagDoor = mk(face - 0.20, face - 0.02,
    ip.topY - 0.015, ip.topY,
    gbZc - 0.15, gbZc + 0.15)

  // ---- 驾驶侧下部：膝部护板（含膝部气囊安装位）----
  const kneePanel = mk(face - 0.04, face,
    ip.bottomY, ip.bottomY + 0.16,
    steerWheel.z - 0.17, steerWheel.z + 0.17)

  // ---- 中控台面功能带（前→后：无线充托盘 → 换挡 → 双杯托 → 扶手盖，链长 ≤ 台面长）----
  const conLen = con.frontX - con.rearX
  const wirelessPad = mk(con.frontX - G.wirelessPadD, con.frontX,
    con.topY, con.topY + 0.012,
    -G.wirelessPadW / 2, G.wirelessPadW / 2)
  const shifterX1 = wirelessPad.x0 - 0.015
  const shifter = mk(shifterX1 - G.shifterW, shifterX1,
    con.topY, con.topY + G.shifterH, -0.045, 0.045)
  // 双杯托 Z 向并排沉台（宽 0.075×2+0.02 = 0.17 ≤ 台面 0.20），X 向只占一杯位
  const cupX1 = shifter.x0 - 0.015
  const cups = [1, -1].map((s) => mk(cupX1 - G.cupDiameter, cupX1,
    con.topY - 0.05, con.topY,
    s * 0.05 - G.cupDiameter / 2, s * 0.05 + G.cupDiameter / 2))
  // 扶手盖：占中控台后段剩余长度（铰链在 rearX 端，与运动学扫掠 deriveArmrestLidSweep 同一锚点）
  const lidX1 = cups[0].x0 - 0.015
  const lidLen = Math.min(G.armrestLidMaxLen, lidX1 - con.rearX)
  const armrestLid = mk(lidX1 - Math.max(lidLen, 0.10), lidX1,
    con.topY, con.topY + 0.03, -G.consoleWidth / 2, G.consoleWidth / 2)

  // ---- 后排舒适件：中控台尾端后排出风口（两排及以上车型）----
  const rearVent = L.rows.length > 1
    ? mk(con.rearX - 0.03, con.rearX, con.topY - 0.10, con.topY - 0.04, -0.07, 0.07)
    : null

  // ---- 人机工程度量（设计验证取数口，spec 直接断言）----
  const reachDisplay = Math.hypot(
    (display.x0 + display.x1) / 2 - front.x,
    (display.y0 + display.y1) / 2 - front.hPointY
  )
  const reachShifter = Math.hypot(
    (shifter.x0 + shifter.x1) / 2 - front.x,
    (shifter.y0 + shifter.y1) / 2 - front.hPointY
  )
  const metrics = {
    reachDisplay,                       // H 点 → 中控屏手伸距离（SAE 前排触及 ≤0.80m）
    reachShifter,                       // H 点 → 换挡模块手伸距离（≤0.55m）
    clusterAboveHPoint: (cluster.y0 + cluster.y1) / 2 - front.hPointY, // 组合仪表中心高出 H 点
    displayAboveHPoint: (display.y0 + display.y1) / 2 - front.hPointY,
    ipSplitY: splitY,                       // 上/下体分型线（软包下界）
    consoleModulesLength: wirelessPad.x1 - armrestLid.x0, // 功能带总长 ≤ 台面长
    consoleLength: conLen
  }

  return {
    shells, cluster, display,
    vents: { center: ventCenter, side: ventSide },
    glovebox, airbagDoor, kneePanel,
    wirelessPad, shifter, cups, armrestLid, rearVent,
    halfInterior, metrics
  }
}

/* ============================== 行李舱内饰布置 ============================== */

/**
 * 前/后行李舱开启状态内饰布置（舱壁衬板 / 地板 / 轮拱饰盒 / 门槛护板 / 地板下储物井 /
 * 系留锚钩×4 / 储物网锚点 / 舱内照明 / 锁扣与应急拉手）。
 *
 * 单一真源约束：X/Y 锚点全部取自 carProfile（frontX/rearX/hoodEndX/trunkStartX/
 * hoodLineY/trunkLineY/bodyBottomY/wheelArch/pickup）与 deriveInteriorLayout（末排靠背后缘），
 * 本函数只做舱体级派生。输出语义化 AABB（米），3D 网格 / 设计文档 / 容积与人机验证共用。
 */
export function deriveLuggageLayout(P) {
  const L = deriveInteriorLayout(P)
  if (!L || !P) return null
  const G = INTERIOR_GEOM
  const halfBody = Math.max((P.W ?? 1.88) / 2, 0.30)
  const halfInterior = Math.max(halfBody - G.bodyTrimThickness, 0.15)
  const wallT = G.luggageWallT
  const bodyBottom = P.bodyBottomY ?? 0.20
  const mk = (x0, x1, y0, y1, z0, z1) => ({ x0, x1, y0, y1, z0, z1 })
  const lastRow = L.rows[L.rows.length - 1]
  const lastBackRearX = Math.min(...lastRow.envelope.backrest.points.map((p) => p[0]))
  const halfZ = halfInterior - G.luggageSideInset

  // ---- 前行李舱（frunk）：前轴前方、机盖之下的储物井（避让前轮拱转向包络）----
  const fArchRx = P.wheelArch?.front?.rx ?? 0.35
  const frunkX0 = (P.frontWheelX ?? 0) + fArchRx + 0.05
  const frunkX1 = (P.frontX ?? 0) - 0.12
  const frunkFloorY = bodyBottom + G.luggageFloorAbove
  const frunkTopY = Math.min((P.hoodLineY ?? (P.H ?? 1.5) * 0.62) - G.trunkTopInset, frunkFloorY + 0.42)
  const frunkHalfZ = Math.max(0.20,
    Math.min(halfInterior - 0.14, (P.halfTrack ?? 0.80) - (P.tireWidth ?? 0.25) / 2 - 0.08))
  const frunk = (frunkX1 - frunkX0 >= 0.25 && frunkTopY - frunkFloorY >= 0.18) ? {
    x0: frunkX0, x1: frunkX1, floorY: frunkFloorY, topY: frunkTopY, halfZ: frunkHalfZ,
    length: frunkX1 - frunkX0, depth: frunkTopY - frunkFloorY,
    volumeL: Math.round((frunkX1 - frunkX0) * (frunkTopY - frunkFloorY) * 2 * frunkHalfZ * 0.82 * 1000),
    // 锁扣/拉手在舱口前缘中心（机盖锁）；照明在右侧壁；锚钩×2 在地板前部两角
    latch: { x: frunkX1 - 0.02, y: frunkTopY + 0.02, z: 0 },
    lamp: { x: (frunkX0 + frunkX1) / 2, y: frunkFloorY + G.luggageLampAbove, z: frunkHalfZ - wallT },
    hooks: [
      { x: frunkX0 + 0.12, y: frunkFloorY + G.luggageHookAbove, z: -frunkHalfZ * 0.7 },
      { x: frunkX0 + 0.12, y: frunkFloorY + G.luggageHookAbove, z: frunkHalfZ * 0.7 }
    ]
  } : null

  // ---- 后行李舱：三种拓扑（皮卡货箱 / 旅行式货舱 SUV·MPV / 封闭式行李舱 轿车系）----
  let cargoFloorY = Math.max(bodyBottom + G.luggageFloorAbove, lastRow.hPointY - 0.12)
  let rear
  if (P.pickup) {
    const b = P.pickup
    const floor = Math.max(bodyBottom + 0.15, b.bedWallY - 0.55)
    const halfBed = Math.max(b.bedInteriorHalfZ - wallT, 0.30)
    const x0 = b.bedRearX + 0.02
    const x1 = b.bedFrontX - 0.02
    rear = {
      type: 'pickup-bed',
      x0, x1, floorY: floor, topY: b.bedWallY - 0.02, halfZ: halfBed,
      length: x1 - x0,
      // 货箱为开放舱：衬里 = 地板 + 前壁 + 两侧壁 + 尾门内板；栏板顶为舱口
      aperture: { bottomY: floor, topY: b.bedWallY, halfZ: halfBed + wallT, x: x0 },
      widthBetweenArches: null,
      archBoxes: [],
      volumeL: Math.round((x1 - x0) * (b.bedWallY - 0.02 - floor) * 2 * halfBed * 0.92 * 1000)
    }
  } else {
    const wagon = P.carType === 'suv' || P.carType === 'mpv'
    const x0 = (P.rearX ?? 0) + 0.10
    const x1 = wagon ? lastBackRearX - 0.08 : (P.trunkStartX ?? x0 + 0.6) - 0.06
    const topY = wagon
      ? (P.roofTopY ?? P.H) - G.trunkTopInset
      : (P.trunkLineY ?? (P.H ?? 1.5) * 0.60) - G.trunkTopInset
    // 舱深下限 0.22m：浅于此时压低地板（不低于车身底板 +80mm）
    if (topY - cargoFloorY < 0.22) cargoFloorY = Math.max(bodyBottom + 0.08, topY - 0.22)
    // 旅行式货舱：后轮拱侵入侧壁 → 轮拱饰盒，并输出「拱间净宽」人机指标
    const archBoxes = []
    let widthBetweenArches = null
    if (wagon && P.rearWheelX != null && P.wheelArch?.rear) {
      const rx = P.wheelArch.rear.rx
      if (P.rearWheelX > x0 && P.rearWheelX < x1) {
        const archInner = Math.max(0.30,
          (P.halfTrack ?? 0.80) - (P.tireWidth ?? 0.25) / 2 - G.wagonArchClearance)
        const boxTop = Math.min(cargoFloorY + 0.35, topY - 0.10)
        for (const s of [1, -1]) {
          archBoxes.push(mk(P.rearWheelX - rx, P.rearWheelX + rx, cargoFloorY, boxTop,
            s > 0 ? archInner : -halfZ - wallT, s > 0 ? halfZ + wallT : -archInner))
        }
        widthBetweenArches = 2 * archInner
      }
    }
    // 容积口径：旅行式货舱按 VDA 惯例计至遮物帘/窗线（beltLine - 20mm），
    // 盖板以上空间只作净空标注、不计容积——避免把玻璃区算进行李容积造成系统性高估。
    const coverY = wagon ? Math.min(topY, (P.beltLineY ?? topY) - 0.02) : topY
    const baseVolume = (x1 - x0) * (coverY - cargoFloorY) * 2 * (halfZ + wallT)
    const archLoss = archBoxes.length
      ? archBoxes.reduce((v, b2) => v + (b2.x1 - b2.x0) * (Math.min(b2.y1, coverY) - b2.y0) * Math.abs(b2.z1 - b2.z0), 0)
      : 0
    rear = {
      type: wagon ? 'wagon' : 'trunk',
      x0, x1, floorY: cargoFloorY, topY, halfZ,
      length: x1 - x0,
      coverY,
      aperture: wagon
        ? { bottomY: cargoFloorY - 0.02, topY: (P.roofTopY ?? P.H) - 0.10, halfZ: halfInterior - 0.06, x: x0 }
        : { bottomY: cargoFloorY, topY: (P.trunkLineY ?? topY) - 0.04, halfZ: halfInterior - 0.06, x: x0 },
      widthBetweenArches,
      archBoxes,
      volumeL: Math.round(Math.max(baseVolume - archLoss, 0) * (wagon ? 0.85 : 0.80) * 1000)
    }
  }

  // ---- 通用部件（三拓扑共用：衬板 / 地板 / 门槛 / 锚点 / 照明 / 锁扣 / 地板下井）----
  const r = rear
  const common = {
    floorCarpet: mk(r.x0, r.x1, r.floorY - 0.012, r.floorY, -r.halfZ, r.halfZ),
    sideLiners: [1, -1].map((s) => mk(r.x0, r.x1, r.floorY, r.topY,
      s > 0 ? r.halfZ : -r.halfZ - wallT, s > 0 ? r.halfZ + wallT : -r.halfZ)),
    frontLiner: mk(r.x1, r.x1 + wallT, r.floorY, Math.min(r.topY, r.floorY + 0.60), -r.halfZ, r.halfZ),
    lidInner: mk(r.x0 - wallT - 0.02, r.x0 - 0.02, r.floorY, r.aperture.topY, -r.halfZ, r.halfZ),
    sillPlate: mk(r.x0 - 0.02, r.x0 + 0.14, r.floorY - 0.006, r.floorY + 0.006,
      -(r.aperture.halfZ), r.aperture.halfZ),
    hooks: [
      { x: r.x0 + 0.15, y: r.floorY + G.luggageHookAbove, z: -r.halfZ * 0.75 },
      { x: r.x0 + 0.15, y: r.floorY + G.luggageHookAbove, z: r.halfZ * 0.75 },
      { x: r.x1 - 0.15, y: r.floorY + G.luggageHookAbove, z: -r.halfZ * 0.75 },
      { x: r.x1 - 0.15, y: r.floorY + G.luggageHookAbove, z: r.halfZ * 0.75 }
    ],
    netAnchors: [1, -1].map((s) => ({
      x: (r.x0 + r.x1) / 2, y: r.floorY + G.cargoNetAnchorAbove, z: s * (r.halfZ - 0.02)
    })),
    lamp: { x: (r.x0 + r.x1) / 2, y: r.floorY + G.luggageLampAbove, z: r.halfZ - wallT },
    latch: { x: r.x0 + 0.02, y: r.aperture.bottomY + 0.10, z: 0 },
    releaseHandle: { x: r.x0 + 0.02, y: r.aperture.bottomY + 0.10, z: 0.10 },
    // 地板下储物井：地板与车身底板之间净高 ≥0.20m 才开设
    underfloorWell: (r.floorY - bodyBottom >= 0.20)
      ? mk(r.x0 + 0.15, r.x1 - 0.15,
          Math.max(bodyBottom + 0.02, r.floorY - G.luggageUnderfloorDepth - 0.012), r.floorY - 0.012,
          -(r.halfZ - 0.05), r.halfZ - 0.05)
      : null
  }

  return {
    frunk,
    rear: { ...rear, ...common },
    meta: {
      type: rear.type,
      loadingHeight: rear.floorY,           // 装载门槛离地高（人机核心指标）
      loadingLength: rear.length,
      aperture: rear.aperture,
      widthBetweenArches: rear.widthBetweenArches,
      volumeL: rear.volumeL,
      frunkVolumeL: frunk?.volumeL ?? null
    }
  }
}
