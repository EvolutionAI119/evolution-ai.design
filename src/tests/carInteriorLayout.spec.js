import { describe, it, expect } from 'vitest'
import * as THREE from 'three'
import { deriveCarProfile } from '../utils/carProfile.js'
import { carTypeParams } from '../config/carPresets.js'
import {
  INTERIOR_GEOM, deriveInteriorLayout, deriveRowPlacement, deriveFloorY,
  seatSideEnvelope, steerWheelX, deriveSectionLayout,
  deriveDoorAperturesX, deriveFrontRowX, deriveInteriorTrim,
  seatBackLean, SEAT_BACK_LEAN_BY_TYPE, deriveSeatTrackTravel
} from '../utils/carInteriorLayout.js'
import { createSeatRow, createInteriorTrim } from '../utils/carInterior.js'
import { createSideViewProjection, createFrontViewProjection } from '../utils/car2dProjection.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type, extra) => deriveCarProfile({ ...carTypeParams[type], ...extra }, type)
const layoutOf = (type, extra) => deriveInteriorLayout(profileOf(type, extra))

/** 单座组（userData.part === 'seat'） */
const seatGroupsOf = (rowGroup) => rowGroup.children.filter((c) => c.userData?.part === 'seat')

/** 侧视包络的 AABB（坐垫 + 靠背 + 头枕三角，单位为米） */
const envelopeBox = (env) => {
  const xs = [env.cushion.x0, env.cushion.x1, ...env.backrest.points.map((p) => p[0]), ...env.headrest.points.map((p) => p[0])]
  const ys = [env.cushion.y0, env.cushion.y1, ...env.backrest.points.map((p) => p[1]), ...env.headrest.points.map((p) => p[1])]
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) }
}

/** 3D 坐垫/靠背/头枕三件的 AABB（排除侧翼：侧翼高出坐垫，属造型件不属侧视包络） */
const coreSeatBox = (seatGroup) => {
  // 席组不在场景中，必须先更新世界矩阵，否则 AABB 只反映 local 坐标
  seatGroup.updateWorldMatrix(true, true)
  const box = new THREE.Box3()
  box.makeEmpty()
  seatGroup.traverse((o) => {
    if (!o.isMesh) return
    if (!['seat-cushion', 'seat-backrest', 'seat-headrest'].includes(o.name)) return
    box.expandByObject(o)
  })
  return box
}

describe('内饰布置 — 排数/座数与 carProfile 座椅 schema 一致', () => {
  it.each(ALL_TYPES)('%s 布置排数 = seatRows，排位随排号向车尾递减', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    expect(L.rows.length).toBe(P.seatRows)
    for (let i = 1; i < L.rows.length; i++) {
      expect(L.rows[i].x).toBeLessThan(L.rows[i - 1].x)
      expect(L.rows[i].row).toBe(i + 1)
    }
    // 每排座数 = seatRowCounts（2/3 座由 rowSeatLayout 给出等距中心）
    L.rows.forEach((r, i) => {
      expect(r.count).toBe(P.seatRowCounts[i])
      expect(r.seat.centers.length).toBe(r.count)
    })
  })

  it('越界排号返回 null（不得回落到相邻排）', () => {
    const P = profileOf('sport')
    expect(deriveRowPlacement(P, 2)).toBeNull()
    expect(deriveRowPlacement(P, 0)).toBeNull()
    expect(deriveRowPlacement(P, -1)).toBeNull()
    const sedan = profileOf('sedan')
    expect(deriveRowPlacement(sedan, 5)).toBeNull()
  })

  it('布置结果是纯函数（同参数两次调用逐字段相等）', () => {
    const a = layoutOf('mpv')
    const b = layoutOf('mpv')
    expect(JSON.stringify(a)).toBe(JSON.stringify(b))
  })
})

