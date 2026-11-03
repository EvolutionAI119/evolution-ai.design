// 人机工程验证断言（评审整改闭环：A-1 悬挑刚度 / B-2 眼椭圆遮罩 / B-3 头部空间 / A-2 扶手盖）
//
// 数据源：carErgoVerification.js（消费 deriveInteriorLayout / deriveIpConsoleLayout / deriveInteriorTrim）
// 判定基线：
//   悬挑刚度  —— MOUNT_SPEC 限值（位移 0.5mm / 偏载 1.0mm / 一阶频率 50Hz）
//   眼椭圆    —— SAE J941 95th 侧视简化模型，可见率分车型阈值（轿跑/跑车低顶为设计偏离项，设回归下限）
//   头部空间  —— GB/T 10000 坐姿头高三体型 + 50mm 运动包络；家用车型 5F/50M 强制，轿跑/跑车 5F 强制、
//               50M/95M 为设计偏离（设回归下限防恶化，整改走顶棚沉坑/座高下调路径）

import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import {
  deriveDisplayMountCheck,
  deriveClusterOcclusion,
  deriveHeadroomCheck,
  MOUNT_SPEC
} from '../utils/carErgoVerification.js'
import { carTypeParams } from '../config/carPresets.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type) => deriveCarProfile(carTypeParams[type], type)

// J941 可见率阈值（当前实测：sedan 76.2 / suv 100 / coupe 61.9 / sport 57.1 / mpv 100 / pickup 100 %）
const OCCLUSION_MIN = { sedan: 0.75, suv: 0.99, coupe: 0.60, sport: 0.55, mpv: 0.99, pickup: 0.99 }
// 头部空间强制线：全车型 5F ≥10mm；家用车型 50M ≥10mm
const FAMILY_TYPES = ['sedan', 'suv', 'mpv', 'pickup']
// 设计偏离回归下限（当前实测：coupe 50M -10/0、95M -70/-60；sport 50M -40、95M -100；sedan 95M -50/-40 mm）
const DEVIATION_FLOOR = {
  sedan: { male95: -0.06 },
  coupe: { male50: -0.02, male95: -0.08 },
  sport: { male50: -0.05, male95: -0.11 }
}

describe('悬浮屏悬挑支架刚度（双臂整改方案）— 六车型', () => {
  it.each(ALL_TYPES)('%s 两种备选材料均满足位移/偏载/频率限值', (type) => {
    const res = deriveDisplayMountCheck(profileOf(type))
    for (const [mat, r] of Object.entries(res)) {
      expect(r.armLen, mat).toBeCloseTo(0.04, 9) // 悬臂跨距 = 屏背面 → IP 后面板（探出 60mm 含 20mm 搭接）
      expect(r.deflectionMm, mat).toBeLessThanOrEqual(MOUNT_SPEC.deflectionMax * 1000)
      expect(r.yawEdgeMm, mat).toBeLessThanOrEqual(MOUNT_SPEC.yawDeflectionMax * 1000)
      expect(r.naturalFreqHz, mat).toBeGreaterThanOrEqual(MOUNT_SPEC.naturalFreqMin)
      expect(r.pass, mat).toBe(true)
    }
  })
})

describe('SAE J941 眼椭圆遮罩分析 — 组合仪表可见率', () => {
  it.each(ALL_TYPES)('%s 95th 眼椭圆全体采样点可见率 ≥ 车型阈值', (type) => {
    const occ = deriveClusterOcclusion(profileOf(type))
    // 眼椭圆中心锚定 H 点（可追溯性：断言取数口）
    expect(occ.eyeCy).toBeGreaterThan(0.9)
    expect(occ.minVisibleRatio).toBeGreaterThanOrEqual(OCCLUSION_MIN[type])
    expect(occ.meanVisibleRatio).toBeGreaterThanOrEqual(occ.minVisibleRatio)
  })
})

describe('各排头部空间（三体型 + 运动包络）— 六车型', () => {
  it.each(ALL_TYPES)('%s 5th 女性强制达标', (type) => {
    for (const row of deriveHeadroomCheck(profileOf(type))) {
      expect(row.perType.female5.clearance, `${type} row${row.row}`).toBeGreaterThanOrEqual(0.01)
    }
  })

  it.each(FAMILY_TYPES)('%s 50th 男性强制达标（家用车型）', (type) => {
    for (const row of deriveHeadroomCheck(profileOf(type))) {
      expect(row.perType.male50.clearance, `${type} row${row.row}`).toBeGreaterThanOrEqual(0.01)
    }
  })

  it.each(Object.keys(DEVIATION_FLOOR))('%s 设计偏离项不恶化（回归下限）', (type) => {
    const floors = DEVIATION_FLOOR[type]
    for (const row of deriveHeadroomCheck(profileOf(type))) {
      for (const [k, floor] of Object.entries(floors)) {
        expect(row.perType[k].clearance, `${type} row${row.row} ${k}`).toBeGreaterThanOrEqual(floor)
      }
    }
  })
})
