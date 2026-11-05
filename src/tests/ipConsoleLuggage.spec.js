// IP/CONSOLE 细化设计 + 前/后行李舱内饰设计 — 六车型断言
//
// 断言对象（单一真源链）：
//   deriveIpConsoleLayout  → createIpConsole（3D 网格）
//   deriveLuggageLayout    → createLuggageTrim（3D 网格）
// 覆盖：模块几何合法性（含于锚点 AABB、不重叠）、人机工程分级目标（手伸距/装载高）、
//       行李舱拓扑（封闭/旅行/货箱）、容积口径（VDA 至窗线）、3D 网格与真源逐值同源。

import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import {
  deriveInteriorLayout,
  deriveIpConsoleLayout,
  deriveLuggageLayout,
  INTERIOR_GEOM
} from '../utils/carInteriorLayout.js'
import { createIpConsole, createLuggageTrim } from '../utils/carInterior.js'
import { carTypeParams } from '../config/carPresets.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type) => deriveCarProfile(carTypeParams[type], type)
// 手伸距分级目标（按坐姿高度/座舱布局分级，设计规范 §人机验证要求）
const REACH_DISPLAY_MAX = { sedan: 0.75, suv: 0.80, coupe: 0.75, sport: 0.75, mpv: 0.85, pickup: 0.80 }
const REACH_SHIFTER_MAX = { sedan: 0.62, suv: 0.70, coupe: 0.62, sport: 0.62, mpv: 0.78, pickup: 0.62 }

const cx = (b) => (b.x0 + b.x1) / 2
const cy = (b) => (b.y0 + b.y1) / 2
const cz = (b) => (b.z0 + b.z1) / 2

describe('IP/CONSOLE 功能模块布置 — 六车型', () => {
  it.each(ALL_TYPES)('%s 模块齐全且锚定于 IP/console 真源', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const C = deriveIpConsoleLayout(P)
    expect(C).toBeTruthy()

    // 驾驶信息区在驾驶侧（Z-），副驾储物区在副驾侧（Z+）
    expect(cz(C.cluster)).toBeLessThan(0)
    expect(cz(C.glovebox)).toBeGreaterThan(0)
    expect(cz(C.display)).toBeCloseTo(0, 9)

    // 悬浮式中控屏：探出 IP 后面板（x1 在 face 之前），且探出量 ≤80mm
    expect(C.display.x1).toBeLessThan(L.ip.rearX)
    expect(L.ip.rearX - C.display.x1).toBeLessThanOrEqual(0.08 + 1e-9)

    // 面装模块全部落在 IP 竖向带内
    for (const m of [C.cluster, C.display, C.glovebox, C.kneePanel, ...C.vents.center, ...C.vents.side]) {
      expect(m.y0).toBeGreaterThanOrEqual(L.ip.bottomY - 1e-9)
      expect(m.y1).toBeLessThanOrEqual(L.ip.topY + 1e-9)
    }

    // IP 上/下体分型线位于带内
    expect(C.metrics.ipSplitY).toBeGreaterThan(L.ip.bottomY)
    expect(C.metrics.ipSplitY).toBeLessThan(L.ip.topY)
  })

  it.each(ALL_TYPES)('%s 中控功能带有序不重叠、总长 ≤ 台面长', (type) => {
    const C = deriveIpConsoleLayout(profileOf(type))
    const { wirelessPad, shifter, cups, armrestLid } = C
    // 前 → 后 单调递减（X+ 朝车头）
    expect(wirelessPad.x0).toBeGreaterThan(shifter.x1 - 1e-9)
    expect(shifter.x0).toBeGreaterThan(cups[0].x1 - 1e-9)
    expect(cups[0].x0).toBeGreaterThan(armrestLid.x1 - 1e-9)
    // 两端不越出台面
    const L = deriveInteriorLayout(profileOf(type))
    expect(wirelessPad.x1).toBeLessThanOrEqual(L.console.frontX + 1e-9)
    expect(armrestLid.x0).toBeGreaterThanOrEqual(L.console.rearX - 1e-9)
    expect(C.metrics.consoleModulesLength).toBeLessThanOrEqual(C.metrics.consoleLength + 1e-9)
    // 扶手盖长度下限（A-2 整改：≥200mm，保证肘部支撑与储物腔；台面长上限已扩至 0.50m）
    expect(armrestLid.x1 - armrestLid.x0).toBeGreaterThanOrEqual(0.20 - 1e-9)
    // 双杯托 Z 向并排、沉台于台面之下
    expect(cups[0].z0).toBeGreaterThan(0)
    expect(cups[1].z1).toBeLessThan(0)
    expect(cups[0].y1).toBeCloseTo(L.console.topY, 9)
    expect(cups[0].y0).toBeLessThan(L.console.topY)
  })

  it.each(ALL_TYPES)('%s 人机工程：手伸距满足分级目标', (type) => {
    const C = deriveIpConsoleLayout(profileOf(type))
    expect(C.metrics.reachDisplay).toBeLessThanOrEqual(REACH_DISPLAY_MAX[type])
    expect(C.metrics.reachShifter).toBeLessThanOrEqual(REACH_SHIFTER_MAX[type])
    // 组合仪表中心高出 H 点 0.25~0.55m（视认性区间）
    expect(C.metrics.clusterAboveHPoint).toBeGreaterThan(0.25)
    expect(C.metrics.clusterAboveHPoint).toBeLessThan(0.60)
  })

  it.each(ALL_TYPES)('%s 后排出风口存在性 = 有第二排', (type) => {
    const C = deriveIpConsoleLayout(profileOf(type))
    const L = deriveInteriorLayout(profileOf(type))
    expect(!!C.rearVent).toBe(L.rows.length > 1)
  })
})