describe('2D 布置图 ↔ 3D 模型 坐标对齐（零偏移）', () => {
  it.each(ALL_TYPES)('%s 每个 3D 座椅的原点严格等于 2D 布置图的 H 点坐标', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    for (const row of L.rows) {
      const seats = seatGroupsOf(createSeatRow(P, row.row))
      expect(seats.length).toBe(row.count)
      seats.forEach((s, i) => {
        // 同一取数口 → 必须是同一个数值，不允许「近似相等」
        expect(s.position.x).toBe(row.x)
        expect(s.position.y).toBe(row.hPointY)
        // 横向中心同样取自 rowSeatLayout（2D 侧视无 Z，但 3D 必须按其分布）
        expect(s.position.z).toBe(row.seat.centers[i])
      })
    }
  })

  it.each(ALL_TYPES)('%s 3D 座椅（坐垫/靠背/头枕）AABB ⊂ 2D 侧视包络 + 倒角容差', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    // 容差 = 单面倒角 0.012m + 数值余量
    const tol = 0.02
    for (const row of L.rows) {
      const env = envelopeBox(row.envelope)
      for (const s of seatGroupsOf(createSeatRow(P, row.row))) {
        const box = coreSeatBox(s)
        expect(box.min.x).toBeGreaterThanOrEqual(env.minX - tol)
        expect(box.max.x).toBeLessThanOrEqual(env.maxX + tol)
        expect(box.min.y).toBeGreaterThanOrEqual(env.minY - tol)
        expect(box.max.y).toBeLessThanOrEqual(env.maxY + tol)
      }
    }
  })

  it.each(ALL_TYPES)('%s 2D 像素可反解回 3D 米（投影零漂移）', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const pxPerM = 61.3   // 任意缩放：换算必须与像素密度无关
    const groundY = 366
    const proj = createSideViewProjection(P, pxPerM, groundY)

    const roundTrip = (x, y) => {
      expect(proj.fromX(proj.toX(x))).toBeCloseTo(x, 9)
      expect(proj.fromY(proj.toY(y))).toBeCloseTo(y, 9)
    }

    for (const row of L.rows) {
      roundTrip(row.x, row.hPointY)
      const r = row.envelope.cushion
      const rect = proj.rect(r.x0, r.x1, r.y0, r.y1)
      expect(proj.fromX(rect.x + rect.w)).toBeCloseTo(r.x0, 9)
      expect(proj.fromX(rect.x)).toBeCloseTo(r.x1, 9)
      expect(proj.fromY(rect.y + rect.h)).toBeCloseTo(r.y0, 9)
      expect(proj.fromY(rect.y)).toBeCloseTo(r.y1, 9)
      // 屏幕尺寸 = 米 × pxPerM（比例严格一致，无额外偏移）
      expect(rect.w).toBeCloseTo((r.x1 - r.x0) * pxPerM, 9)
      expect(rect.h).toBeCloseTo((r.y1 - r.y0) * pxPerM, 9)
    }

    roundTrip(L.ip.rearX, L.ip.topY)
    roundTrip(L.console.frontX, L.console.bottomY)
    roundTrip(L.doorPanel.x0, L.doorPanel.armrestY)
    roundTrip(L.steerWheel.x, L.steerWheel.y)
  })

  it.each(ALL_TYPES)('%s 方向盘 2D 圆 / 3D 圆环 同锚点同半径', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    expect(L.steerWheel.x).toBe(steerWheelX(P))
    expect(L.steerWheel.r).toBe(INTERIOR_GEOM.steerWheelRadius)
    expect(L.steerWheel.y).toBeCloseTo(L.rows[0].hPointY + INTERIOR_GEOM.steerWheelAboveHPoint, 12)
  })

  it.each(ALL_TYPES)('%s 方向盘轮面倾角符合 SAE 人机惯例（15°~30°，与 3D 总成同源）', (type) => {
    const L = deriveInteriorLayout(profileOf(type))
    expect(L.steerWheel.tiltDeg).toBe(INTERIOR_GEOM.steerWheelTiltDeg)
    expect(L.steerWheel.tiltDeg).toBeGreaterThanOrEqual(15)
    expect(L.steerWheel.tiltDeg).toBeLessThanOrEqual(30)
    expect(L.steerWheel.columnLen).toBe(INTERIOR_GEOM.steerColumnLength)
    expect(L.steerWheel.columnLen).toBeGreaterThanOrEqual(0.15)
    expect(L.steerWheel.columnLen).toBeLessThanOrEqual(0.35)
  })

  it('%s 2D 侧视包络与 3D 几何常量同源（坐垫/靠背/头枕尺寸无第二套数值）', () => {
    const P = profileOf('sedan')
    const row = deriveInteriorLayout(P).rows[0]
    const env = seatSideEnvelope(row.x, row.hPointY)
    expect(env.cushion.x1 - env.cushion.x0).toBeCloseTo(INTERIOR_GEOM.cushionDepth, 12)
    expect(env.cushion.y1 - env.cushion.y0).toBeCloseTo(INTERIOR_GEOM.cushionThick, 12)
    expect(env.topY - env.cushion.y1).toBeGreaterThan(INTERIOR_GEOM.backHeight)
  })
})

