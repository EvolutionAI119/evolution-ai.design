/**
 * Car3D.vue 组件几何计算测试
 * 验证 Three.js 3D坐标计算逻辑的正确性
 */

import { describe, it, expect } from 'vitest'
import { carTypeParams, defaultCarParams } from '../src/config/carPresets'

function computeCar3D(params) {
  const W = params.overall_width / 1000
  const H = params.overall_height / 1000
  const WB = params.wheel_base / 1000
  const track = params.track_width / 1000
  const gc = params.ground_clearance / 1000
  const hoodLen = params.hood_length / 1000
  const wheelR = params.wheel_diameter / 2000
  const roofH = params.roof_height / 1000
  const wAngle = params.windshield_angle * Math.PI / 180
  const rAngle = params.rear_window_angle * Math.PI / 180
  const FO = (params.front_overhang || 1000) / 1000
  const RO = (params.rear_overhang || 1000) / 1000

  const frontWheelX = WB / 2
  const rearWheelX = -WB / 2
  const halfTrack = track / 2

  const frontX = frontWheelX + FO
  const rearX = rearWheelX - RO
  const bodyLength = Math.abs(rearX - frontX)

  const bodyBottomY = gc
  const roofTopY = bodyBottomY + H
  const beltLineY = bodyBottomY + H * 0.76
  const hoodLineY = bodyBottomY + H * 0.62
  const trunkLineY = bodyBottomY + H * 0.66

  const hoodEndX = frontX - hoodLen
  const trunkLength = Math.min(RO * 0.6, hoodLen * 0.5)
  const trunkStartX = rearX + trunkLength

  const windshieldHeight = roofTopY - beltLineY
  const windshieldTopX = hoodEndX - windshieldHeight / Math.tan(wAngle)

  const maxRoofLength = windshieldTopX - trunkStartX
  const slantFactor = Math.min(Math.max(params.rear_slant_angle / 60, 0), 1)
  const roofLen = Math.max(maxRoofLength * (1 - slantFactor * 0.6), 0.8)
  const rearWindowTopX = windshieldTopX - roofLen

  const rearWindowVertHeight = roofTopY - beltLineY
  const rearWindowHeightRatio = 0.5 + slantFactor * 0.35
  const rearWindowHeight = rearWindowVertHeight * rearWindowHeightRatio
  const rearWindowBottomX = rearWindowTopX - rearWindowHeight / Math.tan(rAngle)

  return {
    dimensions: {
      W, H, WB, track, gc, hoodLen, wheelR, roofH
    },
    wheelPositions: {
      frontWheelX, rearWheelX, halfTrack
    },
    bodyExtents: {
      frontX, rearX, bodyLength
    },
    heightLines: {
      bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY
    },
    roofGeometry: {
      hoodEndX, trunkStartX, windshieldTopX, rearWindowTopX,
      maxRoofLength, slantFactor, roofLen
    },
    rearWindow: {
      rearWindowHeight, rearWindowBottomX, rearWindowHeightRatio
    }
  }
}

