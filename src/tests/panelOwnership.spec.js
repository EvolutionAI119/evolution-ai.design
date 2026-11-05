/**
 * 平台侧采纳《SISA 提案 PROPOSAL_TO_PLATFORM_PANEL_TOPOLOGY》修法 2 的等价回归。
 *
 * 提案判据 → 平台等价判据：
 *   A1 穷尽：每个面片都必须有归属（车漆 / 洞壁内饰），不得丢面
 *   A2 互斥：每个面片**恰好**属于一个分件，不得被两个分件各取一次（穿模根因 R2）
 *   A3 同壳：归属判据与挖洞几何**同一份数据**（真实洞口多边形），不靠 bbox 近似
 *   A4 车型正确：区间按车型舱位派生，皮卡等分支必须真实生效
 *   A5 区间派生：洞口 X 区间可由该车型的 carProfile/doorLayout 重新推出（不是写死轿车比例）
 *
 * 另含：rear_window_angle「与竖直方向夹角」语义门禁（声明角 vs 几何隐含角 ≤1.5°）。
 */

import { describe, it, expect } from 'vitest'
import { carTypeParams } from '../config/carPresets.js'
import { deriveCarProfile, deriveDoorLayout } from '../utils/carProfile.js'
import {
  deriveCabinGlass,
  deriveDloPaneRanges,
  polygonEdgeDistance,
  BODY_BEVEL_SIZE
} from '../utils/carGlass.js'
import { buildBodyShell } from '../three/geometry/bodyShell.js'
import {
  APERTURE_BAND,
  CAP_NORMAL_LIMIT,
  LEDGE_NORMAL_LIMIT,
  auditShellOwners
} from '../three/geometry/panelOwnership.js'

const TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']

const shellFor = (type, overrides = {}) => {
  const params = { ...carTypeParams[type], ...overrides }
  const P = deriveCarProfile(params, type)
  const cabin = deriveCabinGlass(P, { carType: type })
  const doorLayout = deriveDoorLayout(P, cabin, { carType: type })
  const paneRanges = deriveDloPaneRanges(doorLayout, 8)
  const shell = buildBodyShell({ P, carType: type, cabin, doorLayout, paneRanges })
  return { P, cabin, doorLayout, paneRanges, ...shell }
}

/** 逐三角形重心与面法线（与 panelOwnership 同一口径） */
const triangleAt = (arr, t) => {
  const o = t * 9
  const cx = (arr[o] + arr[o + 3] + arr[o + 6]) / 3
  const cy = (arr[o + 1] + arr[o + 4] + arr[o + 7]) / 3
  const cz = (arr[o + 2] + arr[o + 5] + arr[o + 8]) / 3
  const e1x = arr[o + 3] - arr[o], e1y = arr[o + 4] - arr[o + 1], e1z = arr[o + 5] - arr[o + 2]
  const e2x = arr[o + 6] - arr[o], e2y = arr[o + 7] - arr[o + 1], e2z = arr[o + 8] - arr[o + 2]
  let nx = e1y * e2z - e1z * e2y
  let ny = e1z * e2x - e1x * e2z
  let nz = e1x * e2y - e1y * e2x
  const l = Math.hypot(nx, ny, nz) || 1
  return { cx, cy, cz, nx: nx / l, ny: ny / l, nz: nz / l }
}

describe('A1 穷尽：每个车身面片都有归属，无面片被丢弃', () => {
  it.each(TYPES)('%s：paint + liner == 面片总数', (type) => {
    const { bodyGeom } = shellFor(type)
    const a = auditShellOwners(bodyGeom)
    expect(a.total).toBeGreaterThan(0)
    expect(a.liner).toBeGreaterThan(0)      // 洞口内壁确实被改判（不是全车漆）
    expect(a.paint).toBeGreaterThan(0)
    expect(a.paint + a.liner).toBe(a.total)
    expect(a.exhaustive).toBe(true)
  })
})