describe('人机工程验证清单（6 车型全量断言）', () => {
  it.each(ALL_TYPES)('%s 头部余量 / H 点离地 / 坐垫高于地板 达标', (type) => {
    const P = profileOf(type)
    const m = deriveInteriorLayout(P).metrics
    // 头枕顶到车顶 ≥ 50mm（低于此人无法戴帽/头盔通过）
    expect(m.headRoom).toBeGreaterThanOrEqual(0.05)
    // 坐垫面高于地板 0.22~0.34m（低于会蹲坐，高于则大腿承托不足）
    expect(m.cushionAboveFloor).toBeGreaterThanOrEqual(0.20)
    expect(m.cushionAboveFloor).toBeLessThanOrEqual(0.36)
    // H 点离地 = 前排在 P 中定义的实车值
    expect(m.floorY + m.cushionAboveFloor).toBeCloseTo(P.seatHPointFront, 9)
    // 坐垫面到车顶 ≥ 0.80m（坐姿头顶净空）
    expect(m.seatToRoof).toBeGreaterThanOrEqual(0.80)
  })

  it.each(ALL_TYPES)('%s 腿部与膝部操作空间 达标', (type) => {
    const L = layoutOf(type)
    const m = L.metrics
    // H 点 → 仪表板面 ≥ 0.40m（转向/踏板操作空间）
    expect(m.hipToDash).toBeGreaterThanOrEqual(0.40)
    // 坐垫前缘 → 仪表板面 ≥ 30mm（膝部不得顶到护板）
    expect(m.kneeClearance).toBeGreaterThanOrEqual(0.03)
    // 后排腿部空间 ≥ 0.45m（有第二排时）
    if (m.legRoomRear !== null) expect(m.legRoomRear).toBeGreaterThanOrEqual(0.45)
    // 方向盘中心与 H 点水平距离 = 设计值
    expect(m.hPointToWheel).toBeCloseTo(INTERIOR_GEOM.steerWheelToHPoint, 9)
  })

  it.each(ALL_TYPES)('%s 仪表台 / 中控台 / 门板扶手 达标且互不穿模', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    // 仪表台进深与高度
    expect(L.metrics.ipDepth).toBeGreaterThanOrEqual(INTERIOR_GEOM.ipMinDepth)
    expect(L.metrics.ipDepth).toBeLessThanOrEqual(INTERIOR_GEOM.ipDepth + 1e-9)
    expect(L.metrics.ipHeight).toBeGreaterThanOrEqual(INTERIOR_GEOM.ipMinHeight)
    // 仪表台上沿不得高过腰带线（否则挡住前视野）
    expect(L.ip.topY).toBeLessThan(P.beltLineY)
    // 仪表台前缘不得越过发动机舱端点
    expect(L.ip.frontX).toBeLessThan(P.hoodEndX)
    // 中控台：高度达标、扶手面低于坐垫面、底落在地板
    expect(L.metrics.consoleHeight).toBeGreaterThanOrEqual(INTERIOR_GEOM.consoleMinHeight)
    expect(L.console.topY).toBeLessThan(L.rows[0].hPointY)
    expect(L.console.bottomY).toBeCloseTo(L.floorY, 12)
    expect(L.console.rearX).toBeLessThan(L.console.frontX)
    // 中控台与仪表台仅允许 100mm 重叠（前伸段），不得穿过仪表台
    expect(L.console.frontX - L.ip.rearX).toBeCloseTo(INTERIOR_GEOM.consoleFrontOverlap, 12)
    // 门板扶手面低于坐垫面，且门板带在地板之上
    expect(L.doorPanel.armrestY).toBeLessThan(L.rows[0].hPointY)
    expect(L.doorPanel.y0).toBeGreaterThan(L.floorY)
    expect(L.doorPanel.x1).toBeGreaterThan(L.doorPanel.x0)
  })

  it('地板高度由车身底板 + 结构厚度推导，不直接落在车身底板', () => {
    for (const type of ALL_TYPES) {
      const P = profileOf(type)
      const floorY = deriveFloorY(P, P.seatHPointFront)
      expect(floorY).toBeGreaterThan(P.bodyBottomY)
      expect(floorY).toBeLessThanOrEqual(P.seatHPointFront - INTERIOR_GEOM.cushionAboveFloorMin + 1e-9)
    }
    // 地板面须低于车身侧裙以下的可视下界（避免地板线画到车底外）
    const P = profileOf('sedan')
    expect(deriveFloorY(P, P.seatHPointFront)).toBeLessThan(P.beltLineY)
  })
})

describe('布置图几何合法性：所有元素落在车身包络内', () => {
  it.each(ALL_TYPES)('%s 座椅/仪表台/中控/门板均在车身 X-Y 范围内', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    for (const row of L.rows) {
      const env = envelopeBox(row.envelope)
      expect(env.minX).toBeGreaterThan(P.rearX)
      expect(env.maxX).toBeLessThan(P.frontX)
      expect(env.minY).toBeGreaterThan(0)
      expect(env.maxY).toBeLessThan(P.roofTopY)
    }
    expect(L.ip.frontX).toBeLessThan(P.frontX)
    expect(L.ip.bottomY).toBeGreaterThan(L.floorY)
    expect(L.doorPanel.x0).toBeGreaterThan(P.rearX)
    expect(L.doorPanel.x1).toBeLessThan(P.frontX)
    expect(L.doorPanel.y1).toBeLessThan(P.beltLineY)
  })

  it.each(ALL_TYPES)('%s 座椅不与仪表台/车尾后围互穿', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    for (const row of L.rows) {
      // 坐垫前缘必须在仪表板面之后（膝部空间为正）
      expect(row.envelope.cushion.x1).toBeLessThanOrEqual(L.ip.rearX + 1e-9)
      // 靠背顶不得越过座舱后界
      const backTop = row.envelope.backrest.points.map((p) => p[0])
      expect(Math.min(...backTop)).toBeGreaterThan(P.rearX)
    }
  })
})

