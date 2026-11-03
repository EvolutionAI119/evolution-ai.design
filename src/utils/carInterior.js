// 内饰件参数化生成（纯 Three.js 几何，无外部资源）
//
// 坐标约定与 carProfile.js 完全一致（禁止混用）：
//   X+ 指向车头，Y+ 竖直向上，地面 Y=0，单位「米」；Z 为车宽方向，Z+ = 副驾侧 / Z- = 驾驶侧
//   输入 P 为 deriveCarProfile() 的返回值（已含 seatRows / seatRowCounts / seatHPoint* 等座椅布局）
//
// 渲染约束（与 INTERIOR_PARTS_RENDERING_PLAN.md 一致）：
//   无 UV、纯参数化 PBR 材质；内饰件 castShadow=false（不投外观阴影）/ receiveShadow=true /
//   renderOrder=2（车身外壳之后、玻璃透明件之前）。所有几何与材质均无贴图，dispose 走常规遍历。

import * as THREE from 'three'
import { INTERIOR_GEOM as G, deriveInteriorLayout, deriveRowPlacement, rowSeatLayout, seatBackLean, deriveInteriorTrim, deriveIpConsoleLayout, deriveLuggageLayout } from './carInteriorLayout.js'

/** 座椅材质预设（对应 INTERIOR_DESIGN_UNIFORMITY_STANDARD.md §2.3 的预设 ID）
 *  surface = 座椅主体（坐垫/靠背骨架面），bolster = 侧翼与头枕包覆；
 *  颜色取深色内饰系，避免与车身漆色冲突。 */
export const SEAT_MATERIAL_PRESETS = {
  standard: {
    surface: { color: 0x262a30, roughness: 0.90, metalness: 0.00 },
    bolster: { color: 0x1a1d21, roughness: 0.62, metalness: 0.02 }
  },
  luxury: {
    surface: { color: 0x4a3524, roughness: 0.50, metalness: 0.05 },
    bolster: { color: 0x2e2218, roughness: 0.45, metalness: 0.08 }
  },
  sport: {
    surface: { color: 0x1c1e22, roughness: 0.95, metalness: 0.00 },
    bolster: { color: 0x101214, roughness: 0.85, metalness: 0.05 }
  },
  executive: {
    surface: { color: 0x35302b, roughness: 0.55, metalness: 0.03 },
    bolster: { color: 0x24211d, roughness: 0.50, metalness: 0.10 }
  }
}

// 单座几何常量（m）——与 2D 布置图共用 carInteriorLayout.INTERIOR_GEOM，禁止在此另立数值
const CUSHION_DEPTH = G.cushionDepth
const CUSHION_THICK = G.cushionThick
const BACK_HEIGHT = G.backHeight
const BACK_THICK = G.backThick
const HEAD_GAP = G.headGap
const HEAD_HEIGHT = G.headHeight
const HEAD_THICK = G.headThick
const HEAD_WIDTH_RATIO = G.headWidthRatio
const BOLSTER_W = G.bolsterW
const BOLSTER_EXTRA_H = G.bolsterExtraH

/** 车型 → 默认座椅材质预设（品牌车型可通过 carParams.interior.material_preset 覆盖） */
export const SEAT_PRESET_BY_CAR_TYPE = {
  sedan: 'executive',
  suv: 'standard',
  coupe: 'sport',
  sport: 'sport',
  mpv: 'executive',
  pickup: 'standard'
}

/** 解析座椅材质预设：车型参数显式指定优先，否则按车型表兜底 */
export const resolveSeatPreset = (carType, carParams) => {
  const explicit = carParams?.interior?.material_preset
  if (SEAT_MATERIAL_PRESETS[explicit]) return explicit
  return SEAT_PRESET_BY_CAR_TYPE[carType] || 'standard'
}

/**
 * 侧视圆角矩形沿 Z 挤出（坐垫/靠背/头枕通用）。
 * 用圆角 + 小倒角替代贴图做「软包」观感：无 UV 体系下几何造型是唯一的细节载体。
 * @param {number} w 侧视宽（X 向）
 * @param {number} h 侧视高（Y 向）
 * @param {number} r 圆角半径
 * @param {number} depth Z 向挤出深度（= 座宽）
 */