describe('A2 互斥：每个面片恰好属于一个分件（穿模根因 R2 平台等价）', () => {
  it.each(TYPES)('%s：两个材质组的顶点区间首尾相接、无重叠无空隙', (type) => {
    const { bodyGeom } = shellFor(type)
    const a = auditShellOwners(bodyGeom)
    expect(a.exclusive).toBe(true)
    // 组必须恰好两组，且起始组 = 车漆（材质数组顺序固定 [bodyMat, interiorMat]）
    expect(bodyGeom.groups).toHaveLength(2)
    expect(bodyGeom.groups[0].materialIndex).toBe(0)
    expect(bodyGeom.groups[1].materialIndex).toBe(1)
    expect(bodyGeom.groups[0].start).toBe(0)
    expect(bodyGeom.groups[1].start).toBe(bodyGeom.groups[0].count)
  })

  it.each(TYPES)('%s：内饰组不含端盖/水平壁（车侧可见漆面不被吞）', (type) => {
    const { bodyGeom } = shellFor(type)
    expect(auditShellOwners(bodyGeom).clean).toBe(true)
  })

  it('组 count 单位为顶点数：paint 三角形数 × 3 == 组 count', () => {
    const { bodyGeom } = shellFor('suv')
    const a = auditShellOwners(bodyGeom)
    expect(bodyGeom.groups[0].count).toBe(a.paint * 3)
    expect(bodyGeom.groups[1].count).toBe(a.liner * 3)
  })
})

describe('A3 同壳：归属判据与挖洞几何同一份洞口多边形（非 bbox 近似）', () => {
  it.each(TYPES)('%s：每个内饰面片重心到最近洞口边界 ≤ APERTURE_BAND', (type) => {
    const { bodyGeom, apertures } = shellFor(type)
    const arr = bodyGeom.attributes.position.array
    const liner = bodyGeom.groups.find((g) => g.materialIndex === 1)
    expect(apertures.length).toBeGreaterThan(0)
    let worst = 0
    for (let t = liner.start / 3; t < (liner.start + liner.count) / 3; t++) {
      const { cx, cy } = triangleAt(arr, t)
      let d = Infinity
      for (const ap of apertures) d = Math.min(d, polygonEdgeDistance(cx, cy, ap.pts))
      worst = Math.max(worst, d)
    }
    // 判据带宽 = bevel 收缩量 + 2mm 余量；越界即说明用了 bbox 近似（提案 R1 同构缺陷）
    expect(worst).toBeLessThanOrEqual(APERTURE_BAND + 1e-6)
    expect(APERTURE_BAND).toBeCloseTo(BODY_BEVEL_SIZE + 0.002, 12)
  })

  it.each(TYPES)('%s：洞口多边形是真实多边形（门洞为合并多边形，非矩形 bbox 回退）', (type) => {
    const { apertures, doorLayout } = shellFor(type)
    const door = apertures.find((a) => a.key === 'door')
    expect(door).toBeTruthy()
    // 门洞必须与门片玻璃洞口合并成简单多边形；退化时才会回退成 4 点矩形
    expect(door.pts.length).toBeGreaterThan(4)
    // 固定片（A 柱前 / C 柱后）为 4 点四边形，短车顶车型可能因最小宽度被跳过，
    // 但至少存在一片，且 key 只能来自洞口枚举
    expect(apertures.some((a) => a.key === 'fixedFront' || a.key === 'fixedRear')).toBe(true)
    for (const ap of apertures) {
      expect(['door', 'fixedFront', 'fixedRear']).toContain(ap.key)
    }
    expect(doorLayout.frontSeamX).toBeTypeOf('number')
  })
})