// ============================================================================
// 右视图（A-A 横断面 Z-Y）：补齐侧视缺失的横向投影，证明中控台与座椅不重叠
// ============================================================================
describe('横断面右视图 — 中控台与座椅的横向关系（6 车型全量）', () => {
  it.each(ALL_TYPES)('%s 前排双座与中控台之间存在真实净距（≥ 设计净距）', (type) => {
    const S = deriveSectionLayout(profileOf(type))
    expect(S.metrics.seatToConsoleGap).not.toBeNull()
    // 净距不得小于座-中控设计净距（旧算法两座间距仅 0.126m，中控 0.20m 必然相撞）
    expect(S.metrics.seatToConsoleGap).toBeGreaterThanOrEqual(INTERIOR_GEOM.seatToConsoleClearance - 1e-9)
    // 逐座显式断言：任何一座的内缘都不得进入中控台的 Z 区间（含净距带）
    for (const s of S.rows[0].seats) {
      if (s.z0 > S.console.z1) expect(s.z0 - S.console.z1).toBeGreaterThanOrEqual(INTERIOR_GEOM.seatToConsoleClearance - 1e-9)
      else if (s.z1 < S.console.z0) expect(S.console.z0 - s.z1).toBeGreaterThanOrEqual(INTERIOR_GEOM.seatToConsoleClearance - 1e-9)
      else throw new Error(`${type} 座椅与中控台重叠：seat[${s.z0}, ${s.z1}] vs console[${S.console.z0}, ${S.console.z1}]`)
    }
  })

  it.each(ALL_TYPES)('%s 中控台宽度/位置与常量同源，且座椅不越出门内壁', (type) => {
    const S = deriveSectionLayout(profileOf(type))
    expect(S.metrics.consoleWidth).toBe(INTERIOR_GEOM.consoleWidth)
    expect(S.console.z1 - S.console.z0).toBeCloseTo(INTERIOR_GEOM.consoleWidth, 12)
    // 中控台不得宽过座舱
    expect(S.console.z1).toBeLessThan(S.halfInterior)
    // 座椅外缘到门内壁留净距，且绝不越出内壁
    expect(S.metrics.seatToTrimGap).toBeGreaterThanOrEqual(INTERIOR_GEOM.seatToWallClearance - 1e-9)
    for (const row of S.rows) {
      for (const s of row.seats) {
        expect(Math.abs(s.z0)).toBeLessThan(S.halfInterior)
        expect(Math.abs(s.z1)).toBeLessThan(S.halfInterior)
      }
    }
  })

  it.each(ALL_TYPES)('%s 断面 Y 值与侧视布置图逐值同源（不做二次推导）', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const S = deriveSectionLayout(P)
    expect(S.floorY).toBe(L.floorY)
    expect(S.console.topY).toBe(L.console.topY)
    expect(S.console.bottomY).toBe(L.console.bottomY)
    expect(S.console.topY).toBeLessThan(S.rows[0].hPointY)
    expect(S.door.armrestY).toBe(L.doorPanel.armrestY)
    expect(S.beltLineY).toBe(P.beltLineY)
    expect(S.roofTopY).toBe(P.roofTopY)
    L.rows.forEach((r, i) => {
      expect(S.rows[i].hPointY).toBe(r.hPointY)
      expect(S.rows[i].cushionY0).toBe(r.envelope.cushion.y0)
      expect(S.rows[i].headrestTopY).toBe(r.envelope.topY)
      expect(S.rows[i].seatWidth).toBe(r.seat.width)
      expect(S.rows[i].seats.map((s) => s.z)).toEqual(r.seat.centers)
    })
  })

  it.each(ALL_TYPES)('%s 3D 座椅 Z 包络与断面 z0/z1 一致（同一取数口）', (type) => {
    const P = profileOf(type)
    const S = deriveSectionLayout(P)
    const tol = 0.02   // 倒角 0.012 + 数值余量
    for (const row of S.rows) {
      const seats = seatGroupsOf(createSeatRow(P, row.row))
      row.seats.forEach((sec, i) => {
        const box = coreSeatBox(seats[i])
        expect(box.min.z).toBeGreaterThanOrEqual(sec.z0 - tol)
        expect(box.max.z).toBeLessThanOrEqual(sec.z1 + tol)
      })
    }
  })

  it.each(ALL_TYPES)('%s 断面像素可反解回 3D 米（横向投影零漂移）', (type) => {
    const S = deriveSectionLayout(profileOf(type))
    const pxPerM = 61.3
    const groundY = 366
    const centerX = 250 / 2
    const proj = createFrontViewProjection(centerX, groundY, pxPerM)

    const roundTrip = (z, y) => {
      expect(proj.fromX(proj.toX(z))).toBeCloseTo(z, 9)
      expect(proj.fromY(proj.toY(y))).toBeCloseTo(y, 9)
    }
    // Z+（副驾侧）在画面左侧：z 为正 → x 小于中心；z 为负（驾驶侧）→ x 大于中心
    expect(proj.toX(0.5)).toBeLessThan(centerX)
    expect(proj.toX(-0.5)).toBeGreaterThan(centerX)

    roundTrip(S.console.z0, S.console.topY)
    roundTrip(S.rows[0].seats[0].z0, S.rows[0].hPointY)
    const rect = proj.rect(S.console.z0, S.console.z1, S.console.bottomY, S.console.topY)
    expect(proj.fromX(rect.x)).toBeCloseTo(S.console.z1, 9)
    expect(proj.fromX(rect.x + rect.w)).toBeCloseTo(S.console.z0, 9)
    expect(rect.w).toBeCloseTo(INTERIOR_GEOM.consoleWidth * pxPerM, 9)
    expect(rect.h).toBeCloseTo((S.console.topY - S.console.bottomY) * pxPerM, 9)
  })

  it('三座长排座椅连续（无虚伪缝），双座横向中心左右对称', () => {
    for (const type of ALL_TYPES) {
      const P = profileOf(type)
      const L = deriveInteriorLayout(P)
      for (const row of L.rows) {
        if (row.count >= 3) {
          // 相邻长椅座边缘相接（容差 1e-9），共同构成一条通铺
          expect(row.seat.centers[1] - row.seat.centers[0]).toBeCloseTo(row.seat.width, 9)
          expect(row.seat.centers[2] - row.seat.centers[1]).toBeCloseTo(row.seat.width, 9)
        } else {
          expect(row.seat.centers[0]).toBeCloseTo(-row.seat.centers[1], 12)
        }
      }
    }
  })

  it('方向盘横断面 Z 与 3D 同源（落在驾驶座中心线上，Z<0）', () => {
    for (const type of ALL_TYPES) {
      const P = profileOf(type)
      const S = deriveSectionLayout(P)
      const L = deriveInteriorLayout(P)
      expect(S.steerWheel.z).toBe(L.steerWheel.z)
      // 方向盘中心 = 前排左座（驾驶侧）中心线：不得外偏到门内壁/轮拱
      expect(S.steerWheel.z).toBeCloseTo(L.rows[0].seat.centers[0], 12)
      expect(S.steerWheel.z).toBeLessThan(0)
    }
  })

  it('断面纯函数：同参数两次调用逐字段相等', () => {
    const P = profileOf('mpv')
    expect(JSON.stringify(deriveSectionLayout(P))).toBe(JSON.stringify(deriveSectionLayout(P)))
  })
})