const roundedSideGeometry = (w, h, r, depth, bevel = 0.010) => {
  const rr = Math.max(Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3), 1e-3)
  const hw = w / 2
  const hh = h / 2
  const s = new THREE.Shape()
  s.moveTo(-hw + rr, -hh)
  s.lineTo(hw - rr, -hh)
  s.absarc(hw - rr, -hh + rr, rr, -Math.PI / 2, 0, false)
  s.lineTo(hw, hh - rr)
  s.absarc(hw - rr, hh - rr, rr, 0, Math.PI / 2, false)
  s.lineTo(-hw + rr, hh)
  s.absarc(-hw + rr, hh - rr, rr, Math.PI / 2, Math.PI, false)
  s.lineTo(-hw, -hh + rr)
  s.absarc(-hw + rr, -hh + rr, rr, Math.PI, Math.PI * 1.5, false)
  const g = new THREE.ExtrudeGeometry(s, {
    depth,
    bevelEnabled: true,
    bevelSize: bevel,
    bevelThickness: bevel,
    bevelSegments: 2,
    curveSegments: 6,
    steps: 1
  })
  g.translate(0, 0, -depth / 2)
  return g
}

/** 座次标签：前后排语义不同（驾驶位/副驾 ≠ 左/右） */
const seatLabels = (row, count) => {
  if (count >= 3) return ['left', 'mid', 'right']
  if (row === 1) return ['driver', 'passenger']
  return ['left', 'right']
}

/**
 * 生成一排座椅（坐垫 + 靠背 + 头枕 + 双侧翼）。
 *
 * 定位规则（与 carProfile 的座椅布局字段一一对应）：
 *   X = row1X - (row-1)·seatRowPitch，row1X = hoodEndX - 0.42（前排 H 点落于前轴后方）
 *   Y = seatHPointFront（第一排） / seatHPointRear（第二排及以后）
 *   Z = 按每排座数与车身内宽自适应分布
 *
 * @param {object} P     deriveCarProfile() 返回值（单位 m）
 * @param {number} row  排号（1 起；超出 seatRows 时按最后一排钳位，空排返回空 group）
 * @param {object} [opts]
 * @param {string} [opts.materialVariant] SEAT_MATERIAL_PRESETS 的键，默认 'standard'
 * @returns {THREE.Group} 排组（name = seat-row-N；子节点为单座 group）
 */