describe('A4 车型正确：洞口区间随车型舱位分支', () => {
  it('六车型均生成 door 洞口且 key 不重复（固定片可因最小宽度被跳过）', () => {
    for (const type of TYPES) {
      const { apertures } = shellFor(type)
      const keys = apertures.map((a) => a.key)
      expect(new Set(keys).size).toBe(keys.length)
      expect(keys).toContain('door')
    }
  })

  it('两门车型（coupe/sport/pickup）走后门缝回落分支：门洞后缘 = midSeamX − 4mm', () => {
    for (const type of ['coupe', 'sport', 'pickup']) {
      const { doorLayout, apertures } = shellFor(type)
      expect(doorLayout.rearSeamX).toBeNull()
      const door = apertures.find((a) => a.key === 'door')
      // 3D X+ 车头：后缘是 X 更小的一侧
      const minX = Math.min(...door.pts.map((p) => p[0]))
      expect(minX).toBeCloseTo(doorLayout.midSeamX - 0.004, 9)
    }
    // 皮卡特有：驾驶室后壁在门后缝之后 50mm（门板与后壁不互穿）
    const { P, doorLayout } = shellFor('pickup')
    expect(doorLayout.midSeamX).toBeCloseTo(P.pickup.cabRearX + 0.05, 9)
  })

  it('四门车型（sedan/suv/mpv）有独立后门缝，门洞后缘按 rearSeamX 派生', () => {
    for (const type of ['sedan', 'suv', 'mpv']) {
      const { doorLayout, apertures } = shellFor(type)
      expect(doorLayout.rearSeamX).not.toBeNull()
      const door = apertures.find((a) => a.key === 'door')
      const minX = Math.min(...door.pts.map((p) => p[0]))
      expect(minX).toBeCloseTo(doorLayout.rearSeamX - 0.004, 9)
    }
  })
})

describe('A5 区间派生：洞口 X 区间可由该车型参数重新推出（非写死轿车比例）', () => {
  it.each(TYPES)('%s：门洞前后缘 = doorLayout 接缝 ±4mm（逐点同源）', (type) => {
    const { doorLayout, apertures } = shellFor(type)
    const door = apertures.find((a) => a.key === 'door')
    const xs = door.pts.map((p) => p[0])
    const frontEdge = doorLayout.frontSeamX + 0.004
    const rearEdge = (doorLayout.rearSeamX === null ? doorLayout.midSeamX : doorLayout.rearSeamX) - 0.004
    expect(Math.max(...xs)).toBeCloseTo(frontEdge, 9)
    expect(Math.min(...xs)).toBeCloseTo(rearEdge, 9)
  })

  it('六车型门洞跨度互不相同（证明区间随车型派生，而非固定比例）', () => {
    const spans = TYPES.map((type) => {
      const { apertures } = shellFor(type)
      const xs = apertures.find((a) => a.key === 'door').pts.map((p) => p[0])
      return Math.max(...xs) - Math.min(...xs)
    })
    for (const s of spans) expect(s).toBeGreaterThan(0)
    // 至少 4 个互不相同的跨度（pickup 与 mpv 可能接近，但不允许全部相同）
    expect(new Set(spans.map((s) => s.toFixed(4))).size).toBeGreaterThanOrEqual(4)
  })

  it('洞口全部落在车身 X 包络内（不越出前后保险杠）', () => {
    for (const type of TYPES) {
      const { P, apertures } = shellFor(type)
      for (const ap of apertures) {
        for (const [x] of ap.pts) {
          expect(x).toBeGreaterThan(P.rearX - 0.01)
          expect(x).toBeLessThan(P.frontX + 0.01)
        }
      }
    }
  })
})

describe('归属求解的边界/极限场景（A1/A2 不得退化）', () => {
  const EXTREMES = [
    { label: '最小后窗角 10°', overrides: { rear_window_angle: 10 } },
    { label: '最大后窗角 60°', overrides: { rear_window_angle: 60 } },
    { label: '大轮径 780mm', overrides: { wheel_diameter: 780 } },
    { label: '小轮径 520mm', overrides: { wheel_diameter: 520 } },
    { label: '极短车顶 1200mm', overrides: { roof_height: 1200 } },
    { label: '极长车顶 2000mm', overrides: { roof_height: 2000 } }
  ]
  for (const { label, overrides } of EXTREMES) {
    it.each(TYPES)(`%s + ${label}：仍穷尽且互斥`, (type) => {
      const { bodyGeom } = shellFor(type, overrides)
      const a = auditShellOwners(bodyGeom)
      expect(a.exhaustive).toBe(true)
      expect(a.exclusive).toBe(true)
      expect(a.clean).toBe(true)
    })
  }
})