// ============================================================================
// E 组：座椅纵向基准 —— 以门洞为锚点（修复「座椅整体压在前门洞前缘」）
// ============================================================================
describe('座椅纵向基准 — 门洞锚定与人机工程封顶（6 车型全量）', () => {
  it.each(ALL_TYPES)('%s 前排坐垫整体落在前门洞内，前后均留出上下车通行区', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const A = deriveDoorAperturesX(P)
    const G = INTERIOR_GEOM
    // 前排 H 点 = 门洞锚点（或短头车型的膝部封顶）
    expect(L.rows[0].x).toBe(deriveFrontRowX(P))
    // 坐垫前缘 → 前门洞前缘 ≥ 160mm：乘员上车有落脚区
    expect(L.metrics.entryClearance).toBeGreaterThanOrEqual(G.seatEntryClearance - 1e-9)
    // 坐垫后端仍在门洞内（不得整块缩到 B 柱之前）
    expect(L.rows[0].x - G.cushionFrontOffset).toBeGreaterThan(A.midSeamX)
    // 靠背后缘（含后倾）不得侵入 B 柱
    expect(L.metrics.bPillarGap).toBeGreaterThanOrEqual(0.02)
  })

  it.each(ALL_TYPES)('%s 方向盘 X 由前排 H 点派生（不得反向定义座椅位置）', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    expect(L.steerWheel.x).toBe(steerWheelX(P))
    expect(steerWheelX(P) - deriveFrontRowX(P)).toBeCloseTo(INTERIOR_GEOM.steerWheelToHPoint, 12)
    expect(L.metrics.hPointToWheel).toBeCloseTo(INTERIOR_GEOM.steerWheelToHPoint, 12)
  })

  it.each(ALL_TYPES)('%s 靠背倾角按车型解析，2D 包络与 3D 枢轴同值', (type) => {
    const P = profileOf(type)
    const lean = seatBackLean(P)
    expect(lean).toBe(SEAT_BACK_LEAN_BY_TYPE[type])
    expect(deriveInteriorLayout(P).metrics.backLean).toBe(lean)
    for (const seat of seatGroupsOf(createSeatRow(P, 1))) {
      const pivot = seat.children.find((c) => c.name === 'seat-backrest-pivot')
      expect(pivot).toBeTruthy()
      expect(pivot.rotation.z).toBeCloseTo(lean, 12)
    }
  })

  it.each(ALL_TYPES)('%s 有后门洞时后排 H 点落在后门洞内、坐垫不顶 B 柱', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const A = deriveDoorAperturesX(P)
    if (!A.rear || L.rows.length < 2) return
    expect(L.rows[1].x).toBeGreaterThan(A.rear.x0)
    expect(L.rows[1].x).toBeLessThan(A.rear.x1)
    expect(L.metrics.rearCushionToBPillar).toBeGreaterThanOrEqual(INTERIOR_GEOM.rearCushionGapToBPillar - 1e-9)
  })

  it('双门车无后门洞：后排按排距后移，且与后排间距不小于最小排距', () => {
    const P = profileOf('coupe')
    const L = deriveInteriorLayout(P)
    expect(deriveDoorAperturesX(P).rear).toBeNull()
    expect(L.rows[0].x - L.rows[1].x).toBeGreaterThanOrEqual(INTERIOR_GEOM.minRowPitch - 1e-9)
  })

  it('皮卡后排整排留在驾驶室内（靠背/头枕不越后壁）', () => {
    const P = profileOf('pickup')
    const row2 = deriveRowPlacement(P, 2)
    // 后移量按侧视包络外扩量（靠背后倾 + 头枕 ≈0.365m）定值，留 35mm 余量
    expect(row2.x).toBeCloseTo(P.pickup.cabRearX + 0.40, 12)
    expect(row2.x).toBeGreaterThan(P.pickup.cabRearX)
    // 穿模门禁：包络后缘（靠背 + 头枕）不得越过驾驶室后壁
    const env = deriveInteriorLayout(P).rows[1].envelope
    const rearMost = Math.min(
      ...env.backrest.points.map((p) => p[0]),
      ...env.headrest.points.map((p) => p[0])
    )
    expect(rearMost).toBeGreaterThan(P.pickup.cabRearX - 0.02)
  })

  it.each(ALL_TYPES)('%s 相邻排纵向间距 ≥ 最小排距，且不越出座舱后界', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    for (let i = 1; i < L.rows.length; i++) {
      expect(L.rows[i - 1].x - L.rows[i].x).toBeGreaterThanOrEqual(INTERIOR_GEOM.minRowPitch - 1e-9)
    }
  })
})

