/**
 * Car2D.vue 组件几何计算测试
 * 验证 SVG 坐标计算逻辑的正确性
 */

import { describe, it, expect } from 'vitest'
import { carTypeParams, defaultCarParams } from '../src/config/carPresets'

const svgWidth = 800
const svgHeight = 280
const offsetX = 40
const groundLineY = 200

function computeCar2D(params) {
  const FO = params.front_overhang || 1000
  const RO = params.rear_overhang || 1000
  const WB = params.wheel_base
  const actualLength = FO + WB + RO
  
  const usableWidth = svgWidth - offsetX * 2
  const scale = usableWidth / actualLength
  
  const s = (val) => val * scale
  
  const frontWheelX = s(FO)
  const rearWheelX = s(FO + WB)
  const frontX = 0
  const rearX = s(actualLength)
  
  const wheelRadius = s(params.wheel_diameter / 2)
  const groundClearance = s(params.ground_clearance)
  
  const roofTopY = groundLineY - groundClearance - s(params.overall_height)
  const beltLineY = groundLineY - groundClearance - s(params.overall_height * 0.76)
  const hoodLineY = groundLineY - groundClearance - s(params.overall_height * 0.62)
  const trunkLineY = groundLineY - groundClearance - s(params.overall_height * 0.66)
  
  const hoodEndX = s(params.hood_length)
  const trunkLength = Math.min(s(params.rear_overhang * 0.6), s(params.hood_length * 0.5))
  const trunkStartX = rearX - trunkLength
  
  const windshieldAngleRad = params.windshield_angle * Math.PI / 180
  const rearWindowAngleRad = params.rear_window_angle * Math.PI / 180
  
  const windshieldHeight = beltLineY - roofTopY
  const windshieldTopX = hoodEndX + windshieldHeight / Math.tan(windshieldAngleRad)
  
  const maxRoofLength = trunkStartX - windshieldTopX
  const slantFactor = Math.min(Math.max(params.rear_slant_angle / 60, 0), 1)
  const roofLen = Math.max(maxRoofLength * (1 - slantFactor * 0.6), s(800))
  const rearWindowTopX = windshieldTopX + roofLen
  
  const rearWindowVertHeight = beltLineY - roofTopY
  const rearWindowHeightRatio = 0.5 + slantFactor * 0.35
  const rearWindowHeight = rearWindowVertHeight * rearWindowHeightRatio
  const rearWindowBottomX = rearWindowTopX + rearWindowHeight / Math.tan(rearWindowAngleRad)
  
  return {
    scale,
    actualLength,
    frontWheelX,
    rearWheelX,
    frontX,
    rearX,
    wheelRadius,
    groundClearance,
    roofTopY,
    beltLineY,
    hoodLineY,
    trunkLineY,
    hoodEndX,
    trunkLength,
    trunkStartX,
    windshieldTopX,
    maxRoofLength,
    slantFactor,
    roofLen,
    rearWindowTopX,
    rearWindowBottomX,
    heightLines: {
      distanceRoofToBelt: beltLineY - roofTopY,
      distanceBeltToHood: hoodLineY - beltLineY,
      distanceTrunkToBelt: trunkLineY - beltLineY
    }
  }
}