describe('前/后行李舱内饰布置 — 六车型', () => {
  it.each(ALL_TYPES)('%s 后行李舱几何合法、部件齐全', (type) => {
    const P = profileOf(type)
    const T = deriveLuggageLayout(P)
    expect(T).toBeTruthy()
    const r = T.rear
    const m = T.meta

    // 容积为正，装载高度在人机区间
    expect(m.volumeL).toBeGreaterThan(0)
    expect(m.loadingHeight).toBeGreaterThan(0.20)
    expect(m.loadingHeight).toBeLessThan(0.95)
    expect(m.loadingLength).toBeGreaterThan(0.30)

    // 舱体在车身范围内（皮卡货箱尾门段按外观真源可越出 rearX，见 deriveCarProfile pickup 拓扑）
    expect(r.x0).toBeGreaterThanOrEqual(Math.min(P.rearX, P.pickup?.bedRearX ?? P.rearX) - 1e-9)
    expect(r.floorY).toBeGreaterThan(P.bodyBottomY)
    expect(r.topY).toBeLessThanOrEqual((P.roofTopY ?? P.H) + 1e-9)

    // 部件齐全：锚钩×4 / 网锚×2 / 灯 / 锁 / 应急拉手
    expect(r.hooks).toHaveLength(4)
    expect(r.netAnchors).toHaveLength(2)
    expect(r.lamp.y - r.floorY).toBeCloseTo(INTERIOR_GEOM.luggageLampAbove, 9)
    expect(r.latch).toBeTruthy()
    expect(r.releaseHandle).toBeTruthy()
    // 锚钩四角分布（前后各一对、左右对称）
    const zs = r.hooks.map((h) => h.z)
    expect(Math.max(...zs)).toBeGreaterThan(0)
    expect(Math.min(...zs)).toBeLessThan(0)
    // 门槛护板覆盖舱口全宽
    expect(r.sillPlate.z1 - r.sillPlate.z0).toBeCloseTo(2 * r.aperture.halfZ, 9)
  })

  it.each(ALL_TYPES)('%s 后行李舱拓扑正确', (type) => {
    const P = profileOf(type)
    const T = deriveLuggageLayout(P)
    if (type === 'pickup') {
      expect(T.meta.type).toBe('pickup-bed')
      // 货箱衬里内表面在栏板内，且横向不得越过后轮拱腔体（否则地板/内衬从轮口穿出）
      const archInner = Math.max(0.30,
        P.halfTrack - P.tireWidth / 2 - INTERIOR_GEOM.wagonArchClearance)
      expect(T.rear.halfZ).toBeLessThanOrEqual(P.pickup.bedInteriorHalfZ - INTERIOR_GEOM.luggageWallT + 1e-9)
      expect(T.rear.halfZ).toBeLessThanOrEqual(archInner - INTERIOR_GEOM.luggageWallT - 0.02 + 1e-9)
      expect(T.rear.x1).toBeLessThanOrEqual(P.pickup.bedFrontX)
      expect(T.rear.x0).toBeGreaterThanOrEqual(P.pickup.bedRearX)
      // 内腔不得越出车身车尾面、也不得越过驾驶室后壁
      expect(T.rear.x0).toBeGreaterThan(P.rearX)
      expect(T.rear.x1).toBeLessThan(P.pickup.cabRearX)
    } else if (type === 'suv' || type === 'mpv') {
      expect(T.meta.type).toBe('wagon')
      // 旅行式货舱：前界不越过末排靠背后缘；VDA 容积口径 coverY ≤ 舱顶
      const L = deriveInteriorLayout(P)
      const lastBackRearX = Math.min(...L.rows[L.rows.length - 1].envelope.backrest.points.map((p) => p[0]))
      expect(T.rear.x1).toBeLessThanOrEqual(lastBackRearX - 0.05)
      expect(T.rear.coverY).toBeLessThanOrEqual(T.rear.topY)
    } else {
      expect(T.meta.type).toBe('trunk')
      // 封闭式行李舱：前界不越过甲板起点
      expect(T.rear.x1).toBeLessThanOrEqual(P.trunkStartX + 1e-9)
      expect(T.rear.topY).toBeLessThanOrEqual(P.trunkLineY + 1e-9)
    }
  })

  it('suv 旅行式货舱输出拱间净宽；舱宽已收口时无多余轮拱饰盒', () => {
    const P = profileOf('suv')
    const T = deriveLuggageLayout(P)
    const G = INTERIOR_GEOM
    const archInner = Math.max(0.30,
      P.halfTrack - P.tireWidth / 2 - G.wagonArchClearance)
    expect(T.meta.widthBetweenArches).toBeCloseTo(2 * archInner, 9)
    expect(T.meta.widthBetweenArches).toBeGreaterThan(0.9)
    // 舱壁外表面已在轮拱线以内 → 不存在台阶，饰盒应为空；若舱宽大于拱间净宽则必须有两盒
    if (T.rear.halfZ + G.luggageWallT > archInner + 0.005) {
      expect(T.rear.archBoxes.length).toBe(2)
    } else {
      expect(T.rear.archBoxes.length).toBe(0)
    }
    for (const b of T.rear.archBoxes) {
      expect(b.y1).toBeLessThanOrEqual(T.rear.topY)
      expect(b.y0).toBeCloseTo(T.rear.floorY, 9)
    }
  })

  it.each(ALL_TYPES)('%s 前行李舱（frunk）存在性与几何合法', (type) => {
    const P = profileOf(type)
    const T = deriveLuggageLayout(P)
    // 轮毂直径收窄到后端契约（350~600mm）后，前轮拱跳动包络相应减小，
    // SUV 前舱也出现可用空间 → frunk 存在（不再是必空），一律走几何合法性校验。
    const f = T.frunk
    expect(f).toBeTruthy()
    // 避让前轮拱转向包络、不越出车头
    expect(f.x0).toBeGreaterThanOrEqual(P.frontWheelX + P.wheelArch.front.rx)
    expect(f.x1).toBeLessThanOrEqual(P.frontX)
    expect(f.topY).toBeLessThanOrEqual(P.hoodLineY)
    expect(f.floorY).toBeGreaterThan(P.bodyBottomY)
    expect(f.volumeL).toBeGreaterThan(0)
    expect(f.hooks).toHaveLength(2)
    expect(f.lamp).toBeTruthy()
    expect(f.latch).toBeTruthy()
  })
})

