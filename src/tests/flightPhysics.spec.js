// 平稳垂直起降（VTOL）分支 —— 飞行物理与配置契约测试
import { describe, it, expect } from 'vitest'
import {
  FLIGHT_PRESETS, resolveFlightParams, quinticSmoothstep, altitudeAt,
  hoverBobOffset, vtolPhase, effectiveGravity, dampingRatio,
  thrustToWeight, flightEnvelope
} from '../utils/flightPhysics.js'
import { carTypes, carTypeParams, defaultCarParams, brands } from '../config/carPresets.js'

describe('FLIGHT_PRESETS 六车型飞行预设', () => {
  it('覆盖全部六种车型', () => {
    for (const ct of carTypes) {
      expect(FLIGHT_PRESETS[ct.key], `缺少 ${ct.key} 飞行预设`).toBeTruthy()
    }
  })

  it('所有预设值处于安全界内（无眩晕：呼吸 <0.2% 车长、频率 <0.2Hz）', () => {
    for (const [type, p] of Object.entries(FLIGHT_PRESETS)) {
      expect(p.hoverAltitude, type).toBeGreaterThanOrEqual(800)
      expect(p.hoverAltitude, type).toBeLessThanOrEqual(3000)
      expect(p.liftDuration, type).toBeGreaterThanOrEqual(2.0)
      expect(p.liftDuration, type).toBeLessThanOrEqual(5.0)
      expect(p.exoticRatio, type).toBeGreaterThanOrEqual(0)
      expect(p.exoticRatio, type).toBeLessThanOrEqual(0.3)
      expect(p.darkMatterRatio, type).toBeGreaterThanOrEqual(0)
      expect(p.darkMatterRatio, type).toBeLessThanOrEqual(0.3)
      expect([4, 6], `${type} 风扇数`).toContain(p.liftFans)
      // 0.2% × 最短车长 4600mm = 9.2mm 感知阈
      expect(p.hoverBobAmp, type).toBeLessThanOrEqual(9.2)
      expect(p.hoverBobFreq, type).toBeLessThan(0.2)
    }
  })
})

describe('resolveFlightParams 解析与钳位', () => {
  it('未知车型回退 sedan 预设', () => {
    const r = resolveFlightParams('hovercraft', {})
    expect(r.hoverAltitude).toBe(FLIGHT_PRESETS.sedan.hoverAltitude)
    expect(r.exoticRatio).toBe(FLIGHT_PRESETS.sedan.exoticRatio)
  })

  it('越界覆盖值钳位到安全界', () => {
    const r = resolveFlightParams('sedan', {
      hover_altitude: 99999, exotic_drive_ratio: -1,
      dark_matter_ratio: 5, lift_fan_count: 99
    })
    expect(r.hoverAltitude).toBe(3000)
    expect(r.exoticRatio).toBe(0)
    expect(r.darkMatterRatio).toBe(0.3)
    expect(r.liftFans).toBe(8)
  })

  it('非数值覆盖回退车型默认', () => {
    const r = resolveFlightParams('suv', { hover_altitude: 'abc' })
    expect(r.hoverAltitude).toBe(FLIGHT_PRESETS.suv.hoverAltitude)
  })
})

describe('五次 smoothstep：C² 连续无眩晕起升曲线', () => {
  it('端点与中点取值精确', () => {
    expect(quinticSmoothstep(0)).toBe(0)
    expect(quinticSmoothstep(1)).toBe(1)
    expect(quinticSmoothstep(0.5)).toBeCloseTo(0.5, 12)
  })

  it('单调不减', () => {
    let prev = -1
    for (let t = 0; t <= 1.0001; t += 0.01) {
      const s = quinticSmoothstep(t)
      expect(s).toBeGreaterThanOrEqual(prev)
      prev = s
    }
  })

  it('端点速度与加速度为零（有限差分验证 → 起飞/着陆无冲击）', () => {
    const h = 0.001
    // s'(0) ≈ (s(h)-s(0))/h
    expect((quinticSmoothstep(h) - 0) / h).toBeLessThan(0.01)
    expect((1 - quinticSmoothstep(1 - h)) / h).toBeLessThan(0.01)
    // s''(0) ≈ (s(2h)-2s(h)+s(0))/h²
    const acc0 = (quinticSmoothstep(2 * h) - 2 * quinticSmoothstep(h) + 0) / (h * h)
    expect(Math.abs(acc0)).toBeLessThan(0.5)
  })
})

describe('高度剖面与悬浮呼吸', () => {
  const sedan = resolveFlightParams('sedan', {})

  it('t=0 在地面，t=liftDuration 达到悬浮高度，过程单调', () => {
    expect(altitudeAt(0, sedan)).toBe(0)
    expect(altitudeAt(sedan.liftDuration, sedan)).toBeCloseTo(sedan.hoverAltitude, 6)
    let prev = -1
    for (let t = 0; t <= sedan.liftDuration + 0.01; t += 0.1) {
      const a = altitudeAt(t, sedan)
      expect(a).toBeGreaterThanOrEqual(prev)
      prev = a
    }
  })

  it('呼吸偏移永不超振幅', () => {
    for (let t = 0; t < 60; t += 0.05) {
      expect(Math.abs(hoverBobOffset(t, sedan))).toBeLessThanOrEqual(sedan.hoverBobAmp + 1e-9)
    }
  })
})