// ============================================================================
// F 组：剩余内饰件（门板内饰 / 中央通道 / 顶棚 / 地毯 / 安全带固定点）
// ============================================================================
describe('剩余内饰件 — 舱内边界与座椅无干涉（6 车型全量）', () => {
  it.each(ALL_TYPES)('%s 地毯 / 顶棚 / 中央通道几何落在座舱内且不压座椅', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const T = deriveInteriorTrim(P)
    const G = INTERIOR_GEOM

    // 地毯：铺满地板面（10mm 厚），后端到座舱后界、前端到仪表台前缘
    expect(T.carpet.x1).toBe(L.ip.frontX)
    expect(T.carpet.y0).toBe(L.floorY)
    expect(T.carpet.y1 - T.carpet.y0).toBeCloseTo(G.carpetThickness, 12)
    expect(T.carpet.halfZ).toBeLessThanOrEqual(T.halfInterior)
    expect(T.carpet.x0).toBeGreaterThan(P.rearX)
    for (const r of L.rows) expect(T.carpet.y1).toBeLessThanOrEqual(r.envelope.cushion.y0)

    // 顶棚：车顶内表面（-20mm），半宽内缩避让侧窗，且不得压任何一排头枕
    expect(T.headliner.y0).toBeCloseTo(P.roofTopY - G.headlinerThickness, 12)
    expect(T.headliner.halfZ).toBeCloseTo(T.halfInterior - G.headlinerZInset, 12)
    expect(T.headliner.x0).toBeLessThan(T.headliner.x1)
    expect(T.headliner.x0).toBeGreaterThan(P.rearX)
    expect(T.headliner.x1).toBeLessThan(P.frontX)
    const topSeat = Math.max(...L.rows.map((r) => r.envelope.topY))
    expect(T.headliner.y0 - topSeat).toBeGreaterThanOrEqual(0.03)

    // 中央通道：前排本体贴中控台，后排低通道不侵入座椅 Z 区间、不顶坐垫
    expect(T.tunnel.halfZ).toBeCloseTo(G.consoleWidth / 2, 12)
    expect(T.tunnel.console.x0).toBe(L.console.rearX)
    expect(T.tunnel.console.x1).toBe(L.console.frontX)
    const innerSeat = Math.min(...L.rows[0].seat.centers.map((z) => Math.abs(z))) - L.rows[0].seat.width / 2
    expect(T.tunnel.halfZ).toBeLessThan(innerSeat)
    expect(T.tunnel.rear.y1 - T.tunnel.rear.y0).toBeCloseTo(G.tunnelRearHeight, 12)
    const lastRow = L.rows[L.rows.length - 1]
    expect(T.tunnel.rear.y1).toBeLessThanOrEqual(lastRow.envelope.cushion.y0 + 0.002)
    expect(T.tunnel.rear.x0).toBeLessThan(T.tunnel.rear.x1)
  })

  it.each(ALL_TYPES)('%s 门板内饰贴合门洞、扶手内凸且与座椅留净距', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const T = deriveInteriorTrim(P)
    const A = deriveDoorAperturesX(P)
    const G = INTERIOR_GEOM
    const expected = (A.front ? 2 : 0) + (A.rear ? 2 : 0)
    expect(T.doors.length).toBe(expected)
    expect(T.armrests.length).toBe(expected)
    for (const d of T.doors) {
      const ap = d.key === 'front' ? A.front : A.rear
      expect(d.x0).toBeGreaterThanOrEqual(ap.x0)
      expect(d.x1).toBeLessThanOrEqual(ap.x1)
      expect(d.y0).toBeGreaterThanOrEqual(L.floorY)
      expect(d.y1).toBeLessThanOrEqual(T.beltLineY)
      expect(Math.max(Math.abs(d.z0), Math.abs(d.z1))).toBeCloseTo(T.halfInterior, 12)
      expect(Math.abs(d.z1 - d.z0)).toBeCloseTo(G.doorTrimThickness, 12)
    }
    // 扶手内表面向舱内凸 60mm，且与座椅最外缘保留净距（不得顶住座椅）
    for (const a of T.armrests) {
      expect(Math.min(Math.abs(a.z0), Math.abs(a.z1))).toBeCloseTo(T.halfInterior - G.armrestDepthInward, 12)
    }
    const seatOuter = Math.max(...L.rows[0].seat.centers.map((z) => Math.abs(z))) + L.rows[0].seat.width / 2
    expect(T.halfInterior - G.armrestDepthInward - seatOuter).toBeGreaterThanOrEqual(0.03)
  })

  it.each(ALL_TYPES)('%s 安全带固定点：上固定点柱侧高度、下固定点地板侧', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const T = deriveInteriorTrim(P)
    const G = INTERIOR_GEOM
    expect(T.belts.length).toBe(L.rows.length * 4)   // 每排 × 两侧 × 上/下
    for (const b of T.belts) {
      const row = L.rows.find((r) => r.row === b.row)
      // 固定点贴门内壁；该排若因轮罩收窄，固定点跟随座椅外缘（不得落进轮腔）
      const expectZ = row.seat.halfUsable < T.halfInterior
        ? row.seat.halfUsable - 0.02
        : T.halfInterior - G.seatBeltAnchorInset
      expect(Math.abs(b.z)).toBeCloseTo(expectZ, 12)
      if (b.kind === 'upper') {
        expect(b.y).toBeGreaterThanOrEqual(T.beltLineY - 1e-9)
        expect(b.y).toBeLessThanOrEqual(P.roofTopY - 0.12 + 1e-9)
      } else {
        expect(b.y).toBeCloseTo(T.floorY + 0.10, 12)
      }
      expect(b.x).toBeGreaterThan(P.rearX)
      expect(b.x).toBeLessThan(P.frontX)
    }
  })
})

