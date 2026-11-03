import { describe, it, expect } from 'vitest'
import * as THREE from 'three'
import { createDoorInnerPanel } from '../three/parts/doors.js'

const PARAMS = { width: 0.9, height: 0.8, offsetX: 0.35, bottomY: 0.12 }

const bboxOf = (mesh) => new THREE.Box3().setFromObject(mesh)

describe('门内板补面（D-1 B 方案）', () => {
  it('每门合并为单个 Mesh（draw call = 1）', () => {
    for (const zSide of [1, -1]) {
      const panel = createDoorInnerPanel({ ...PARAMS, zSide })
      expect(panel.isMesh).toBe(true)
      expect(panel.children.length).toBe(0)
      expect(panel.name).toBe('door-inner-trim')
      // 三件 BoxGeometry 合并：3 × 24 顶点 / 3 × 36 索引
      expect(panel.geometry.attributes.position.count).toBe(72)
      expect(panel.geometry.index.count).toBe(108)
    }
  })

  it('完全落在门板包络内：X 不超宽、Y 不超门高', () => {
    for (const zSide of [1, -1]) {
      const b = bboxOf(createDoorInnerPanel({ ...PARAMS, zSide }))
      expect(b.min.x).toBeGreaterThanOrEqual(PARAMS.offsetX - PARAMS.width / 2 - 1e-6)
      expect(b.max.x).toBeLessThanOrEqual(PARAMS.offsetX + PARAMS.width / 2 + 1e-6)
      expect(b.min.y).toBeGreaterThanOrEqual(PARAMS.bottomY - 1e-6)
      expect(b.max.y).toBeLessThanOrEqual(PARAMS.bottomY + PARAMS.height + 1e-6)
    }
  })

  it('实体位于门板内侧（z 朝座舱），不伸出车外', () => {
    for (const zSide of [1, -1]) {
      const b = bboxOf(createDoorInnerPanel({ ...PARAMS, zSide }))
      // 右侧门（zSide=1）内侧为 -Z，左侧门镜像；整体厚度控制在 4cm 内
      expect(b.min.z).toBeLessThan(0)
      expect(b.max.z).toBeGreaterThan(0)
      expect(Math.abs(b.min.z - b.max.z)).toBeLessThan(0.04)
      expect(zSide > 0 ? b.min.z < -0.01 : b.max.z > 0.01).toBe(true)
    }
  })
})