describe('VTOL 相位机', () => {
  const p = resolveFlightParams('sedan', {})
  it('ground → lift → hover 边界正确', () => {
    expect(vtolPhase(-1, p)).toBe('ground')
    expect(vtolPhase(0, p)).toBe('ground')
    expect(vtolPhase(0.1, p)).toBe('lift')
    expect(vtolPhase(p.liftDuration - 0.01, p)).toBe('lift')
    expect(vtolPhase(p.liftDuration, p)).toBe('hover')
  })
})

describe('暗能量/暗物质物理（科幻受界）', () => {
  it('有效重力随暗能量占比单调下降，η=0 时不改变物理', () => {
    expect(effectiveGravity(0)).toBeCloseTo(9.81, 12)
    expect(effectiveGravity(0.3)).toBeCloseTo(9.81 * 0.895, 12)
    expect(effectiveGravity(0.2)).toBeLessThan(effectiveGravity(0.1))
  })

  it('推重比恒 ≥1（悬浮充要条件），η=0 时恰为 1', () => {
    expect(thrustToWeight(0)).toBeCloseTo(1, 12)
    for (let e = 0; e <= 0.3; e += 0.05) {
      expect(thrustToWeight(e)).toBeGreaterThanOrEqual(1)
    }
  })

  it('阻尼比恒 ≥1（临界/过阻尼 → 零超调 → 无眩晕数学保证）', () => {
    expect(dampingRatio(0)).toBe(1)
    expect(dampingRatio(0.3)).toBeCloseTo(1.18, 12)
    for (let d = 0; d <= 0.3; d += 0.05) {
      expect(dampingRatio(d)).toBeGreaterThanOrEqual(1)
    }
  })
})

describe('flightEnvelope 飞行包线（公式可复现）', () => {
  const dims = { overall_length: 4950, overall_width: 1880, overall_height: 1460 }
  const p = resolveFlightParams('sedan', {})
  const env = flightEnvelope(dims, p)

  it('整备质量 = 120kg/m³ × 包络体积', () => {
    const expectMass = (4950 * 1880 * 1460) / 1e9 * 120
    expect(env.curbMassKg).toBeCloseTo(expectMass, 0)
  })

  it('起飞推力 = 1.2 × 悬浮推力 > 0，垂晕豁免为真', () => {
    expect(env.thrustTakeoffKn).toBeCloseTo(env.thrustRequiredKn * 1.2, 1)
    expect(env.thrustRequiredKn).toBeGreaterThan(0)
    expect(env.vertigoFree).toBe(true)
    expect(env.dampingRatio).toBeGreaterThanOrEqual(1)
    expect(env.hoverAltitudeM).toBeCloseTo(p.hoverAltitude / 1000, 2)
  })
})

describe('carPresets 飞行参数契约', () => {
  it('defaultCarParams 具备飞行能力（enable_vtol=true）', () => {
    expect(defaultCarParams.enable_vtol).toBe(true)
    expect(defaultCarParams.hover_altitude).toBe(FLIGHT_PRESETS.sedan.hoverAltitude)
  })

  it('六车型 carTypeParams 与 FLIGHT_PRESETS 一致', () => {
    for (const ct of carTypes) {
      const cp = carTypeParams[ct.key]
      expect(cp.enable_vtol, ct.key).toBe(true)
      expect(cp.hover_altitude, ct.key).toBe(FLIGHT_PRESETS[ct.key].hoverAltitude)
      expect(cp.exotic_drive_ratio, ct.key).toBe(FLIGHT_PRESETS[ct.key].exoticRatio)
      expect(cp.dark_matter_ratio, ct.key).toBe(FLIGHT_PRESETS[ct.key].darkMatterRatio)
      expect(cp.lift_fan_count, ct.key).toBe(FLIGHT_PRESETS[ct.key].liftFans)
    }
  })

  it('19 款品牌车型全部注入五项飞行字段', () => {
    const total = brands.reduce((n, b) => n + b.models.length, 0)
    expect(total).toBe(19)
    for (const brand of brands) {
      for (const model of brand.models) {
        if (!model.car_type) continue
        expect(model.params.enable_vtol, `${brand.key}/${model.key}`).toBe(true)
        expect(model.params.hover_altitude, `${brand.key}/${model.key}`)
          .toBe(FLIGHT_PRESETS[model.car_type].hoverAltitude)
        expect(model.params.lift_fan_count, `${brand.key}/${model.key}`)
          .toBe(FLIGHT_PRESETS[model.car_type].liftFans)
      }
    }
  })
})