describe('IP/CONSOLE + 行李舱 3D 网格 — 与真源逐值同源', () => {
  it.each(ALL_TYPES)('%s createIpConsole 网格与 deriveIpConsoleLayout 逐值一致', (type) => {
    const P = profileOf(type)
    const C = deriveIpConsoleLayout(P)
    const group = createIpConsole(P)
    expect(group.name).toBe('ip-console')
    const byName = (n) => group.children.find((c) => c.name === n)

    for (const name of ['ip-shell-upper', 'ip-shell-lower', 'ip-cluster', 'ip-display',
      'ip-glovebox', 'ip-knee-panel', 'console-wireless-pad', 'console-shifter',
      'console-cup-0', 'console-cup-1', 'console-armrest-lid',
      'ip-vent-center-0', 'ip-vent-center-1', 'ip-vent-side-0', 'ip-vent-side-1']) {
      expect(byName(name), name).toBeTruthy()
    }
    // 中控屏网格位置 = 真源 AABB 中心
    const d = byName('ip-display')
    expect(d.position.x).toBeCloseTo(cx(C.display), 12)
    expect(d.position.y).toBeCloseTo(cy(C.display), 12)
    expect(d.position.z).toBeCloseTo(cz(C.display), 12)
    // 扶手盖网格尺寸 = 真源尺寸
    const lid = byName('console-armrest-lid')
    expect(lid.geometry.parameters.width).toBeCloseTo(C.armrestLid.x1 - C.armrestLid.x0, 12)
  })

  it.each(ALL_TYPES)('%s createLuggageTrim 网格与 deriveLuggageLayout 逐值一致', (type) => {
    const P = profileOf(type)
    const T = deriveLuggageLayout(P)
    const group = createLuggageTrim(P)
    expect(group.name).toBe('luggage-trim')
    const byName = (n) => group.children.find((c) => c.name === n)

    for (const name of ['cargo-floor-carpet', 'cargo-side-liner-left', 'cargo-side-liner-right',
      'cargo-front-liner', 'cargo-lid-inner', 'cargo-sill-plate',
      'cargo-hook-0', 'cargo-hook-1', 'cargo-hook-2', 'cargo-hook-3',
      'cargo-lamp', 'cargo-latch', 'cargo-release-handle']) {
      expect(byName(name), name).toBeTruthy()
    }
    const floor = byName('cargo-floor-carpet')
    expect(floor.position.x).toBeCloseTo(cx(T.rear.floorCarpet), 12)
    expect(floor.position.y).toBeCloseTo(cy(T.rear.floorCarpet), 12)
    // frunk 网格存在性与真源一致
    expect(!!byName('frunk-floor')).toBe(!!T.frunk)
  })
})