describe('剩余内饰件 3D 网格 — 与布置层逐值同源（无第二套数值）', () => {
  it.each(ALL_TYPES)('%s createInteriorTrim 子件齐全、位置尺寸取自 deriveInteriorTrim', (type) => {
    const P = profileOf(type)
    const T = deriveInteriorTrim(P)
    const group = createInteriorTrim(P)
    expect(group.name).toBe('interior-trim')
    const byName = (n) => group.children.find((c) => c.name === n)

    // 地毯按轮拱区间分段渲染：每段一个网格，段首尾相接、无缺料、无越界段
    const spans = T.carpet.spans
    expect(spans.length).toBeGreaterThan(0)
    expect(spans[0].x0).toBeCloseTo(T.carpet.x0, 12)
    expect(spans[spans.length - 1].x1).toBeCloseTo(T.carpet.x1, 12)
    for (let i = 0; i < spans.length; i++) {
      if (i > 0) expect(spans[i].x0).toBeCloseTo(spans[i - 1].x1, 12)
      const m = byName(`carpet-${i}`)
      expect(m).toBeTruthy()
      expect(m.position.x).toBeCloseTo((spans[i].x0 + spans[i].x1) / 2, 12)
      expect(m.position.y).toBeCloseTo((T.carpet.y0 + T.carpet.y1) / 2, 12)
      expect(m.position.z).toBeCloseTo(0, 12)
      expect(m.geometry.parameters.width).toBeCloseTo(spans[i].x1 - spans[i].x0, 12)
      expect(m.geometry.parameters.height).toBeCloseTo(T.carpet.y1 - T.carpet.y0, 12)
      expect(m.geometry.parameters.depth).toBeCloseTo(spans[i].halfZ * 2, 12)
    }

    const headliner = byName('headliner')
    expect(headliner.geometry.parameters.depth).toBeCloseTo(T.headliner.halfZ * 2, 12)
    expect(headliner.geometry.parameters.height).toBeCloseTo(T.headliner.y1 - T.headliner.y0, 12)

    const tunnelConsole = byName('tunnel-console')
    expect(tunnelConsole.geometry.parameters.width).toBeCloseTo(T.tunnel.console.x1 - T.tunnel.console.x0, 12)
    const tunnelRear = byName('tunnel-rear')
    expect(tunnelRear.geometry.parameters.height).toBeCloseTo(INTERIOR_GEOM.tunnelRearHeight, 12)

    for (const d of T.doors) {
      const m = byName(`door-trim-${d.key}-${d.side < 0 ? 'left' : 'right'}`)
      expect(m).toBeTruthy()
      expect(m.geometry.parameters.depth).toBeCloseTo(INTERIOR_GEOM.doorTrimThickness, 12)
      expect(m.position.z).toBeCloseTo((d.z0 + d.z1) / 2, 12)
    }
    for (const a of T.armrests) {
      expect(byName(`door-armrest-${a.key}-${a.side < 0 ? 'left' : 'right'}`)).toBeTruthy()
    }
    for (const b of T.belts) {
      const m = byName(`seatbelt-${b.kind}-r${b.row}-${b.side < 0 ? 'left' : 'right'}`)
      expect(m).toBeTruthy()
      expect(m.position.x).toBeCloseTo(b.x, 12)
      expect(m.position.y).toBeCloseTo(b.y, 12)
      expect(m.position.z).toBeCloseTo(b.z, 12)
    }

    // 阴影/渲染契约：内饰件不投影、接收阴影，与座椅同一渲染序
    let meshCount = 0
    group.traverse((o) => {
      if (!o.isMesh) return
      meshCount++
      expect(o.castShadow).toBe(false)
      expect(o.receiveShadow).toBe(true)
      expect(o.renderOrder).toBe(2)
      expect(o.userData.noCastShadow).toBe(true)
    })
    expect(meshCount).toBe(T.carpet.spans.length + 3 + T.doors.length + T.armrests.length + T.belts.length)
  })
})

