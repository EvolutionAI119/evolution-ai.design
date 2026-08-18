/**
 * 后风档角度联动效果测试
 * 模拟 Car3D.vue / Car2D.vue 中的后风档计算逻辑
 * 验证不同车型参数下 rear_window_angle 和 rear_slant_angle 的联动效果
 */

import { describe, it, expect } from 'vitest'
import { carTypeParams, defaultCarParams } from '../src/config/carPresets'

/**
 * 模拟 Car3D.vue 中的后风档计算逻辑（单位：米）
 * 与 Car3D.vue createCar() 中的计算保持一致
 */
function computeRearWindow3D(params) {
  const W = params.overall_width / 1000
  const H = params.overall_height / 1000
  const WB = params.wheel_base / 1000
  const gc = params.ground_clearance / 1000
  const hoodLen = params.hood_length / 1000
  const roofH = params.roof_height / 1000
  const wAngle = params.windshield_angle * Math.PI / 180
  const rAngle = params.rear_window_angle * Math.PI / 180
  const rSlant = params.rear_slant_angle * Math.PI / 180
  const FO = (params.front_overhang || 1000) / 1000
  const RO = (params.rear_overhang || 1000) / 1000

  const frontWheelX = WB / 2
  const rearWheelX = -WB / 2
  const frontX = frontWheelX + FO
  const rearX = rearWheelX - RO

  const hoodEndX = frontX - hoodLen
  const trunkLength = Math.min(RO * 0.6, hoodLen * 0.5)
  const trunkStartX = rearX + trunkLength

  const bodyBottomY = gc
  const bodyTopY = gc + H * 0.4
  const roofTopY = gc + H * 0.4 + roofH
  const beltLineY = gc + H * 0.55

  const windshieldHeight = (roofTopY - beltLineY) * 0.7
  const windshieldTopX = hoodEndX - windshieldHeight / Math.tan(wAngle)

  const maxRoofLength = windshieldTopX - trunkStartX
  const slantFactor = Math.min(Math.max(params.rear_slant_angle / 60, 0), 1)
  const roofLen = Math.max(maxRoofLength * (1 - slantFactor * 0.7), 0.8)
  const rearWindowTopX = windshieldTopX - roofLen

  const rearWindowVertHeight = roofTopY - beltLineY
  const rearWindowHeightRatio = 0.5 + slantFactor * 0.3
  const rearWindowHeight = rearWindowVertHeight * rearWindowHeightRatio
  const rearWindowBottomX = rearWindowTopX - rearWindowHeight / Math.tan(rAngle)

  return {
    // 关键坐标
    windshieldTopX,
    rearWindowTopX,
    rearWindowBottomX,
    roofTopY,
    beltLineY,
    bodyTopY,
    // 派生尺寸
    roofLen,
    maxRoofLength,
    rearWindowHeight,
    rearWindowHorizontalSpan: Math.abs(rearWindowBottomX - rearWindowTopX),
    slantFactor,
    // 车身范围
    frontX,
    rearX,
    bodyLength: frontX - rearX,
    trunkStartX
  }
}

/**
 * 计算后风档玻璃的有效倾角（从顶部到底部的实际角度）
 */
function computeEffectiveAngle(result) {
  const dx = result.rearWindowBottomX - result.rearWindowTopX
  const dy = result.roofTopY - result.beltLineY
  // 与垂直方向的夹角
  return Math.atan2(dx, dy) * 180 / Math.PI
}

