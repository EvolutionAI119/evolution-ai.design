/**
 * NURBS 早退路径行为测试（P6 收口）
 *
 * 锁死 assembleCar 的 NURBS 分支契约：有 nurbsMesh 时不建门、不建升力装置——
 * doorHinges / doorSeams 必须是空数组、liftLayout 必须显式 null，车组内不得出现
 * door-hinge-* / door-seam 等门几何。任何后续重构若把门装配或升降布局漏进 NURBS
 * 分支，这里会直接失败。
 */

import { describe, it, expect } from 'vitest'
import { assembleCar } from '../three/assembly/assembleCar.js'
import { defaultCarParams, carTypeParams } from '../config/carPresets'

/** 最小后端网格：1 片 2×2 车身面 + 1 轮，足以走完 NURBS 构建与对齐 */
function fakeNurbsMesh() {
  return {
    parts: [{
      type: 'body_shell',
      points: [
        [[0, -800, 0], [0, 800, 0]],
        [[4000, -800, 800], [4000, 800, 800]]
      ]
    }],
    wheels: [{ radius: 340, width: 220, position: { x: 1000, y: 340, z: 0 } }]
  }
}

function buildNurbs() {
  return assembleCar({
    carParams: { ...defaultCarParams, ...carTypeParams.sedan },
    carType: 'sedan',
    carColor: '#4ade80',
    wireframe: false,
    nurbsMesh: fakeNurbsMesh()
  })
}

describe('assembleCar NURBS 早退路径', () => {
  it('返回空 doorHinges / doorSeams，liftLayout 显式为 null', () => {
    const built = buildNurbs()

    // 严格锁死为空数组（不是 undefined/null）：动画层直接调 hinges.length
    expect(built.doorHinges).toEqual([])
    expect(built.doorSeams).toEqual([])
    expect(built.liftLayout).toBeNull()
    expect(built.group).toBeTruthy()
  })

  it('车组内不建门组与门缝几何', () => {
    const built = buildNurbs()

    const hingeNodes = []
    const doorMeshes = []
    built.group.traverse((o) => {
      if (o.name?.startsWith('door-hinge-')) hingeNodes.push(o)
      if (o.isMesh && (o.name === 'door-seam' || o.name === 'door-inner-trim')) doorMeshes.push(o)
    })

    expect(hingeNodes).toHaveLength(0)
    expect(doorMeshes).toHaveLength(0)
  })
})