// ============================================================================
// G 组：滑轨全行程安全约束（R-01~R-03 整改：有效行程由布置几何联动收窄）
//   判据来源：验收报告 R-01 suv 最后端靠背侵 B 柱 −105mm、
//             R-02 coupe/sport 最前端膝部顶仪表板 −70mm、R-03 sedan 后端余量仅 4mm。
//   整改后不变式：任何车型滑轨任一端点余量都 ≥ seatTravelMargin（10mm）。
// ============================================================================
describe('滑轨全行程（G 组）— 有效行程由布置几何联动收窄，端点余量 ≥ 10mm', () => {
  const MARGIN = INTERIOR_GEOM.seatTravelMargin

  it.each(ALL_TYPES)('%s travel 结构完备：fwd/aft ≤ 半行程，effective = fwd + aft', (type) => {
    const t = deriveSeatTrackTravel(profileOf(type))
    expect(t).toBeTruthy()
    expect(t.design).toBeGreaterThan(0)
    expect(t.half).toBeCloseTo(t.design / 2, 12)
    expect(t.fwd).toBeGreaterThanOrEqual(0)
    expect(t.aft).toBeGreaterThanOrEqual(0)
    expect(t.fwd).toBeLessThanOrEqual(t.half + 1e-12)
    expect(t.aft).toBeLessThanOrEqual(t.half + 1e-12)
    expect(t.effective).toBeCloseTo(t.fwd + t.aft, 12)
    expect(t.margin).toBe(MARGIN)
    expect(t.effective).toBeGreaterThan(0)
  })

  it.each(ALL_TYPES)('%s 滑轨端点余量：最前端膝部、最后端 B 柱均 ≥ 10mm（R-01/R-02/R-03 闭环判据）', (type) => {
    const P = profileOf(type)
    const L = deriveInteriorLayout(P)
    const t = L.travel
    // 最前端：坐垫前缘 → 仪表板面余量 − 前向行程 ≥ 10mm（膝部不得顶护板）
    expect(L.metrics.kneeClearance - t.fwd).toBeGreaterThanOrEqual(MARGIN - 1e-9)
    // 最后端：靠背最后缘 → B 柱前缘余量 − 后向行程 ≥ 10mm（靠背不得侵入 B 柱）
    expect(L.metrics.bPillarGap - t.aft).toBeGreaterThanOrEqual(MARGIN - 1e-9)
  })

  it.each(ALL_TYPES)('%s 收窄标记与有效行程一致：limited ⟺ effective < design', (type) => {
    const t = deriveSeatTrackTravel(profileOf(type))
    expect(t.limited).toBe(t.effective < t.design - 1e-9)
  })

  it('mpv / pickup 在契约设计值下同样需收窄（limited=true）', () => {
    // 轮毂直径按后端契约收窄后，前排纵向空间变小，mpv/pickup 不再能保留全量行程
    const expected = { mpv: 274.6, pickup: 176.5 }
    for (const [type, effMm] of Object.entries(expected)) {
      const t = deriveSeatTrackTravel(profileOf(type))
      expect(t.limited).toBe(true)
      expect(t.effective * 1000).toBeCloseTo(effMm, 0)
    }
  })

  it('sedan 全量行程安全；suv/coupe/sport 全量行程必收窄（limited=true）', () => {
    // 整改验收值（mm）：与当前契约设计值下的布置几何逐一对应
    const expected = { suv: 254.3, coupe: 140.0, sport: 120.0 }
    for (const [type, effMm] of Object.entries(expected)) {
      const t = deriveSeatTrackTravel(profileOf(type))
      expect(t.limited).toBe(true)
      expect(t.effective * 1000).toBeCloseTo(effMm, 0)
    }
    const sedan = deriveSeatTrackTravel(profileOf('sedan'))
    expect(sedan.limited).toBe(false)
    expect(sedan.effective).toBeCloseTo(sedan.design, 12)
  })

  it('R-01 复现性断言：suv 若沿用全量行程，最后端靠背侵入 B 柱（证明收窄必要）', () => {
    // 用历史轮毂直径 760mm 复现原始缺陷（当前契约设计值 600mm 下间隙已增大，不再复现）
    const P = profileOf('suv', { wheel_diameter: 760 })
    const L = deriveInteriorLayout(P)
    const t = L.travel
    // 全量半行程 130mm > 允许后向 14.7mm → 全量最后端余量 = 24.7 − 130 = −105.3mm（侵入）
    expect(L.metrics.bPillarGap - t.half).toBeLessThan(0)
    expect((L.metrics.bPillarGap - t.half) * 1000).toBeCloseTo(-105.3, 0)
    // 整改后后向行程锁 14.7mm，端点余量恰好 = margin
    expect((L.metrics.bPillarGap - t.aft) * 1000).toBeCloseTo(10, 0)
  })

  it('R-02 复现性断言：coupe/sport 若沿用全量行程，最前端膝部顶仪表板（证明收窄必要）', () => {
    for (const [type, expectedMm] of [['coupe', -70.0], ['sport', -70.0]]) {
      const L = layoutOf(type)
      const t = L.travel
      expect(L.metrics.kneeClearance - t.half).toBeLessThan(0)
      expect((L.metrics.kneeClearance - t.half) * 1000).toBeCloseTo(expectedMm, 0)
    }
  })
})