describe('rear_window_angle 语义门禁：声明角 == 几何隐含角（≤1.5°）', () => {
  it.each(TYPES)('%s：声明角与隐含角一致且未触发钳制', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    expect(P.rearWindowImpliedAngleDeg).toBeCloseTo(P.rearWindowAngleDeg, 6)
    expect(Math.abs(P.rearWindowImpliedAngleDeg - P.rearWindowAngleDeg)).toBeLessThanOrEqual(1.5)
    expect(P.rearWindowAngleClamped).toBe(false)
    // 与竖直方向的夹角语义：水平进深 = 玻璃带高 × tan(a)（非 /tan）
    const bandH = P.roofTopY - P.beltLineY
    const run = bandH * Math.tan((P.rearWindowAngleDeg * Math.PI) / 180)
    expect(P.rearWindowTopX - P.rearWindowBottomX).toBeCloseTo(run, 6)
  })

  it('皮卡驾驶室后壁角 = 声明角（旧实现隐含 90°，即完全不倾斜）', () => {
    const P = deriveCarProfile(carTypeParams.pickup, 'pickup')
    // 几何隐含角按真实壁高（车顶 → 货箱栏板）计算，与 band 角分开记录
    const wallDeg = (Math.atan2(P.pickup.cabWallRun, P.pickup.cabWallDrop) * 180) / Math.PI
    expect(wallDeg).toBeCloseTo(P.rearWindowAngleDeg, 6)
    expect(wallDeg).toBeLessThan(45)   // 绝不能是 90°（竖直壁）
    expect(P.pickup.cabWallRun).toBeGreaterThan(0)
  })

  it('极端角：10° 与 60° 下声明角与隐含角仍一致或明确标记钳制', () => {
    for (const angle of [10, 60]) {
      for (const type of TYPES) {
        const P = deriveCarProfile({ ...carTypeParams[type], rear_window_angle: angle }, type)
        if (P.rearWindowAngleClamped) {
          // 钳制来自「后窗下沿不得越过甲板起点 / 驾驶室后壁底」：进深被截短 ⟹ 隐含角小于声明角
          expect(P.rearWindowImpliedAngleDeg).toBeLessThanOrEqual(angle + 1e-9)
          // 钳制后下缘仍须落在车身内、且在顶缘之后（不得越过后保险杠）
          expect(P.rearWindowBottomX).toBeGreaterThanOrEqual(P.rearX - 1e-9)
          expect(P.rearWindowBottomX).toBeLessThanOrEqual(P.rearWindowTopX + 1e-9)
        } else {
          expect(Math.abs(P.rearWindowImpliedAngleDeg - angle)).toBeLessThanOrEqual(1.5)
        }
      }
    }
  })
})

describe('性能基准：归属在一次装配期内求解（无逐帧开销）', () => {
  it('六车型全量装配 + 归属审计总耗时 < 8s（含 three.js 挤出与法线重算）', () => {
    const t0 = performance.now()
    for (const type of TYPES) {
      const { bodyGeom } = shellFor(type)
      auditShellOwners(bodyGeom)
    }
    const ms = performance.now() - t0
    expect(ms).toBeLessThan(8000)
  })

  it('单次审计为纯遍历：面片数不变、无副作用（可重复调用得到相同结果）', () => {
    const { bodyGeom } = shellFor('suv')
    const first = auditShellOwners(bodyGeom)
    const second = auditShellOwners(bodyGeom)
    expect(second).toEqual(first)
    expect(bodyGeom.attributes.position.array.length).toBe(first.total * 9)
  })
})
