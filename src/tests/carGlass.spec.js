import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import { bandGlassEndpoints, deriveCabinGlass } from '../utils/carGlass.js'
import { carTypeParams } from '../config/carPresets.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']

describe('bandGlassEndpoints 斜面玻璃带几何', () => {
  it('法线为单位向量且朝上（ny ≥ 0）', () => {
    const { normal } = bandGlassEndpoints(1, 0, 0, 1, 0, 0)
    const [nx, ny] = normal
    expect(Math.hypot(nx, ny)).toBeCloseTo(1, 10)
    expect(ny).toBeGreaterThanOrEqual(0)
  })

  it('下坡斜面法线自动翻转为朝上（外表面）', () => {
    // (0,1)→(1,0)：原始法线 ny<0，必须翻转为朝上
    const { normal } = bandGlassEndpoints(0, 1, 1, 0, 0, 0)
    expect(normal[1]).toBeGreaterThan(0)
    // 翻转后与手工计算一致：(-dy, dx)/len = (1, 1)/√2
    expect(normal[0]).toBeCloseTo(Math.SQRT1_2, 10)
    expect(normal[1]).toBeCloseTo(Math.SQRT1_2, 10)
  })

  it('topInset 使顶缘沿斜线下退，底缘不动', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0.5, 0)
    expect(a).toEqual([0, 0])
    expect(b[0]).toBeCloseTo(0, 10)
    expect(b[1]).toBeCloseTo(1.5, 10) // 2 - 0.5
  })

  it('topInset 超过段长 90% 时钳位，杜绝回折', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 10, 0)
    expect(b[1]).toBeCloseTo(0.2, 10) // 2 × (1 - 0.9)
  })

  it('offset 沿法线平移两端点（贴合外扩后的车身侧壁）', () => {
    const { a, b } = bandGlassEndpoints(0, 0, 0, 2, 0, 0.031)
    // 竖直带法线 = (+1, 0)
    expect(a).toEqual([0.031, 0])
    expect(b).toEqual([0.031, 2])
  })

  it('零长度带不抛异常（len || 1 保护）', () => {
    expect(() => bandGlassEndpoints(0, 0, 0, 0, 0.09, 0.03)).not.toThrow()
  })
})