export function createSeatRow(P, row, opts = {}) {
  const variant = SEAT_MATERIAL_PRESETS[opts.materialVariant]
    ? opts.materialVariant
    : 'standard'
  const preset = SEAT_MATERIAL_PRESETS[variant]

  const rowIndex = Number.isFinite(+row) ? Math.round(+row) : 1
  // 排位/座数全部取自 carInteriorLayout（与 2D 布置图同一取数口，杜绝两套公式漂移）
  const placement = deriveRowPlacement(P, rowIndex)
  const count = placement?.count ?? 0

  const group = new THREE.Group()
  group.name = `seat-row-${rowIndex}`
  group.userData = { part: 'seat-row', row: rowIndex, count, materialVariant: variant }
  // 越界排号（>总排数 或 <1）返回空组：不得回落到相邻排，避免「要第三排却拿到第二排」
  if (!placement) return group

  const rowX = placement.x
  const hPoint = placement.hPointY

  // ---- 几何/材质在同排内共享（3 座共用一套几何，避免重复上传 GPU） ----
  const { width: seatWidth, centers } = placement.seat
  const surfaceMat = new THREE.MeshStandardMaterial({
    ...preset.surface,
    side: THREE.DoubleSide,
    envMapIntensity: 0.8
  })
  const bolsterMat = new THREE.MeshStandardMaterial({
    ...preset.bolster,
    side: THREE.DoubleSide,
    envMapIntensity: 0.8
  })
  surfaceMat.name = `seat-surface-${variant}`
  bolsterMat.name = `seat-bolster-${variant}`

  const cushionGeom = roundedSideGeometry(CUSHION_DEPTH, CUSHION_THICK, 0.045, seatWidth, 0.012)
  const backGeom = roundedSideGeometry(BACK_THICK, BACK_HEIGHT, 0.055, seatWidth, 0.010)
  const headGeom = roundedSideGeometry(HEAD_THICK, HEAD_HEIGHT, 0.045, seatWidth * HEAD_WIDTH_RATIO, 0.010)
  const bolsterGeom = roundedSideGeometry(CUSHION_DEPTH * 0.92, CUSHION_THICK + BOLSTER_EXTRA_H, 0.03, BOLSTER_W, 0.010)

  const attach = (parent, geom, mat, name, pos) => {
    const mesh = new THREE.Mesh(geom, mat)
    mesh.name = name
    mesh.position.set(pos[0], pos[1], pos[2])
    mesh.castShadow = false
    mesh.receiveShadow = true
    mesh.renderOrder = 2
    // Car3D.updateCar() 按 userData.noCastShadow 统一重设投影，内饰件必须显式标位
    mesh.userData.noCastShadow = true
    parent.add(mesh)
    return mesh
  }

  const labels = seatLabels(rowIndex, count)
  centers.forEach((z, i) => {
    const label = labels[i] || `pos-${i}`
    const seat = new THREE.Group()
    seat.name = `seat-r${rowIndex}-${label}`
    seat.position.set(rowX, hPoint, z)
    // H 点为座椅 local 原点：坐垫向下、靠背向上、头枕居靠背顶
    seat.userData = {
      part: 'seat',
      row: rowIndex,
      position: label,
      isDriver: rowIndex === 1 && label === 'driver',
      adjustable: true,
      adjustments: rowIndex === 1 ? ['slide', 'recline', 'height'] : ['slide', 'recline'],
      materialVariant: variant
    }

    // 坐垫：自 H 点向前伸出 CUSHION_DEPTH - 0.06，厚 CUSHION_THICK
    attach(seat, cushionGeom, surfaceMat, 'seat-cushion', [
      CUSHION_DEPTH / 2 - 0.06, -CUSHION_THICK / 2, 0
    ])
    // 双侧翼：贴合坐垫两端，略高出坐垫形成包裹感
    attach(seat, bolsterGeom, bolsterMat, 'seat-bolster-left', [
      CUSHION_DEPTH / 2 - 0.08, -CUSHION_THICK / 2 + BOLSTER_EXTRA_H / 2, -(seatWidth / 2 - BOLSTER_W / 2)
    ])
    attach(seat, bolsterGeom, bolsterMat, 'seat-bolster-right', [
      CUSHION_DEPTH / 2 - 0.08, -CUSHION_THICK / 2 + BOLSTER_EXTRA_H / 2, seatWidth / 2 - BOLSTER_W / 2
    ])

    // 靠背：独立 group 作为倾角枢轴，底部锚在 H 点（旋转不抬离坐垫）
    // 倾角必须与 2D 侧视包络取同一个解析值（seatBackLean），不得在此另取常量
    const backrest = new THREE.Group()
    backrest.name = 'seat-backrest-pivot'
    backrest.position.set(0, 0, 0)
    backrest.rotation.z = seatBackLean(P)
    seat.add(backrest)
    attach(backrest, backGeom, surfaceMat, 'seat-backrest', [0, BACK_HEIGHT / 2, 0])
    attach(backrest, headGeom, surfaceMat, 'seat-headrest', [
      0, BACK_HEIGHT + HEAD_GAP + HEAD_HEIGHT / 2, 0
    ])

    group.add(seat)
  })

  return group
}

/** 内饰非座椅件的材质（同一套深色内饰体系，无贴图，保持与座椅同一光照语言） */
export const INTERIOR_TRIM_MATERIALS = {
  carpet: { color: 0x14171b, roughness: 1.00, metalness: 0.00 },
  headliner: { color: 0x4a4f57, roughness: 0.94, metalness: 0.00 },
  doorTrim: { color: 0x22262c, roughness: 0.84, metalness: 0.04 },
  armrest: { color: 0x2f343c, roughness: 0.68, metalness: 0.06 },
  tunnel: { color: 0x1f2329, roughness: 0.80, metalness: 0.05 },
  belt: { color: 0x9aa4b2, roughness: 0.42, metalness: 0.55 }
}

