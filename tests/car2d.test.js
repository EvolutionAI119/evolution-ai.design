/**
 * Car2D.vue 组件几何计算测试
 * 验证 2D 渲染管线（双向自适应缩放 + 触地车轮 + 闭合轮廓 + SISA 参考集成）
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { carTypeParams, defaultCarParams, brands } from '../src/config/carPresets'
import { SISA_META, SISA_Z_TOP_NORM, evalTopRMSE, sampleTopNorm, toPlatformX } from '../src/config/sisaReference'
import { LINE_RATIOS, deriveCarProfile } from '../src/utils/carProfile.js'

const svgWidth = 800
const svgHeight = 420
const padTop = 30
const dimAreaH = 84
const groundY = svgHeight - dimAreaH

function computeCar2D(params, carType = 'sedan') {
  const FO = params.front_overhang ?? 1000
  const RO = params.rear_overhang ?? 1000
  const WB = params.wheel_base
  const H = params.overall_height ?? 1400
  const gc = params.ground_clearance ?? 140
  const actualLength = FO + WB + RO

  // 双向自适应缩放：宽度（车长）与高度（离地总高 H，含离地间隙）共同约束
  const scale = Math.min((svgWidth - 150) / actualLength, (groundY - padTop) / H)
  const s = (val) => val * scale

  const rearX = s(actualLength)
  const frontWheelCX = s(FO)
  const rearWheelCX = s(FO + WB)

  const wheelRadius = s((params.wheel_diameter ?? 680) / 2)
  const wheelCY = groundY - wheelRadius
  const underbodyY = groundY - s(gc)

  // 轮廓锚点与组件/3D 同源：deriveCarProfile → 2D 镜像换算（x = 距前保险杠距离）
  const P = deriveCarProfile(params, carType)
  const toX = (x3d) => s((P.frontX - x3d) * 1000)
  const roofTopY = groundY - s(P.roofTopY * 1000)
  const beltLineY = groundY - s(P.beltLineY * 1000)
  const hoodLineY = groundY - s(P.hoodLineY * 1000)
  const trunkLineY = groundY - s(P.trunkLineY * 1000)
  const hoodEndX = toX(P.hoodEndX)
  const cowlStartX = toX(P.cowlStartX)
  const windshieldTopX = toX(P.windshieldTopX)
  const rearWindowTopX = toX(P.rearWindowTopX)
  const rearWindowBottomX = toX(P.rearWindowBottomX)
  const cabRearX2d = P.pickup ? toX(P.pickup.cabRearX) : 0

  return {
    scale,
    actualLength,
    groundY,
    rearX,
    frontWheelCX,
    rearWheelCX,
    wheelRadius,
    wheelCY,
    underbodyY,
    roofTopY,
    beltLineY,
    hoodLineY,
    trunkLineY,
    hoodEndX,
    cowlStartX,
    trunkStartX: toX(P.trunkStartX),
    cabRearX2d,
    slantFactor: P.slantFactor,
    roofLen: P.roofLen * 1000,
    windshieldTopX,
    rearWindowTopX,
    rearWindowBottomX,
    profile: P,
    wheelBottomY: wheelCY + wheelRadius,
    heightLines: {
      distanceRoofToBelt: beltLineY - roofTopY,
      distanceBeltToHood: hoodLineY - beltLineY
    }
  }
}

describe('Car2D 几何计算测试（重构后管线）', () => {
  describe('1. 双向自适应缩放', () => {
    it('不同车型车顶不得越出画布顶部（历史缺陷：SUV 车顶被裁切）', () => {
      for (const type of Object.keys(carTypeParams)) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        expect(result.roofTopY).toBeGreaterThanOrEqual(padTop - 0.001)
      }
    })

    it('缩放取宽度与高度约束的较小者', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar2D(params)
      const expected = Math.min((svgWidth - 150) / result.actualLength, (groundY - padTop) / (params.overall_height + params.ground_clearance))
      expect(result.scale).toBeCloseTo(expected, 6)
      expect(result.rearX).toBeLessThanOrEqual(svgWidth - 40)
    })
  })

  describe('2. 高度线层次验证', () => {
    it('所有车型应具有正确的三层高度线（车顶 < 腰带 < 引擎盖，尾箱/栏板 < 腰带）', () => {
      for (const type of Object.keys(carTypeParams)) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        expect(result.roofTopY).toBeLessThan(result.beltLineY)
        expect(result.beltLineY).toBeLessThan(result.hoodLineY)
        expect(result.trunkLineY).toBeGreaterThan(result.beltLineY) // 尾箱/栏板顶低于腰带线
        expect(result.heightLines.distanceRoofToBelt).toBeGreaterThan(0)
        expect(result.heightLines.distanceBeltToHood).toBeGreaterThan(0)
      }
    })
  })

  describe('3. 车轮几何验证（触地 + 同心）', () => {
    it('车轮位置应基于轴距正确计算', () => {
      const params = { ...defaultCarParams, ...carTypeParams.sedan }
      const result = computeCar2D(params)

      expect(result.frontWheelCX).toBeCloseTo(result.scale * params.front_overhang, 6)
      expect(result.rearWheelCX).toBeCloseTo(result.scale * (params.front_overhang + params.wheel_base), 6)
      expect(result.rearWheelCX - result.frontWheelCX).toBeCloseTo(result.scale * params.wheel_base, 6)
    })

    it('轮胎最低点应触地（SISA ground_alignment：z 原点 = 地面）', () => {
      for (const type of ['sedan', 'suv', 'sport']) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        expect(result.wheelBottomY).toBeCloseTo(result.groundY, 6)
      }
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
      const sport = computeCar2D({ ...defaultCarParams, ...carTypeParams.sport }, 'sport')
      const suv = computeCar2D({ ...defaultCarParams, ...carTypeParams.suv }, 'suv')

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

    it('侧窗关键点应钳位在甲板起点与车尾之间（SUV/MPV 大倾角不越出车尾）', () => {
      for (const type of ['suv', 'mpv']) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        expect(result.rearWindowBottomX).toBeLessThanOrEqual(result.rearX + 0.001)
        expect(result.rearWindowBottomX).toBeGreaterThanOrEqual(result.trunkStartX - 0.001)
        expect(result.windshieldTopX).toBeGreaterThan(result.hoodEndX)
        expect(result.rearWindowTopX).toBeGreaterThan(result.windshieldTopX)
      }
      // pickup：后窗下沿在驾驶室（cabWindowBottom），位于风挡顶之后、车尾之前
      const pk = computeCar2D({ ...defaultCarParams, ...carTypeParams.pickup }, 'pickup')
      expect(pk.rearWindowBottomX).toBeLessThan(pk.rearWindowTopX)
      expect(pk.rearWindowBottomX).toBeGreaterThan(pk.windshieldTopX)
      expect(pk.rearWindowBottomX).toBeLessThan(pk.rearX)
    })
  })

  describe('8. Cayenne 实参回归（用户报告场景）', () => {
    const cayenne = brands.flatMap(b => b.models).find(m => m.key === 'cayenne')

    it('预设存在且车顶完整可见、车轮触地', () => {
      expect(cayenne).toBeTruthy()
      const result = computeCar2D(cayenne.params, 'suv')
      expect(result.roofTopY).toBeGreaterThanOrEqual(padTop - 0.001)
      expect(result.wheelBottomY).toBeCloseTo(result.groundY, 6)
      expect(result.rearWindowBottomX).toBeLessThanOrEqual(result.rearX + 0.001)
      expect(result.rearWindowBottomX).toBeGreaterThanOrEqual(result.trunkStartX - 0.001)
    })
  })

  describe('9. SISA 参考集成', () => {
    it('坐标映射符合参考包约定（车头 = -L/2）', () => {
      expect(toPlatformX(0, 4926)).toBeCloseTo(-2463, 6)
      expect(toPlatformX(1, 4926)).toBeCloseTo(2463, 6)
    })

    it('evalTopRMSE 对参考曲线自身为 0', () => {
      const rmse = evalTopRMSE(SISA_Z_TOP_NORM)
      expect(rmse).toBeLessThan(1e-9)
    })

    it('sampleTopNorm 在端点与中点返回有限值且单调不超界', () => {
      expect(sampleTopNorm(0)).toBeCloseTo(SISA_Z_TOP_NORM[0], 6)
      expect(sampleTopNorm(1)).toBeCloseTo(SISA_Z_TOP_NORM[SISA_Z_TOP_NORM.length - 1], 6)
      for (let i = 0; i < 20; i++) {
        const v = sampleTopNorm(i / 20)
        expect(Number.isFinite(v)).toBe(true)
        expect(v).toBeGreaterThanOrEqual(0)
        expect(v).toBeLessThanOrEqual(1.001)
      }
    })

    it('参考包元数据完整（地面基准 / 像真度来源）', () => {
      expect(SISA_META.coordinateSystem.refHeightMm).toBeGreaterThan(1000)
      expect(SISA_META.quality.fitRmseMedianMm).toBeGreaterThan(0)
    })
  })

  describe('10. SISA 反馈单问题 A 回归守卫', () => {
    it('Car2D.vue 不得包含顶层 console.log', () => {
      const src = readFileSync(resolve(process.cwd(), 'src/components/Car2D.vue'), 'utf8')
      expect(src).not.toMatch(/console\.log/)
    })
  })

  describe('11. 玻璃衔接与标注规范回归（belt 下移 + cowl 斜坡 + 三行尺寸标注）', () => {
    it('腰带线已下移且仍高于引擎盖（玻璃不悬浮、车身比例正确）', () => {
      for (const r of Object.values(LINE_RATIOS)) {
        expect(1 - r.belt).toBeGreaterThanOrEqual(0.26) // 玻璃区高度不低于车高 26%
        expect(r.belt).toBeGreaterThan(r.hood)          // 腰带高于引擎盖
        expect(r.trunk ?? r.bed).toBeLessThan(r.belt)   // 尾箱/栏板低于腰带
      }
    })

    it('特征线离地高度符合官方基准（E级 / Cayenne / F-150，±60mm 容差）', () => {
      // sedan≈奔驰E级：腰带≈990mm、引擎盖≈905mm
      const sedan = carTypeParams.sedan.overall_height
      expect(sedan * LINE_RATIOS.sedan.belt).toBeGreaterThan(930)
      expect(sedan * LINE_RATIOS.sedan.belt).toBeLessThan(1050)
      expect(sedan * LINE_RATIOS.sedan.hood).toBeGreaterThan(845)
      expect(sedan * LINE_RATIOS.sedan.hood).toBeLessThan(965)
      // suv≈Cayenne：腰带≈1210mm
      const suv = carTypeParams.suv.overall_height
      expect(suv * LINE_RATIOS.suv.belt).toBeGreaterThan(1150)
      expect(suv * LINE_RATIOS.suv.belt).toBeLessThan(1270)
      // pickup≈F-150：货箱栏板≈1090mm、低于腰带
      const pk = carTypeParams.pickup.overall_height
      expect(pk * LINE_RATIOS.pickup.bed).toBeGreaterThan(1030)
      expect(pk * LINE_RATIOS.pickup.bed).toBeLessThan(1150)
      expect(LINE_RATIOS.pickup.bed).toBeLessThan(LINE_RATIOS.pickup.belt)
    })

    it('Cowl 斜坡位于风挡底之前（玻璃下缘落在车身表面）', () => {
      for (const type of Object.keys(carTypeParams)) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        expect(result.cowlStartX).toBeLessThan(result.hoodEndX)
        expect(result.cowlStartX).toBeGreaterThan(0)
        expect(result.windshieldTopX).toBeGreaterThan(result.hoodEndX)
      }
    })

    it('三行尺寸标注均在地面线下方且不越出画布（文字不与车身/车轮重叠）', () => {
      const dimY1 = groundY + 20
      const dimY2 = groundY + 42
      const dimY3 = groundY + 64
      for (const textBaseY of [dimY1 - 5, dimY2 - 5, dimY3 - 5]) {
        expect(textBaseY).toBeGreaterThan(groundY) // 车身/车轮均在地面线之上
      }
      expect(dimY3 + 4).toBeLessThanOrEqual(svgHeight)
    })

    it('H 车高垂直标注不越出画布右缘（宽度预留 150px）', () => {
      for (const type of Object.keys(carTypeParams)) {
        const result = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        const contentX = (svgWidth - result.actualLength * result.scale) / 2
        expect(contentX + result.rearX + 56).toBeLessThanOrEqual(svgWidth)
      }
    })

    it('Car2D.vue 源码含 cowl 斜坡与完整尺寸标注实现', () => {
      const src = readFileSync(resolve(process.cwd(), 'src/components/Car2D.vue'), 'utf8')
      expect(src).toContain('cowlStartX')
      expect(src).toContain('dimY3')
      expect(src).toContain('H {{ overallHeight }}mm')
      expect(src).toContain('W {{ overallWidth }}mm')
    })
  })

  describe('12. 皮卡拓扑与 2D/3D 比例一致性（F-150 基准）', () => {
    it('驾驶室后壁 = 后轮中心朝车头 0.5m，车顶不贯通、货箱段 ≥1.5m', () => {
      const params = { ...defaultCarParams, ...carTypeParams.pickup }
      const result = computeCar2D(params, 'pickup')
      expect(result.cabRearX2d).toBeCloseTo(result.rearWheelCX - result.scale * 500, 6)
      expect(result.cabRearX2d).toBeGreaterThan(result.windshieldTopX)   // 车顶长度为正
      expect(result.rearWindowTopX).toBeCloseTo(result.cabRearX2d, 6)    // 车顶止于驾驶室后壁
      expect(result.rearX - result.cabRearX2d).toBeGreaterThan(result.scale * 1500) // 货箱段 ≈1.6m（F-150 1676mm 等比）
      expect(result.rearWindowBottomX).toBeLessThan(result.cabRearX2d)   // 后窗下沿微向前收
    })

    it('2D 与 3D 关键比例逐点一致（carProfile 同源推导）', () => {
      const params = { ...defaultCarParams, ...carTypeParams.pickup }
      const r2d = computeCar2D(params, 'pickup')
      const p3d = deriveCarProfile(carTypeParams.pickup, 'pickup')
      // 驾驶室后壁：3D X+ 朝车头 → 前保险杠到后壁距离（mm）应等于 2D 同名量
      const cabRearFromFrontMm = (p3d.frontX - p3d.pickup.cabRearX) * 1000
      expect(r2d.cabRearX2d / r2d.scale).toBeCloseTo(cabRearFromFrontMm, 1)
      // 特征线离地高度：2D/3D 同为 H × LINE_RATIOS
      expect((r2d.groundY - r2d.roofTopY) / r2d.scale).toBeCloseTo(p3d.roofTopY * 1000, 1)
      expect((r2d.groundY - r2d.beltLineY) / r2d.scale).toBeCloseTo(p3d.beltLineY * 1000, 1)
      expect((r2d.groundY - r2d.hoodLineY) / r2d.scale).toBeCloseTo(p3d.hoodLineY * 1000, 1)
      expect((r2d.groundY - r2d.trunkLineY) / r2d.scale).toBeCloseTo(p3d.pickup.bedWallY * 1000, 1)
    })

    it('六车型 2D/3D 全部侧围锚点逐点一致（hoodEnd/cowl/wsTop/rwTop/rwBot/高度线）', () => {
      for (const type of Object.keys(carTypeParams)) {
        const r2d = computeCar2D({ ...defaultCarParams, ...carTypeParams[type] }, type)
        const p3d = r2d.profile
        // 镜像换算自 profile → 与 3D 锚点严格一致（重算验证换算无漂移）
        const toX = (x) => (p3d.frontX - x) * 1000
        expect(r2d.hoodEndX / r2d.scale).toBeCloseTo(toX(p3d.hoodEndX), 1)
        expect(r2d.cowlStartX / r2d.scale).toBeCloseTo(toX(p3d.cowlStartX), 1)
        expect(r2d.windshieldTopX / r2d.scale).toBeCloseTo(toX(p3d.windshieldTopX), 1)
        expect(r2d.rearWindowTopX / r2d.scale).toBeCloseTo(toX(p3d.rearWindowTopX), 1)
        expect(r2d.rearWindowBottomX / r2d.scale).toBeCloseTo(toX(p3d.rearWindowBottomX), 1)
        expect((r2d.groundY - r2d.roofTopY) / r2d.scale).toBeCloseTo(p3d.roofTopY * 1000, 1)
        expect((r2d.groundY - r2d.beltLineY) / r2d.scale).toBeCloseTo(p3d.beltLineY * 1000, 1)
        expect((r2d.groundY - r2d.hoodLineY) / r2d.scale).toBeCloseTo(p3d.hoodLineY * 1000, 1)
        expect((r2d.groundY - r2d.trunkLineY) / r2d.scale).toBeCloseTo(p3d.trunkLineY * 1000, 1)
      }
    })

    it('侧围轮廓 G1 圆角/cowl/轮拱 notch 收敛到 carProfile.bodySideOutline 单一真源，Car3D 消费之', () => {
      const prof = readFileSync(resolve(process.cwd(), 'src/utils/carProfile.js'), 'utf8')
      const car3d = readFileSync(resolve(process.cwd(), 'src/components/Car3D.vue'), 'utf8')
      // 轮廓真源在 carProfile.js：三处 G1 圆角 + cowl 斜坡 + 底边轮拱 notch
      expect(prof).toContain('export function bodySideOutline')
      expect(prof).toContain('filletCorner')
      expect(prof).toContain('cowlStartX')
      expect(prof).toContain('hoodEndX, beltLineY')
      expect(prof).toContain('archNotch')
      // Car3D 不再内联构建轮廓，改为消费 bodySideOutline（2D/3D 同源）
      expect(car3d).toContain('bodySideOutline(')
      expect(car3d).not.toContain('bodyShape.holes.push')
    })

    it('Car2D.vue 源码含皮卡专属拓扑分支（isPickup / cabRearX2d）', () => {
      const src = readFileSync(resolve(process.cwd(), 'src/components/Car2D.vue'), 'utf8')
      expect(src).toContain('isPickup')
      expect(src).toContain('cabRearX2d')
      expect(src).toContain("from '../utils/carProfile.js'")
    })
  })
})
