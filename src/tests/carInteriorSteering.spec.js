import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import { deriveInteriorLayout } from '../utils/carInteriorLayout.js'
import { carTypeParams } from '../config/carPresets.js'
import { createSteeringWheel } from '../utils/carInterior.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type) => deriveCarProfile({ ...carTypeParams[type] }, type)

/** 取轮面（局部 XY 平面）与三根辐条网格 */
const wheelPartsOf = (P) => {
  const group = createSteeringWheel(P)
  const plane = group.children.find((c) => c.isGroup)
  expect(plane).toBeTruthy()
  const spokes = plane.children.filter((c) => c.isMesh && c.geometry?.type === 'BoxGeometry')
  return { sw: deriveInteriorLayout(P).steerWheel, spokes }
}

/** 辐条两端在轮面局部坐标中的位置：rotation.z=a 将局部 +Y 映射为 (-sin a, cos a) */
const endsOf = (spoke) => {
  const a = spoke.rotation.z
  const dir = { x: -Math.sin(a), y: Math.cos(a) }
  const half = spoke.geometry.parameters.height / 2
  const c = spoke.position
  return {
    inner: { x: c.x - dir.x * half, y: c.y - dir.y * half },
    outer: { x: c.x + dir.x * half, y: c.y + dir.y * half }
  }
}

const radiusOf = (p) => Math.hypot(p.x, p.y)
const angleOf = (p) => (Math.atan2(p.y, p.x) * 180) / Math.PI

describe('createSteeringWheel — 三辐几何', () => {
  it.each(ALL_TYPES)('%s 三根辐条均自轮毂发出（内端半径 ≤ 轮毂半径）', (type) => {
    const { spokes } = wheelPartsOf(profileOf(type))
    expect(spokes.length).toBe(3)
    for (const spoke of spokes) {
      // 轮毂半径 0.032；留 0.012 容差覆盖辐条宽度/建模误差
      expect(radiusOf(endsOf(spoke).inner)).toBeLessThanOrEqual(0.044)
    }
  })

  it.each(ALL_TYPES)('%s 三根辐条外端贴在轮圈上（半径 ≈ steerWheel.r）', (type) => {
    const { sw, spokes } = wheelPartsOf(profileOf(type))
    for (const spoke of spokes) {
      expect(radiusOf(endsOf(spoke).outer)).toBeCloseTo(sw.r, 2)
    }
  })

  it.each(ALL_TYPES)('%s 外端方位为 12/4/8 点钟：互差 120° 且下侧两根左右对称', (type) => {
    const { spokes } = wheelPartsOf(profileOf(type))
    const angles = spokes.map((s) => angleOf(endsOf(s).outer)).sort((a, b) => a - b)
    // 期望 -150 / -30 / 90（即 4 点、8 点、12 点方向）
    expect(angles[0]).toBeCloseTo(-150, 0)
    expect(angles[1]).toBeCloseTo(-30, 0)
    expect(angles[2]).toBeCloseTo(90, 0)
    // 相邻辐条夹角 120°
    expect(angles[1] - angles[0]).toBeCloseTo(120, 0)
    expect(angles[2] - angles[1]).toBeCloseTo(120, 0)
    // 下侧两根镜像：|x| 相等、y 相等（无重叠汇聚）
    const outers = spokes.map((s) => endsOf(s).outer)
    const lower = outers.filter((p) => p.y < 0)
    expect(lower.length).toBe(2)
    expect(Math.abs(lower[0].x)).toBeCloseTo(Math.abs(lower[1].x), 6)
    expect(lower[0].y).toBeCloseTo(lower[1].y, 6)
    expect(lower[0].x).not.toBeCloseTo(lower[1].x, 6)   // 不得退化为同一根
  })
})