/**
 * 生成剩余内饰件（门板内饰 / 中央通道 / 顶棚 / 地毯 / 安全带固定点）。
 *
 * 全部尺寸与位置取自 carInteriorLayout.deriveInteriorTrim（2D 布置图同一取数口），
 * 本函数只把米制 AABB 转成 BoxGeometry，不另立任何数值。
 * 渲染约束与座椅一致：castShadow=false / receiveShadow=true / renderOrder=2。
 *
 * @param {object} P deriveCarProfile() 返回值
 * @returns {THREE.Group} name = interior-trim；子网格名带部件语义，供测试与采样定位
 */
export function createInteriorTrim(P) {
  const T = deriveInteriorTrim(P)
  const group = new THREE.Group()
  group.name = 'interior-trim'
  group.userData = { part: 'interior-trim' }
  if (!T) return group

  const mats = {}
  for (const [key, cfg] of Object.entries(INTERIOR_TRIM_MATERIALS)) {
    const mat = new THREE.MeshStandardMaterial({ ...cfg, envMapIntensity: 0.7 })
    mat.name = `interior-trim-${key}`
    mats[key] = mat
  }

  /** 按 AABB 生成薄板/实体（z0/z1 必须有序传入） */
  const addBox = (name, r, mat) => {
    const w = Math.abs(r.x1 - r.x0)
    const h = Math.abs(r.y1 - r.y0)
    const d = Math.abs(r.z1 - r.z0)
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat)
    mesh.name = name
    mesh.position.set((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, (r.z0 + r.z1) / 2)
    mesh.castShadow = false
    mesh.receiveShadow = true
    mesh.renderOrder = 2
    mesh.userData.noCastShadow = true
    group.add(mesh)
    return mesh
  }

  const zSpan = (halfZ) => [-halfZ, halfZ]

  // ---- 地毯 / 顶棚：座舱内表面的两块「包裹层」----
  const [cz0, cz1] = zSpan(T.carpet.halfZ)
  addBox('carpet', { x0: T.carpet.x0, x1: T.carpet.x1, y0: T.carpet.y0, y1: T.carpet.y1, z0: cz0, z1: cz1 }, mats.carpet)

  const [hz0, hz1] = zSpan(T.headliner.halfZ)
  addBox('headliner', { x0: T.headliner.x0, x1: T.headliner.x1, y0: T.headliner.y0, y1: T.headliner.y1, z0: hz0, z1: hz1 }, mats.headliner)

  // ---- 中央通道：前排中控台本体 + 向后连通后排的低通道 ----
  const [tz0, tz1] = zSpan(T.tunnel.halfZ)
  addBox('tunnel-console', { ...T.tunnel.console, z0: tz0, z1: tz1 }, mats.tunnel)
  addBox('tunnel-rear', { ...T.tunnel.rear, z0: tz0, z1: tz1 }, mats.tunnel)

  // ---- 门板内饰 + 扶手：每个门洞两侧各一件 ----
  for (const d of T.doors) {
    const sideTag = d.side < 0 ? 'left' : 'right'
    addBox(`door-trim-${d.key}-${sideTag}`, d, mats.doorTrim)
  }
  for (const a of T.armrests) {
    const sideTag = a.side < 0 ? 'left' : 'right'
    addBox(`door-armrest-${a.key}-${sideTag}`, a, mats.armrest)
  }

  // ---- 安全带固定点：上固定点（B/C 柱）+ 下固定点（地板侧），几何按上/下共享 ----
  const upperGeom = new THREE.BoxGeometry(0.070, 0.050, 0.030)
  const lowerGeom = new THREE.BoxGeometry(0.050, 0.040, 0.050)
  for (const b of T.belts) {
    const mesh = new THREE.Mesh(b.kind === 'upper' ? upperGeom : lowerGeom, mats.belt)
    mesh.name = `seatbelt-${b.kind}-r${b.row}-${b.side < 0 ? 'left' : 'right'}`
    mesh.position.set(b.x, b.y, b.z)
    mesh.castShadow = false
    mesh.receiveShadow = true
    mesh.renderOrder = 2
    mesh.userData.noCastShadow = true
    group.add(mesh)
  }

  return group
}

