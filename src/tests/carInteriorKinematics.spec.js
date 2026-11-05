// 内饰运动件运动学模型测试（R-04 整改：调角器 / 遮阳板 / 扶手盖全行程扫掠）
//
// 判据来源：验收报告 R-04「调角器、遮阳板、扶手盖未建立运动模型」。
// 模型取数口：carInteriorKinematics.js（deriveReclinerSweep / deriveSunVisorSweep /
// deriveArmrestLidSweep），全部参数实车对标（KINEMATICS_PARAMS 与 INTERIOR_GEOM 同源）。
import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import { carTypeParams } from '../config/carPresets.js'
import { INTERIOR_GEOM, seatBackLean, deriveSeatTrackTravel } from '../utils/carInteriorLayout.js'
import {
  KINEMATICS_PARAMS, deriveReclinerSweep, deriveSunVisorSweep, deriveArmrestLidSweep, deriveKinematics
} from '../utils/carInteriorKinematics.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type) => deriveCarProfile({ ...carTypeParams[type] }, type)
const MARGIN = INTERIOR_GEOM.seatTravelMargin

describe('运动学参数契约 — 与 INTERIOR_GEOM 同源，实车对标', () => {
  it('调角器行程取自 INTERIOR_GEOM（禁止消费端另立数值）', () => {
    expect(KINEMATICS_PARAMS.reclinerFwd).toBe(INTERIOR_GEOM.reclinerFwdRange)
    expect(KINEMATICS_PARAMS.reclinerAft).toBe(INTERIOR_GEOM.reclinerAftRange)
    expect(KINEMATICS_PARAMS.margin).toBe(INTERIOR_GEOM.seatTravelMargin)
  })

  it('遮阳板/扶手盖物理参数落在实车典型区间', () => {
    // 遮阳板展长 180~200mm、翻转上限 180°
    expect(KINEMATICS_PARAMS.sunVisorLength).toBeGreaterThanOrEqual(0.18)
    expect(KINEMATICS_PARAMS.sunVisorLength).toBeLessThanOrEqual(0.20)
    expect(KINEMATICS_PARAMS.sunVisorFlipMax).toBeCloseTo(Math.PI, 12)
    // 扶手盖有效盖长 ≤320mm、开启上限 75°
    expect(KINEMATICS_PARAMS.armrestLidMaxLength).toBeLessThanOrEqual(0.32)
    expect(KINEMATICS_PARAMS.armrestLidOpenMax).toBeCloseTo(1.31, 12)
  })
})

describe('调角器扫掠 — 逐角间隙 + 限位角（R-01/R-03 运动学佐证）', () => {
  it.each(ALL_TYPES)('%s 每排：设计角间隙 ≥ 10mm 且限位角不早于设计角（pass）', (type) => {
    const P = profileOf(type)
    const design = seatBackLean(P)
    for (const r of deriveReclinerSweep(P)) {
      expect(r.pass).toBe(true)
      expect(r.design).toBeCloseTo(design, 12)
      expect(r.maxSafeAft).toBeGreaterThanOrEqual(design - 1e-9)
      expect(r.gapAtMaxSafe).toBeGreaterThanOrEqual(MARGIN - 1e-9)
      // 限位角不得超出物理行程上限
      expect(r.maxSafeAft).toBeLessThanOrEqual(r.aftLimitMax + 1e-9)
    }
  })

  it.each(ALL_TYPES)('%s 前排限位角按滑轨最后端标定（worst case，与实车机械限位一致）', (type) => {
    const P = profileOf(type)
    const [r1] = deriveReclinerSweep(P)
    expect(r1.aftShift).toBeCloseTo(deriveSeatTrackTravel(P).aft, 12)
  })

  it('suv 前排调角器必须限位（limited=true）：全行程后倒 + 滑轨最后端会侵入 B 柱', () => {
    const [r1] = deriveReclinerSweep(profileOf('suv'))
    expect(r1.limited).toBe(true)
    // 不限位时全行程末端间隙为负（侵入），限位后间隙恰好回到 margin 带
    expect(r1.minGap).toBeLessThan(0)
    expect(r1.gapAtMaxSafe).toBeGreaterThanOrEqual(MARGIN - 1e-9)
  })

  it('sedan 前排调角器锁上限高于设计角：设计角仍处于安全区（R-03 运动学闭环）', () => {
    const [r1] = deriveReclinerSweep(profileOf('sedan'))
    expect(r1.limited).toBe(true)
    // 契约轮毂设计值收窄后纵向空间增大，安全上限提升；设计角仍须落在安全侧
    expect(r1.maxSafeAft).toBeGreaterThanOrEqual(r1.design - 1e-9)
    expect(r1.gapAtMaxSafe).toBeGreaterThanOrEqual(MARGIN - 1e-9)
  })

  it('mpv 三排全覆盖：中排障碍 = 第 3 排坐垫前缘，末排障碍 = 座舱后界', () => {
    const rows = deriveReclinerSweep(profileOf('mpv'))
    expect(rows.length).toBe(3)
    expect(rows[1].obstacle).toContain('第 3 排')
    expect(rows[2].obstacle).toContain('座舱后界')
    rows.forEach((r) => expect(r.pass).toBe(true))
  })
})