describe('后风档角度联动效果测试', () => {
  // 构造包含不同车型参数的 mock 数据
  const carTypeMockData = {
    sedan: {
      name: '轿车 Sedan',
      params: { ...defaultCarParams, ...carTypeParams.sedan },
      expected: { slantFactorRange: [0, 0.3], roofRatioMin: 0.7 }
    },
    suv: {
      name: 'SUV',
      params: { ...defaultCarParams, ...carTypeParams.suv },
      expected: { slantFactorRange: [0, 0.2], roofRatioMin: 0.85 }
    },
    coupe: {
      name: 'Coupe 跑车',
      params: { ...defaultCarParams, ...carTypeParams.coupe },
      expected: { slantFactorRange: [0.4, 0.7], roofRatioMin: 0.4 }
    },
    sport: {
      name: 'Sports 超跑',
      params: { ...defaultCarParams, ...carTypeParams.sport },
      expected: { slantFactorRange: [0.7, 1.0], roofRatioMin: 0.25 }
    },
    mpv: {
      name: 'MPV 商务车',
      params: { ...defaultCarParams, ...carTypeParams.mpv },
      expected: { slantFactorRange: [0, 0.15], roofRatioMin: 0.9 }
    },
    pickup: {
      name: 'Pickup 皮卡',
      params: { ...defaultCarParams, ...carTypeParams.pickup },
      expected: { slantFactorRange: [0.1, 0.3], roofRatioMin: 0.75 }
    }
  }

  describe('1. 各车型后风档参数差异化验证', () => {
    Object.entries(carTypeMockData).forEach(([type, data]) => {
      it(`${data.name}: rear_slant_angle=${data.params.rear_slant_angle}°, rear_window_angle=${data.params.rear_window_angle}°`, () => {
        const result = computeRearWindow3D(data.params)

        // slantFactor 应在预期范围内
        expect(result.slantFactor).toBeGreaterThanOrEqual(data.expected.slantFactorRange[0])
        expect(result.slantFactor).toBeLessThanOrEqual(data.expected.slantFactorRange[1])

        // 车顶长度占最大可用长度的比例
        const roofRatio = result.roofLen / result.maxRoofLength
        expect(roofRatio).toBeGreaterThanOrEqual(data.expected.roofRatioMin)

        console.log(`  [${data.name}] slantFactor=${result.slantFactor.toFixed(3)}, ` +
          `roofLen=${result.roofLen.toFixed(3)}m, ` +
          `roofRatio=${roofRatio.toFixed(3)}, ` +
          `rearWindowSpan=${result.rearWindowHorizontalSpan.toFixed(3)}m, ` +
          `effectiveAngle=${computeEffectiveAngle(result).toFixed(1)}°`)
      })
    })
  })

  describe('2. rear_slant_angle 对车顶长度的影响（溜背效果）', () => {
    it('后倾角度越大，车顶越短（溜背效果越明显）', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      const slantAngles = [5, 15, 25, 35, 45, 55]
      const results = slantAngles.map(angle => {
        const params = { ...baseParams, rear_slant_angle: angle }
        const r = computeRearWindow3D(params)
        return { angle, roofLen: r.roofLen, slantFactor: r.slantFactor }
      })

      console.log('\n  后倾角度对车顶长度的影响:')
      results.forEach(r => {
        console.log(`    slant=${r.angle}° → roofLen=${r.roofLen.toFixed(3)}m, slantFactor=${r.slantFactor.toFixed(3)}`)
      })

      // 验证单调递减（车顶长度随角度增大而减小）
      for (let i = 1; i < results.length; i++) {
        expect(results[i].roofLen).toBeLessThanOrEqual(results[i - 1].roofLen)
      }
    })
  })

  describe('3. rear_window_angle 对后风档玻璃倾斜度的影响', () => {
    it('后风档角度越小，玻璃越倾斜（水平投影越大）', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      const windowAngles = [15, 25, 35, 45, 55]
      const results = windowAngles.map(angle => {
        const params = { ...baseParams, rear_window_angle: angle }
        const r = computeRearWindow3D(params)
        return {
          angle,
          span: r.rearWindowHorizontalSpan,
          effectiveAngle: computeEffectiveAngle(r)
        }
      })

      console.log('\n  后风档角度对玻璃倾斜度的影响:')
      results.forEach(r => {
        console.log(`    window_angle=${r.angle}° → horizontalSpan=${r.span.toFixed(3)}m, effectiveAngle=${r.effectiveAngle.toFixed(1)}°`)
      })

      // 角度越小，水平投影越大（玻璃越倾斜）
      for (let i = 1; i < results.length; i++) {
        expect(results[i].span).toBeLessThanOrEqual(results[i - 1].span)
      }
    })
  })

  describe('4. 车型差异化对比（Sport vs SUV）', () => {
    it('超跑应该有明显的溜背造型，SUV应该有方正的车顶', () => {
      const sportResult = computeRearWindow3D({ ...defaultCarParams, ...carTypeParams.sport })
      const suvResult = computeRearWindow3D({ ...defaultCarParams, ...carTypeParams.suv })

      const sportRoofRatio = sportResult.roofLen / sportResult.maxRoofLength
      const suvRoofRatio = suvResult.roofLen / suvResult.maxRoofLength

      console.log('\n  车型对比:')
      console.log(`    Sport: roofLen=${sportResult.roofLen.toFixed(3)}m, ratio=${sportRoofRatio.toFixed(3)}, slantFactor=${sportResult.slantFactor.toFixed(3)}`)
      console.log(`    SUV:   roofLen=${suvResult.roofLen.toFixed(3)}m, ratio=${suvRoofRatio.toFixed(3)}, slantFactor=${suvResult.slantFactor.toFixed(3)}`)

      // 超跑的车顶比例应该明显小于SUV（溜背造型）
      expect(sportRoofRatio).toBeLessThan(suvRoofRatio)
      // 超跑的slantFactor应该明显大于SUV
      expect(sportResult.slantFactor).toBeGreaterThan(suvResult.slantFactor)
      // 超跑的车顶绝对长度应该更短
      expect(sportResult.roofLen).toBeLessThan(suvResult.roofLen)
    })
  })

  describe('5. 前后悬与整车长度比例关系验证', () => {
    Object.entries(carTypeMockData).forEach(([type, data]) => {
      it(`${data.name}: FO + WB + RO = overall_length`, () => {
        const { front_overhang, wheel_base, rear_overhang, overall_length } = data.params
        const sum = front_overhang + wheel_base + rear_overhang

        console.log(`  [${data.name}] FO=${front_overhang} + WB=${wheel_base} + RO=${rear_overhang} = ${sum} (overall_length=${overall_length})`)

        expect(sum).toBe(overall_length)
      })
    })
  })

  describe('6. 参数联动测试 - 调整 rear_slant_angle 时其他尺寸应合理变化', () => {
    it('调整 rear_slant_angle 不应改变车身总长和轴距', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      const original = computeRearWindow3D(baseParams)

      const modified = computeRearWindow3D({ ...baseParams, rear_slant_angle: 50 })

      // 车身总长不变
      expect(modified.bodyLength).toBeCloseTo(original.bodyLength, 5)
      // 前后悬位置不变
      expect(modified.frontX).toBeCloseTo(original.frontX, 5)
      expect(modified.rearX).toBeCloseTo(original.rearX, 5)

      console.log(`  bodyLength: ${original.bodyLength.toFixed(3)}m → ${modified.bodyLength.toFixed(3)}m (不变)`)
      console.log(`  roofLen: ${original.roofLen.toFixed(3)}m → ${modified.roofLen.toFixed(3)}m (缩短)`)
    })
  })
})