/** IP/CONSOLE 功能模块材质（与整车深色内饰同一光照语言；显示屏黑晶、风口金属叶片分层） */
export const IP_CONSOLE_MATERIALS = {
  ipUpper: { color: 0x2a2e34, roughness: 0.85, metalness: 0.02 },   // 上体：软质搪塑表皮
  ipLower: { color: 0x212429, roughness: 0.78, metalness: 0.03 },   // 下体：硬质注塑
  screen: { color: 0x05070a, roughness: 0.25, metalness: 0.35 },    // 显示屏/组合仪表黑晶面板
  ventSlat: { color: 0x3a4046, roughness: 0.45, metalness: 0.55 },  // 出风口叶片
  consoleTrim: { color: 0x1a1d22, roughness: 0.30, metalness: 0.15 }, // 中控饰板/换挡基座
  armrestSoft: { color: 0x2f343c, roughness: 0.68, metalness: 0.06 }, // 扶手盖软包（与门扶手同色）
  cupWell: { color: 0x0c0e11, roughness: 0.90, metalness: 0.00 }     // 杯托沉台
}

/** 行李舱内饰材质（耐磨/防刮取向：PP 蜂窝衬板 + PET 针刺地毯 + 金属门槛护板） */
export const LUGGAGE_MATERIALS = {
  liner: { color: 0x23262b, roughness: 0.92, metalness: 0.02 },    // 舱壁衬板
  carpet: { color: 0x17191d, roughness: 1.00, metalness: 0.00 },   // 地板针刺地毯
  underfloor: { color: 0x0f1114, roughness: 1.00, metalness: 0.00 }, // 地板下储物井
  sillPlate: { color: 0x6a7076, roughness: 0.38, metalness: 0.75 }, // 装载门槛护板
  hardware: { color: 0x9aa4b2, roughness: 0.42, metalness: 0.55 },  // 锁扣/锚钩/应急拉手
  lampLens: { color: 0xf5f8ff, roughness: 0.20, metalness: 0.00, emissive: 0x8899aa, emissiveIntensity: 0.35 } // LED 舱灯
}

/** 通用 AABB → Box 网格（与 createInteriorTrim 同一渲染约束；供 IP/CONSOLE 与行李舱复用） */
const addTrimBox = (group, name, r, mat) => {
  const w = Math.abs(r.x1 - r.x0)
  const h = Math.abs(r.y1 - r.y0)
  const d = Math.abs(r.z1 - r.z0)
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat)
  mesh.name = name
  mesh.position.set((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2, (r.z0 + r.z1) / 2)
  mesh.castShadow = false
  mesh.receiveShadow = true
  mesh.renderOrder = 2
  mesh.userData.noCastShadow = true
  group.add(mesh)
  return mesh
}

/** 点状小件（锚钩 / 锁扣 / 拉手 / 灯）→ 小 Box 网格 */
const addPointBox = (group, name, p, mat, size = 0.03) => {
  return addTrimBox(group, name, {
    x0: p.x - size / 2, x1: p.x + size / 2,
    y0: p.y - size / 2, y1: p.y + size / 2,
    z0: p.z - size / 2, z1: p.z + size / 2
  }, mat)
}

/**
 * IP/CONSOLE 功能模块 3D 网格（组合仪表 / 悬浮式中控屏 / 出风口×4 / 手套箱 / 膝部护板 /
 * 副驾气囊盖板 / 无线充托盘 / 换挡 / 双杯托 / 扶手盖 / 后排风口）。
 * 全部坐标取自 deriveIpConsoleLayout（与 2D 标注图、人机验证同一取数口），本函数只做网格转换。
 */