describe('Car2D 几何计算测试', () => {
  describe('1. 比例缩放验证', () => {
    it('不同长度车型应正确缩放以适应 SVG 画布', () => {
      const sedan = computeCar2D({ ...defaultCarParams, ...carTypeParams.sedan })
      const suv = computeCar2D({ ...defaultCarParams, ...carTypeParams.suv })
      const sport = computeCar2D({ ...defaultCarParams, ...carTypeParams.sport })
      
      expect(sedan.rearX).toBeLessThanOrEqual(svgWidth - offsetX * 2)
      expect(suv.rearX).toBeLessThanOrEqual(svgWidth - offsetX * 2)
      expect(sport.rearX).toBeLessThanOrEqual(svgWidth - offsetX * 2)
      
      expect(sedan.scale).toBeCloseTo((svgWidth - 80) / sedan.actualLength, 6)
    })
  })

  describe('2. 高度线层次验证', () => {
    it('轿车应具有正确的三层高度线（引擎盖/腰带线/车顶）', () => {
      const result = computeCar2D({ ...defaultCarParams, ...carTypeParams.sedan })
      
      expect(result.roofTopY).toBeLessThan(result.beltLineY)
      expect(result.beltLineY).toBeLessThan(result.hoodLineY)
      expect(result.trunkLineY).toBeLessThan(result.hoodLineY)
      
      expect(result.heightLines.distanceRoofToBelt).toBeGreaterThan(0)
      expect(result.heightLines.distanceBeltToHood).toBeGreaterThan(0)
    })
  })

  describe('3. 车轮位置验证', () => {
    it('车轮位置应基于轴距正确计算', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar2D(params)
      
      const expectedFrontWheelX = result.scale * params.front_overhang
      const expectedRearWheelX = result.scale * (params.front_overhang + params.wheel_base)
      
      expect(result.frontWheelX).toBeCloseTo(expectedFrontWheelX, 6)
      expect(result.rearWheelX).toBeCloseTo(expectedRearWheelX, 6)
      
      expect(result.rearWheelX - result.frontWheelX).toBeCloseTo(result.scale * params.wheel_base, 6)
    })
  })

  describe('4. 后风档角度联动验证', () => {
    it('rear_slant_angle 增大应缩短车顶长度', () => {
      const baseParams = { ...defaultCarParams, ...carTypeParams.sedan }
      
      const result1 = computeCar2D({ ...baseParams, rear_slant_angle: 10 })
      const result2 = computeCar2D({ ...baseParams, rear_slant_angle: 30 })
      const result3 = computeCar2D({ ...baseParams, rear_slant_angle: 50 })
      
      expect(result1.slantFactor).toBeLessThan(result2.slantFactor)
      expect(result2.slantFactor).toBeLessThan(result3.slantFactor)
      
      expect(result1.roofLen).toBeGreaterThan(result2.roofLen)
      expect(result2.roofLen).toBeGreaterThan(result3.roofLen)
    })
  })

  describe('5. 前后悬与整车长度关系', () => {
    it('FO + WB + RO 应等于整车长度', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar2D(params)
      
      expect(result.actualLength).toBe(params.front_overhang + params.wheel_base + params.rear_overhang)
      expect(result.actualLength).toBe(params.overall_length)
    })
  })

  describe('6. 车型差异化验证', () => {
    it('Sport 车型应比 SUV 有更大的 slantFactor', () => {
      const sport = computeCar2D({ ...defaultCarParams, ...carTypeParams.sport })
      const suv = computeCar2D({ ...defaultCarParams, ...carTypeParams.suv })
      
      expect(sport.slantFactor).toBeGreaterThan(suv.slantFactor)
      expect(sport.roofLen).toBeLessThan(suv.roofLen)
    })
  })

  describe('7. 边界条件验证', () => {
    it('slantFactor 应在 0-1 范围内', () => {
      const result1 = computeCar2D({ ...defaultCarParams, rear_slant_angle: -10 })
      const result2 = computeCar2D({ ...defaultCarParams, rear_slant_angle: 0 })
      const result3 = computeCar2D({ ...defaultCarParams, rear_slant_angle: 60 })
      const result4 = computeCar2D({ ...defaultCarParams, rear_slant_angle: 100 })
      
      expect(result1.slantFactor).toBe(0)
      expect(result2.slantFactor).toBe(0)
      expect(result3.slantFactor).toBe(1)
      expect(result4.slantFactor).toBe(1)
    })

    it('车顶长度不应小于最小限制', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sport }
      const result = computeCar2D(params)
      
      const minRoofLen = result.scale * 800
      expect(result.roofLen).toBeGreaterThanOrEqual(minRoofLen)
    })
  })
})