describe('Car3D 几何计算测试', () => {
  describe('1. 3D坐标系统验证', () => {
    it('坐标系统应遵循"前正后负"规则', () => {
      const result = computeCar3D({ ...defaultCarParams, ...carTypeParams.sedan })
      
      expect(result.bodyExtents.frontX).toBeGreaterThan(0)
      expect(result.bodyExtents.rearX).toBeLessThan(0)
      expect(result.bodyExtents.frontX).toBeGreaterThan(result.bodyExtents.rearX)
    })

    it('前车轮应在正X方向，后车轮应在负X方向', () => {
      const result = computeCar3D({ ...defaultCarParams, ...carTypeParams.sedan })
      
      expect(result.wheelPositions.frontWheelX).toBeGreaterThan(0)
      expect(result.wheelPositions.rearWheelX).toBeLessThan(0)
    })
  })

  describe('2. 车身高度层次验证', () => {
    it('SEDAN 应使用正确的高度线比例', () => {
      const result = computeCar3D({ ...defaultCarParams, ...carTypeParams.sedan })
      
      expect(result.heightLines.beltLineY).toBeCloseTo(result.heightLines.bodyBottomY + result.dimensions.H * 0.76, 6)
      expect(result.heightLines.hoodLineY).toBeCloseTo(result.heightLines.bodyBottomY + result.dimensions.H * 0.62, 6)
      expect(result.heightLines.trunkLineY).toBeCloseTo(result.heightLines.bodyBottomY + result.dimensions.H * 0.66, 6)
      
      expect(result.heightLines.roofTopY).toBeGreaterThan(result.heightLines.beltLineY)
      expect(result.heightLines.beltLineY).toBeGreaterThan(result.heightLines.hoodLineY)
      expect(result.heightLines.hoodLineY).toBeGreaterThan(result.heightLines.bodyBottomY)
    })
  })

  describe('3. 车身总长度验证', () => {
    it('车身长度应等于 frontX - rearX (绝对值)', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar3D(params)
      
      const expectedLength = (params.overall_length) / 1000
      expect(result.bodyExtents.bodyLength).toBeCloseTo(expectedLength, 6)
    })
  })

  describe('4. 车顶长度计算验证', () => {
    it('车顶长度应随 rear_slant_angle 增大而减小', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      
      const result1 = computeCar3D({ ...baseParams, rear_slant_angle: 10 })
      const result2 = computeCar3D({ ...baseParams, rear_slant_angle: 30 })
      const result3 = computeCar3D({ ...baseParams, rear_slant_angle: 50 })
      
      expect(result1.roofGeometry.slantFactor).toBeLessThan(result2.roofGeometry.slantFactor)
      expect(result2.roofGeometry.slantFactor).toBeLessThan(result3.roofGeometry.slantFactor)
      
      expect(result1.roofGeometry.roofLen).toBeGreaterThan(result2.roofGeometry.roofLen)
      expect(result2.roofGeometry.roofLen).toBeGreaterThan(result3.roofGeometry.roofLen)
    })

    it('车顶长度不应小于最小限制 0.8m', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sport }
      const result = computeCar3D(params)
      
      expect(result.roofGeometry.roofLen).toBeGreaterThanOrEqual(0.8)
    })
  })

  describe('5. 车型差异化验证', () => {
    it('Sport 车型应具有明显溜背造型', () => {
      const sport = computeCar3D({ ...defaultCarParams, ...carTypeParams.sport })
      const suv = computeCar3D({ ...defaultCarParams, ...carTypeParams.suv })
      
      expect(sport.roofGeometry.slantFactor).toBeGreaterThan(suv.roofGeometry.slantFactor)
      expect(sport.roofGeometry.roofLen).toBeLessThan(suv.roofGeometry.roofLen)
      
      expect(sport.dimensions.H).toBeLessThan(suv.dimensions.H)
      expect(sport.dimensions.gc).toBeLessThan(suv.dimensions.gc)
    })

    it('SUV 应具有方正的车顶', () => {
      const suv = computeCar3D({ ...defaultCarParams, ...carTypeParams.suv })
      
      expect(suv.roofGeometry.slantFactor).toBeLessThan(0.3)
      expect(suv.roofGeometry.roofLen / suv.roofGeometry.maxRoofLength).toBeGreaterThan(0.8)
    })
  })

  describe('6. 车轮位置与轮距关系', () => {
    it('半轮距应等于 track_width / 2', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar3D(params)
      
      expect(result.wheelPositions.halfTrack).toBeCloseTo(params.track_width / 2000, 6)
    })
  })

  describe('7. 后风档玻璃几何验证', () => {
    it('后风档底部X坐标应随 rear_window_angle 增大而前移', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      
      const result1 = computeCar3D({ ...baseParams, rear_window_angle: 20 })
      const result2 = computeCar3D({ ...baseParams, rear_window_angle: 40 })
      
      expect(result1.rearWindow.rearWindowBottomX).toBeLessThan(result2.rearWindow.rearWindowBottomX)
    })
  })

  describe('8. 前后悬与车轮位置关系', () => {
    it('前轮位置应等于 WB/2', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar3D(params)
      
      expect(result.wheelPositions.frontWheelX).toBeCloseTo(params.wheel_base / 2000, 6)
    })

    it('前悬末端应在前轮前方', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar3D(params)
      
      expect(result.bodyExtents.frontX).toBeGreaterThan(result.wheelPositions.frontWheelX)
    })
  })
})