export function createIpConsole(P) {
  const C = deriveIpConsoleLayout(P)
  const group = new THREE.Group()
  group.name = 'ip-console'
  group.userData = { part: 'ip-console' }
  if (!C) return group

  const mats = {}
  for (const [key, cfg] of Object.entries(IP_CONSOLE_MATERIALS)) {
    const mat = new THREE.MeshStandardMaterial({ ...cfg, envMapIntensity: 0.7 })
    mat.name = `ip-console-${key}`
    mats[key] = mat
  }

  // IP 本体上/下体分件（软包/硬塑分型线）
  addTrimBox(group, 'ip-shell-upper', C.shells.upper, mats.ipUpper)
  addTrimBox(group, 'ip-shell-lower', C.shells.lower, mats.ipLower)

  // 驾驶信息区：组合仪表（方向盘正前方）+ 悬浮式中控屏（含 60mm 安装臂）
  addTrimBox(group, 'ip-cluster', C.cluster, mats.screen)
  addTrimBox(group, 'ip-display', C.display, mats.screen)
  addTrimBox(group, 'ip-display-mount', {
    x0: C.display.x1, x1: C.display.x1 + 0.06,
    y0: (C.display.y0 + C.display.y1) / 2 - 0.03, y1: (C.display.y0 + C.display.y1) / 2 + 0.03,
    z0: -0.04, z1: 0.04
  }, mats.consoleTrim)

  // 空调出风区
  C.vents.center.forEach((v, i) => addTrimBox(group, `ip-vent-center-${i}`, v, mats.ventSlat))
  C.vents.side.forEach((v, i) => addTrimBox(group, `ip-vent-side-${i}`, v, mats.ventSlat))

  // 副驾储物区 + 安全标注件
  addTrimBox(group, 'ip-glovebox', C.glovebox, mats.ipLower)
  addTrimBox(group, 'ip-airbag-door', C.airbagDoor, mats.ipUpper)
  addTrimBox(group, 'ip-knee-panel', C.kneePanel, mats.ipLower)

  // 中控台面功能带
  addTrimBox(group, 'console-wireless-pad', C.wirelessPad, mats.consoleTrim)
  addTrimBox(group, 'console-shifter', C.shifter, mats.consoleTrim)
  C.cups.forEach((c, i) => addTrimBox(group, `console-cup-${i}`, c, mats.cupWell))
  addTrimBox(group, 'console-armrest-lid', C.armrestLid, mats.armrestSoft)
  if (C.rearVent) addTrimBox(group, 'console-rear-vent', C.rearVent, mats.ventSlat)

  return group
}

/**
 * 前/后行李舱开启状态内饰 3D 网格（舱壁衬板 / 地板地毯 / 轮拱饰盒 / 门槛护板 /
 * 地板下储物井 / 系留锚钩×4 / 储物网锚点 / 舱内 LED 照明 / 锁扣与应急拉手；frunk 独立成组）。
 * 全部坐标取自 deriveLuggageLayout（与容积、人机验证同一取数口）。
 */
export function createLuggageTrim(P) {
  const T = deriveLuggageLayout(P)
  const group = new THREE.Group()
  group.name = 'luggage-trim'
  group.userData = { part: 'luggage-trim' }
  if (!T) return group

  const mats = {}
  for (const [key, cfg] of Object.entries(LUGGAGE_MATERIALS)) {
    const mat = new THREE.MeshStandardMaterial({ ...cfg, envMapIntensity: 0.6 })
    mat.name = `luggage-${key}`
    mats[key] = mat
  }

  // ---- 后行李舱（封闭式行李舱 / 旅行式货舱 / 皮卡货箱衬里）----
  const r = T.rear
  addTrimBox(group, 'cargo-floor-carpet', r.floorCarpet, mats.carpet)
  r.sideLiners.forEach((l, i) => addTrimBox(group, `cargo-side-liner-${i === 0 ? 'right' : 'left'}`, l, mats.liner))
  addTrimBox(group, 'cargo-front-liner', r.frontLiner, mats.liner)
  addTrimBox(group, 'cargo-lid-inner', r.lidInner, mats.liner)
  addTrimBox(group, 'cargo-sill-plate', r.sillPlate, mats.sillPlate)
  r.archBoxes.forEach((b, i) => addTrimBox(group, `cargo-arch-box-${i === 0 ? 'right' : 'left'}`, b, mats.liner))
  if (r.underfloorWell) addTrimBox(group, 'cargo-underfloor-well', r.underfloorWell, mats.underfloor)
  r.hooks.forEach((h, i) => addPointBox(group, `cargo-hook-${i}`, h, mats.hardware))
  r.netAnchors.forEach((a, i) => addPointBox(group, `cargo-net-anchor-${i}`, a, mats.hardware, 0.024))
  addPointBox(group, 'cargo-lamp', r.lamp, mats.lampLens, 0.06)
  addPointBox(group, 'cargo-latch', r.latch, mats.hardware)
  addPointBox(group, 'cargo-release-handle', r.releaseHandle, mats.hardware, 0.036)

  // ---- 前行李舱（frunk）：地板 + 前后/左右壁 + 照明 + 锁扣 + 锚钩×2 ----
  if (T.frunk) {
    const f = T.frunk
    const wallT = G.luggageWallT
    addTrimBox(group, 'frunk-floor', {
      x0: f.x0, x1: f.x1, y0: f.floorY - 0.012, y1: f.floorY, z0: -f.halfZ, z1: f.halfZ
    }, mats.carpet)
    addTrimBox(group, 'frunk-wall-rear', {
      x0: f.x0, x1: f.x0 + wallT, y0: f.floorY, y1: f.topY, z0: -f.halfZ, z1: f.halfZ
    }, mats.liner)
    addTrimBox(group, 'frunk-wall-front', {
      x0: f.x1 - wallT, x1: f.x1, y0: f.floorY, y1: f.topY, z0: -f.halfZ, z1: f.halfZ
    }, mats.liner)
    for (const s of [1, -1]) {
      addTrimBox(group, `frunk-wall-${s > 0 ? 'right' : 'left'}`, {
        x0: f.x0, x1: f.x1, y0: f.floorY, y1: f.topY,
        z0: s > 0 ? f.halfZ - wallT : -f.halfZ, z1: s > 0 ? f.halfZ : -(f.halfZ - wallT)
      }, mats.liner)
    }
    addPointBox(group, 'frunk-lamp', f.lamp, mats.lampLens, 0.06)
    addPointBox(group, 'frunk-latch', f.latch, mats.hardware)
    f.hooks.forEach((h, i) => addPointBox(group, `frunk-hook-${i}`, h, mats.hardware))
  }

  return group
}

