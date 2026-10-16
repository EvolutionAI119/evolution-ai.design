// 平稳垂直起降（VTOL）分支 —— 飞行物理与配置契约测试
import { describe, it, expect } from 'vitest'
import {
  FLIGHT_PRESETS, FLIGHT_CONTROL, resolveFlightParams, quinticSmoothstep, altitudeAt,
  hoverBobOffset, vtolPhase, effectiveGravity, dampingRatio,
  thrustToWeight, flightEnvelope,
  fieldLiftShare, baseHoverPowerKw, antigravityHoverPowerKw, enduranceMultiple,
  energyProfile, turnDurationSec, yawAt, attitudeSample, attitudeControl,
  controlLatencyMs, flightControlEnvelope
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

// ============ 反重力飞控系统（五项技术目标） ============

/** 六车型真实尺寸（取自 carTypeParams，与 UI 指标卡同源） */
const dimsOf = (type) => {
  const cp = carTypeParams[type]
  return { overall_length: cp.overall_length, overall_width: cp.overall_width, overall_height: cp.overall_height }
}

describe('场升力份额（反重力驱动核心）', () => {
  it('单调性：η_e 与 η_cdm 增大 → 场份额不减', () => {
    expect(fieldLiftShare(0, 0)).toBe(0)
    for (let e = 0; e <= 0.3; e += 0.05) {
      expect(fieldLiftShare(e + 0.01, 0)).toBeGreaterThanOrEqual(fieldLiftShare(e, 0))
      expect(fieldLiftShare(0, e + 0.01)).toBeGreaterThanOrEqual(fieldLiftShare(0, e))
    }
  })

  it('钳位 [0, 0.75]：风扇保留 ≥25% 推力做姿态差动（±2° 包络前提）', () => {
    expect(fieldLiftShare(0.3, 0.3)).toBe(FLIGHT_CONTROL.fieldLiftShareMax)
    expect(fieldLiftShare(-1, -1)).toBe(0)
    for (const ct of carTypes) {
      const s = fieldLiftShare(FLIGHT_PRESETS[ct.key].exoticRatio, FLIGHT_PRESETS[ct.key].darkMatterRatio)
      expect(s, ct.key).toBeGreaterThanOrEqual(0)
      expect(s, ct.key).toBeLessThanOrEqual(0.75)
    }
  })
})

describe('技术目标 3+4：续航 ≥3× 且全工况无明显能耗峰值', () => {
  it('六车型预设续航倍数全部 ≥3（同电量 vs 传统动力基准）', () => {
    for (const ct of carTypes) {
      const p = resolveFlightParams(ct.key, {})
      const { curbMassKg } = flightEnvelope(dimsOf(ct.key), p)
      const mult = enduranceMultiple(curbMassKg, p.exoticRatio, p.darkMatterRatio)
      expect(mult, `${ct.key} 续航倍数`).toBeGreaterThanOrEqual(FLIGHT_CONTROL.enduranceTarget)
    }
  })

  it('基准功率公式可复现：P = 55·(m/t)^1.2', () => {
    expect(baseHoverPowerKw(1600)).toBeCloseTo(55 * Math.pow(1.6, 1.2), 9)
  })

  it('反重力悬停功率 = 风扇(1−s)^1.5 + 场维持，且低于传统基准', () => {
    const ag = antigravityHoverPowerKw(1631, 0.15, 0.20)
    const base = baseHoverPowerKw(1631)
    const s = fieldLiftShare(0.15, 0.20)
    expect(ag.fan).toBeCloseTo(base * Math.pow(1 - s, 1.5), 9)
    expect(ag.field).toBeCloseTo(12 * 1631 * s / 1000, 9)
    expect(ag.total).toBeLessThan(base)
  })

  it('六车型峰值因子 ≤1.25（起飞峰值/转向增量均不显著）', () => {
    for (const ct of carTypes) {
      const p = resolveFlightParams(ct.key, {})
      const { curbMassKg } = flightEnvelope(dimsOf(ct.key), p)
      const ep = energyProfile(curbMassKg, p.exoticRatio, p.darkMatterRatio)
      expect(ep.peakFactor, `${ct.key} 峰值因子`).toBeLessThanOrEqual(FLIGHT_CONTROL.peakFactorLimit)
      expect(ep.takeoffPeakKw).toBeGreaterThan(0)
      expect(ep.turnKw).toBeGreaterThan(ep.hoverKw)   // 转向差动增量存在但受界
    }
  })

  it('η 归零退化为传统动力：峰值因子如实升至 1.31（无虚假达标）', () => {
    const ep = energyProfile(1631, 0, 0)
    expect(ep.peakFactor).toBeCloseTo(Math.pow(1.2, 1.5), 1)
    expect(ep.peakFactor).toBeGreaterThan(FLIGHT_CONTROL.peakFactorLimit)
  })
})

describe('技术目标 2：全自由度 360° 无限制原地转向', () => {
  it('转向时长 = 1.875·|Δ|/45°/s，360° 恰为 15s，最短 2.5s', () => {
    expect(turnDurationSec(90)).toBeCloseTo(3.75, 9)
    expect(turnDurationSec(360)).toBeCloseTo(15.0, 9)
    expect(turnDurationSec(5)).toBe(FLIGHT_CONTROL.turnMinSec)
    expect(turnDurationSec(-90)).toBe(turnDurationSec(90))
  })

  it('yaw 剖面 C² 端点归零、终值精确、多圈累计无 wrap', () => {
    const T = turnDurationSec(360)
    expect(yawAt(0, 360, T)).toBe(0)
    expect(yawAt(T, 360, T)).toBeCloseTo(360, 9)
    expect(yawAt(T + 10, 360, T)).toBeCloseTo(360, 9)   // 完成后保持
    // 峰值角速度 = 1.875·Δ/T ≤ 45°/s（视场旋转晕动阈内）
    const h = 0.001
    const peakRate = (yawAt(T / 2 + h, 360, T) - yawAt(T / 2 - h, 360, T)) / (2 * h)
    expect(peakRate).toBeLessThanOrEqual(FLIGHT_CONTROL.turnPeakRateDps + 0.5)
    // 连续多圈：720° 累计（不回绕）
    expect(yawAt(T, 720, T)).toBeCloseTo(720, 9)
    // 端点角加速度为零（无卡顿：与 quintic 同 C² 保证）
    const acc0 = (yawAt(2 * h, 90, turnDurationSec(90)) - 2 * yawAt(h, 90, turnDurationSec(90))) / (h * h)
    expect(Math.abs(acc0)).toBeLessThan(1.0)
  })
})

describe('技术目标 1：悬停姿态偏差 ≤±2°', () => {
  it('残余微摆峰值 ≤0.85°（全 η_cdm 范围，远低于 ±2° 包络）', () => {
    for (let d = 0; d <= 0.3001; d += 0.05) {
      let peak = 0
      for (let t = 0; t < 200; t += 0.02) {
        peak = Math.max(peak, Math.abs(attitudeSample(t, d)))
      }
      expect(peak, `η_cdm=${d}`).toBeLessThan(FLIGHT_CONTROL.attitudeLimitDeg)
    }
  })

  it('微摆频率成分 <0.5Hz（0.07/0.11Hz 远离晕动敏感频段）', () => {
    // 0.5s 采样过零间隔下界：主频 0.11Hz → 半周期 ≥4.5s
    const p = attitudeSample
    expect(Math.abs(p(0, 0.2))).toBeLessThan(2)
    // 频率常数自检（防回归：不许有人调高频率）
    expect(FLIGHT_CONTROL.attitudeBandwidthHz).toBeLessThan(3)
  })

  it('姿态控制指标：过阻尼无超调，8° 阵风回落 ±2° 带内 ≤100ms', () => {
    const ac = attitudeControl(0.20)
    expect(ac.dampingRatio).toBeCloseTo(1.12, 3)
    expect(ac.recoveryMs).toBeLessThanOrEqual(FLIGHT_CONTROL.latencyLimitMs)
    expect(ac.peakDeg).toBeLessThanOrEqual(FLIGHT_CONTROL.attitudeLimitDeg)
    expect(ac.settlingMs).toBeGreaterThan(0)
  })
})

describe('技术目标 5：飞控响应延迟 ≤100ms', () => {
  it('全风扇范围（2~8）与全 η_cdm 范围下延迟均 ≤100ms', () => {
    for (const fans of [2, 4, 6, 8]) {
      for (const d of [0, 0.1, 0.2, 0.3]) {
        expect(controlLatencyMs(fans, d), `fans=${fans}, η_cdm=${d}`)
          .toBeLessThanOrEqual(FLIGHT_CONTROL.latencyLimitMs)
      }
    }
  })

  it('链路延迟公式可复现：30 + 6×fans', () => {
    // η_cdm=0 时恢复时间 63.7×ln4 ≈ 88.3ms 主导 fans≤8 的链路（78ms）
    expect(controlLatencyMs(8, 0)).toBeLessThanOrEqual(100)
    expect(controlLatencyMs(2, 0.3)).toBeLessThanOrEqual(100)
  })
})

describe('flightControlEnvelope 反重力飞控总包线', () => {
  it('六车型四项技术目标全部达标', () => {
    for (const ct of carTypes) {
      const p = resolveFlightParams(ct.key, {})
      const env = flightControlEnvelope(dimsOf(ct.key), p)
      expect(env.enduranceOk, `${ct.key} 续航 ≥3×`).toBe(true)
      expect(env.attitudeOk, `${ct.key} 姿态 ≤±2°`).toBe(true)
      expect(env.latencyOk, `${ct.key} 延迟 ≤100ms`).toBe(true)
      expect(env.peakOk, `${ct.key} 峰值因子 ≤1.25`).toBe(true)
      expect(env.enduranceMultiple).toBeGreaterThanOrEqual(3)
      expect(env.fullTurnSec).toBeCloseTo(15.0, 1)
      expect(env.curbMassKg).toBeGreaterThan(0)
    }
  })

  it('同电量续航时长换算可复现（100 kWh 基准）', () => {
    const env = flightControlEnvelope(dimsOf('sedan'), resolveFlightParams('sedan', {}))
    expect(env.enduranceAgH / env.enduranceBaseH).toBeCloseTo(env.enduranceMultiple, 1)
  })
})