// 同步完整性：交付方案（真源 AABB 清单）↔ 三维模型（网格清单）双向一一对应，
// 既防「方案有件、模型缺失」，也防「模型多件、方案无据」，并逐件核对中心与尺寸。
const ipRects = (C) => {
  const out = [
    ['ip-shell-upper', C.shells.upper], ['ip-shell-lower', C.shells.lower],
    ['ip-cluster', C.cluster], ['ip-display', C.display],
    ['ip-glovebox', C.glovebox], ['ip-airbag-door', C.airbagDoor],
    ['ip-knee-panel', C.kneePanel],
    ['console-wireless-pad', C.wirelessPad], ['console-shifter', C.shifter],
    ['console-armrest-lid', C.armrestLid]
  ]
  C.vents.center.forEach((v, i) => out.push([`ip-vent-center-${i}`, v]))
  C.vents.side.forEach((v, i) => out.push([`ip-vent-side-${i}`, v]))
  C.cups.forEach((c, i) => out.push([`console-cup-${i}`, c]))
  if (C.rearVent) out.push(['console-rear-vent', C.rearVent])
  return out
}
const luggageRects = (T) => {
  const r = T.rear
  const out = [
    ['cargo-floor-carpet', r.floorCarpet], ['cargo-front-liner', r.frontLiner],
    ['cargo-lid-inner', r.lidInner], ['cargo-sill-plate', r.sillPlate]
  ]
  r.sideLiners.forEach((l, i) => out.push([`cargo-side-liner-${i === 0 ? 'right' : 'left'}`, l]))
  r.archBoxes.forEach((b, i) => out.push([`cargo-arch-box-${i === 0 ? 'right' : 'left'}`, b]))
  if (r.underfloorWell) out.push(['cargo-underfloor-well', r.underfloorWell])
  return out
}