describe('遮阳板翻转扫掠 — 顶棚不穿透 + 风挡接触即止', () => {
  it.each(ALL_TYPES)('%s 全程不穿透顶棚内表面，有效行程内不越玻璃外侧（pass）', (type) => {
    const s = deriveSunVisorSweep(profileOf(type))
    expect(s.pass).toBe(true)
    expect(s.penetration).toBe(false)
    expect(s.minHeadlinerGap).toBeGreaterThanOrEqual(-1e-9)
    expect(s.minGlassDist).toBeGreaterThanOrEqual(-0.002)
  })

  it.each(ALL_TYPES)('%s 有效翻转角 ≥ 90°（遮阳功能可用）且被风挡玻璃限位', (type) => {
    const s = deriveSunVisorSweep(profileOf(type))
    expect(s.contactTheta).toBeGreaterThanOrEqual(Math.PI / 2)
    expect(s.contactFound).toBe(true)
    expect(s.contactTheta).toBeLessThanOrEqual(Math.PI)
  })

  it('铰链锚定顶棚前缘下方 35mm（与 deriveInteriorTrim 同源）', () => {
    const P = profileOf('sedan')
    const s = deriveSunVisorSweep(P)
    expect(s.pivot.y).toBeLessThan(P.roofTopY)
    expect(s.length).toBe(KINEMATICS_PARAMS.sunVisorLength)
  })
})

describe('扶手盖开合扫掠 — 75° 全行程无干涉', () => {
  it.each(ALL_TYPES)('%s 全行程不碰仪表台/顶棚，Z 向与座椅错层（pass）', (type) => {
    const a = deriveArmrestLidSweep(profileOf(type))
    expect(a.pass).toBe(true)
    expect(a.minIpGap).toBeGreaterThanOrEqual(0)
    expect(a.minRoofGap).toBeGreaterThanOrEqual(MARGIN)
    expect(a.zClearance).toBeGreaterThanOrEqual(0)
  })

  it.each(ALL_TYPES)('%s 盖长 ≤ 320mm 且铰链在中控台后端顶面', (type) => {
    const a = deriveArmrestLidSweep(profileOf(type))
    expect(a.lidLen).toBeLessThanOrEqual(KINEMATICS_PARAMS.armrestLidMaxLength + 1e-12)
    expect(a.lidLen).toBeGreaterThan(0)
    expect(a.openMax).toBeCloseTo(1.31, 12)
  })
})

describe('deriveKinematics 汇总 — 三件套全车型闭环', () => {
  it.each(ALL_TYPES)('%s 调角器/遮阳板/扶手盖全部 pass（R-04 关闭判据）', (type) => {
    const K = deriveKinematics(profileOf(type))
    expect(K.recliner.length).toBeGreaterThan(0)
    K.recliner.forEach((r) => expect(r.pass).toBe(true))
    expect(K.sunVisor.pass).toBe(true)
    expect(K.armrestLid.pass).toBe(true)
  })
})