describe('deriveCabinGlass 与 2D Car2D windowPath/pillarX 逐点同源', () => {
  it('前风挡带锚点 = A 柱线（COWL → 车顶前缘），宽度 = W × 0.9', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.windshield.x1).toBeCloseTo(P.hoodEndX, 10)
    expect(g.windshield.y1).toBeCloseTo(P.beltLineY, 10)
    expect(g.windshield.x2).toBeCloseTo(P.windshieldTopX, 10)
    expect(g.windshield.y2).toBeCloseTo(P.roofTopY, 10)
    expect(g.windshield.width).toBeCloseTo(P.W * 0.9, 10)
    expect(g.windshield.topInset).toBeCloseTo(0.09, 10)
  })

  it('三厢车后风挡存在，锚点 = C 柱线，宽度 = W × 0.88', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.rearWindow).not.toBeNull()
    expect(g.rearWindow.x1).toBeCloseTo(P.rearWindowBottomX, 10)
    expect(g.rearWindow.y1).toBeCloseTo(P.beltLineY, 10)
    expect(g.rearWindow.x2).toBeCloseTo(P.rearWindowTopX, 10)
    expect(g.rearWindow.y2).toBeCloseTo(P.roofTopY, 10)
    expect(g.rearWindow.width).toBeCloseTo(P.W * 0.88, 10)
  })

  it('DLO 四边形与 2D windowPath 同源：上下边水平、顶角内收 12mm、顶边下落 35mm、底边抬升 8mm', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    const [p0, p1, p2, p3] = g.dlo
    // 底边：hoodEndX / rearWindowBottomX，均抬升 8mm（与 2D windowPath 底缘同源）
    expect(p0).toEqual([P.hoodEndX, P.beltLineY + 0.008])
    expect(p3).toEqual([P.rearWindowBottomX, P.beltLineY + 0.008])
    // 顶边：水平，两端各内收 12mm，较车顶下落 35mm（避开 G1 圆角）
    expect(p1).toEqual([P.windshieldTopX + 0.012, P.roofTopY - 0.035])
    expect(p2).toEqual([P.rearWindowTopX - 0.012, P.roofTopY - 0.035])
    expect(p1[1]).toBeCloseTo(p2[1], 10)
    expect(p0[1]).toBeCloseTo(p3[1], 10)
  })

  it('B 柱 = DLO 顶跨 55% 分段（与 2D pillarX 同公式），落在 DLO 范围内', () => {
    const P = deriveCarProfile(carTypeParams.sedan, 'sedan')
    const g = deriveCabinGlass(P)
    expect(g.pillar.x).toBeCloseTo(
      P.windshieldTopX + (P.rearWindowTopX - P.windshieldTopX) * 0.55, 10
    )
    // 55% 插值朝车尾方向（dloTopRear < windshieldTopX，X+ 为车头）
    expect(g.pillar.x).toBeLessThan(P.windshieldTopX)
    expect(g.pillar.x).toBeGreaterThan(g.dloTopRear)
    // 立柱上下端均收进玻璃面内（不越过车顶圆角/腰带）
    expect(g.pillar.topY).toBeCloseTo(P.roofTopY - 0.05, 10)
    expect(g.pillar.botY).toBeCloseTo(P.beltLineY + 0.035, 10)
    expect(g.pillar.topY).toBeGreaterThan(g.pillar.botY)
    expect(g.pillar.topY).toBeLessThan(g.dlo[1][1])
    expect(g.pillar.botY).toBeGreaterThan(g.dlo[0][1])
  })

  it('皮卡专属拓扑：无后风挡，DLO 止于驾驶室后壁', () => {
    const P = deriveCarProfile(carTypeParams.pickup, 'pickup')
    const g = deriveCabinGlass(P)
    expect(g.rearWindow).toBeNull()
    expect(g.dloTopRear).toBeCloseTo(P.pickup.cabRearX, 10)
    expect(g.dloBotRear).toBeCloseTo(P.pickup.cabWindowBottomX, 10)
    expect(g.dlo[2]).toEqual([P.pickup.cabRearX - 0.012, P.roofTopY - 0.035])
    expect(g.dlo[3]).toEqual([P.pickup.cabWindowBottomX, P.beltLineY + 0.008])
    expect(g.pillar.x).toBeCloseTo(
      P.windshieldTopX + (P.pickup.cabRearX - P.windshieldTopX) * 0.55, 10
    )
  })

  it.each(ALL_TYPES)('%s 玻璃面板拓扑合法（DLO 高于底边、风挡锚点有序）', (type) => {
    const P = deriveCarProfile(carTypeParams[type], type)
    const g = deriveCabinGlass(P)
    // 前风挡：底缘在车头侧、顶缘在车顶（X 向后收、Y 向上升）
    expect(g.windshield.x2).toBeLessThan(g.windshield.x1)
    expect(g.windshield.y2).toBeGreaterThan(g.windshield.y1)
    // DLO：顶边高于底边，顶前角在底前角之后（车头在 +X）
    expect(g.dlo[1][1]).toBeGreaterThan(g.dlo[0][1])
    expect(g.dlo[1][0]).toBeLessThan(g.dlo[0][0])
    // 顶后角与底后角关系（后窗斜面不回折）：
    // 常规车 C 柱向后倾 → 底后角更靠车尾；皮卡驾驶室后窗 → 底后角在顶后角车头侧
    if (type === 'pickup') {
      expect(g.dlo[3][0]).toBeGreaterThan(g.dlo[2][0])
    } else {
      expect(g.dlo[2][0]).toBeGreaterThanOrEqual(g.dlo[3][0])
    }
    // B 柱严格落在 DLO 水平跨度内（55% 插值朝车尾方向）
    expect(g.pillar.x).toBeLessThan(P.windshieldTopX)
    expect(g.pillar.x).toBeGreaterThan(g.dloTopRear)
  })
})