describe('整车内饰三维同步 — 交付方案与网格件逐个对齐（六车型）', () => {
  it.each(ALL_TYPES)('%s IP/CONSOLE 网格与方案件一一对应且零错位', (type) => {
    const P = profileOf(type)
    const C = deriveIpConsoleLayout(P)
    const group = createIpConsole(P)
    const plan = ipRects(C)
    const planNames = plan.map(([n]) => n).sort()
    // 允许网格中存在方案外的纯装配件（悬浮屏安装臂），其余必须严格对应
    const meshNames = group.children.map((c) => c.name).filter((n) => n !== 'ip-display-mount').sort()
    expect(meshNames).toEqual(planNames)
    for (const [name, r] of plan) {
      const m = group.children.find((c) => c.name === name)
      expect(m.position.x).toBeCloseTo((r.x0 + r.x1) / 2, 12)
      expect(m.position.y).toBeCloseTo((r.y0 + r.y1) / 2, 12)
      expect(m.position.z).toBeCloseTo((r.z0 + r.z1) / 2, 12)
      expect(m.geometry.parameters.width).toBeCloseTo(Math.abs(r.x1 - r.x0), 12)
      expect(m.geometry.parameters.height).toBeCloseTo(Math.abs(r.y1 - r.y0), 12)
      expect(m.geometry.parameters.depth).toBeCloseTo(Math.abs(r.z1 - r.z0), 12)
    }
  })

  it.each(ALL_TYPES)('%s 行李舱网格与方案件一一对应且零错位', (type) => {
    const P = profileOf(type)
    const T = deriveLuggageLayout(P)
    const group = createLuggageTrim(P)
    const plan = luggageRects(T)
    const planNames = plan.map(([n]) => n).sort()
    const pointNames = [
      ...T.rear.hooks.map((_, i) => `cargo-hook-${i}`),
      ...T.rear.netAnchors.map((_, i) => `cargo-net-anchor-${i}`),
      'cargo-lamp', 'cargo-latch', 'cargo-release-handle'
    ]
    const meshNames = group.children.map((c) => c.name)
      .filter((n) => !n.startsWith('frunk-'))
      .sort()
    expect(meshNames).toEqual([...planNames, ...pointNames].sort())
    for (const [name, r] of plan) {
      const m = group.children.find((c) => c.name === name)
      expect(m.position.x).toBeCloseTo((r.x0 + r.x1) / 2, 12)
      expect(m.position.y).toBeCloseTo((r.y0 + r.y1) / 2, 12)
      expect(m.position.z).toBeCloseTo((r.z0 + r.z1) / 2, 12)
      expect(m.geometry.parameters.width).toBeCloseTo(Math.abs(r.x1 - r.x0), 12)
      expect(m.geometry.parameters.height).toBeCloseTo(Math.abs(r.y1 - r.y0), 12)
      expect(m.geometry.parameters.depth).toBeCloseTo(Math.abs(r.z1 - r.z0), 12)
    }
    // frunk 件：有舱必有全套墙体，无舱则零残余件
    const frunkNames = group.children.map((c) => c.name).filter((n) => n.startsWith('frunk-'))
    if (T.frunk) {
      expect(frunkNames.sort()).toEqual(['frunk-floor', 'frunk-hook-0', 'frunk-hook-1',
        'frunk-lamp', 'frunk-latch', 'frunk-wall-front', 'frunk-wall-left', 'frunk-wall-rear', 'frunk-wall-right'])
    } else {
      expect(frunkNames).toEqual([])
    }
  })
})