/**
 * 方向盘总成（轮圈 / 辐条×3 / 轮毂 / 转向柱），Car3D 与独立预览页共用。
 * 坐标链（单一真源 carInteriorLayout.steerWheel，含 tiltDeg / columnLen）：
 *   asm（世界锚点 x/y/z）→ rotation.z = -tilt（绕横轴 Z：轮顶前倾、轮面法线后上方对准驾驶员胸腹部）
 *   plane（rotation.y = -π/2，局部 +Z → 世界 -X 朝驾驶员）→ 全部件建在局部 XY 轮面内
 * 人机依据：SAE 乘用车轮面倾角惯例 20~25°（INTERIOR_GEOM.steerWheelTiltDeg）。
 */
export function createSteeringWheel(P) {
  const L = deriveInteriorLayout(P)
  const sw = L?.steerWheel
  const group = new THREE.Group()
  group.name = 'steering-wheel'
  group.userData = { part: 'steering-wheel' }
  if (!sw) return group

  const mat = new THREE.MeshStandardMaterial({ color: 0x9aa4b2, roughness: 0.35, metalness: 0.75, envMapIntensity: 0.7 })
  const tilt = (sw.tiltDeg * Math.PI) / 180

  group.rotation.z = -tilt
  const plane = new THREE.Group()
  plane.rotation.y = -Math.PI / 2
  group.add(plane)

  const rim = new THREE.Mesh(new THREE.TorusGeometry(sw.r, 0.012, 16, 32), mat)
  plane.add(rim)
  // 三辐（Y 形：12 / 4 / 8 点钟）：每根辐条半长 r、自轮毂沿辐向偏移 r/2 至轮圈，
  // 用「单向半辐」而非整条横杆，避免同一根杆被读成两根辐（六辐错觉）
  for (const a of [0, Math.PI * 2 / 3, -Math.PI * 2 / 3]) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.008, sw.r, 0.008), mat)
    spoke.rotation.z = a
    spoke.position.set(Math.sin(a) * sw.r / 2, Math.cos(a) * sw.r / 2, 0)
    plane.add(spoke)
  }
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 0.05, 12), mat)
  hub.rotation.x = Math.PI / 2
  plane.add(hub)
  // 转向柱：轮毂 → IP 面（局部 -Z 经 plane/tilt 映射为世界前下方，与实车柱体走向一致）
  const col = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, sw.columnLen, 8), mat)
  col.rotation.x = Math.PI / 2
  col.position.set(0, 0, -sw.columnLen / 2)
  plane.add(col)

  group.position.set(sw.x, sw.y, sw.z)
  return group
}
