import { describe, it, expect } from 'vitest'
import * as THREE from 'three'
import { deriveCarProfile } from '../utils/carProfile.js'
import { carTypeParams } from '../config/carPresets.js'
import {
  createSeatRow, SEAT_MATERIAL_PRESETS, SEAT_PRESET_BY_CAR_TYPE, resolveSeatPreset
} from '../utils/carInterior.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type, extra) => deriveCarProfile({ ...carTypeParams[type], ...extra }, type)

/** 收集一排内的座组（userData.part === 'seat'） */
const seatGroupsOf = (rowGroup) => rowGroup.children.filter((c) => c.userData?.part === 'seat')

/** 收集一排内所有 mesh */
const meshesOf = (rowGroup) => {
  const out = []
  rowGroup.traverse((o) => { if (o.isMesh) out.push(o) })
  return out
}

describe('createSeatRow — 排/座数量与 carProfile 布局一致', () => {
  it.each(ALL_TYPES)('%s 每排座数 = seatRowCounts，总座数 = seatTotal', (type) => {
    const P = profileOf(type)
    let total = 0
    for (let row = 1; row <= P.seatRows; row++) {
      const g = createSeatRow(P, row)
      expect(g.name).toBe(`seat-row-${row}`)
      expect(g.userData.part).toBe('seat-row')
      expect(g.userData.row).toBe(row)
      const seats = seatGroupsOf(g)
      expect(seats.length).toBe(P.seatRowCounts[row - 1])
      expect(g.userData.count).toBe(P.seatRowCounts[row - 1])
      total += seats.length
    }
    expect(total).toBe(P.seatTotal)
  })

  it('第二排 3 座（bench）标签为 left/mid/right，2 座为 left/right，前排为 driver/passenger', () => {
    const P = profileOf('sedan')
    const row1 = createSeatRow(P, 1)
    expect(seatGroupsOf(row1).map((s) => s.userData.position)).toEqual(['driver', 'passenger'])
    const row2 = createSeatRow(P, 2)
    expect(seatGroupsOf(row2).map((s) => s.userData.position)).toEqual(['left', 'mid', 'right'])

    const coupe = profileOf('coupe')
    const coupeRow2 = createSeatRow(coupe, 2)
    expect(seatGroupsOf(coupeRow2).map((s) => s.userData.position)).toEqual(['left', 'right'])
  })
})

describe('createSeatRow — 越界排号返回空组（不得回落到相邻排）', () => {
  it('sport 请求第二排返回空组', () => {
    const P = profileOf('sport')
    const g = createSeatRow(P, 2)
    expect(g.children.length).toBe(0)
    expect(g.userData.count).toBe(0)
    expect(g.name).toBe('seat-row-2')
  })

  it('sedan 请求第 5 排 / 第 0 排 / 负排 均返回空组', () => {
    const P = profileOf('sedan')
    for (const bad of [5, 0, -1]) {
      const g = createSeatRow(P, bad)
      expect(g.children.length).toBe(0)
      expect(seatGroupsOf(g).length).toBe(0)
    }
  })
})

describe('createSeatRow — 座椅几何不越出座舱包络', () => {
  it.each(ALL_TYPES)('%s 所有座椅落在车身 X/Y/Z 包络内且低于车顶', (type) => {
    const P = profileOf(type)
    for (let row = 1; row <= P.seatRows; row++) {
      const g = createSeatRow(P, row)
      const box = new THREE.Box3().setFromObject(g)
      expect(box.isEmpty()).toBe(false)
      // X：不得超出车头/车尾立面
      expect(box.max.x).toBeLessThan(P.frontX)
      expect(box.min.x).toBeGreaterThan(P.rearX)
      // Y：不得高于车顶，不得低于地面
      expect(box.max.y).toBeLessThan(P.roofTopY)
      expect(box.min.y).toBeGreaterThan(0)
      // Z：不得超出发车身半宽
      expect(box.max.z).toBeLessThan(P.W / 2)
      expect(box.min.z).toBeGreaterThan(-P.W / 2)
    }
  })

  it.each(ALL_TYPES)('%s 排位随排号向车尾递减', (type) => {
    const P = profileOf(type)
    const xs = []
    for (let row = 1; row <= P.seatRows; row++) {
      xs.push(seatGroupsOf(createSeatRow(P, row))[0].position.x)
    }
    for (let i = 1; i < xs.length; i++) expect(xs[i]).toBeLessThan(xs[i - 1])
  })

  it('H 点高度按排取 seatHPointFront / seatHPointRear', () => {
    const P = profileOf('sedan')
    const row1 = seatGroupsOf(createSeatRow(P, 1))
    const row2 = seatGroupsOf(createSeatRow(P, 2))
    row1.forEach((s) => expect(s.position.y).toBeCloseTo(P.seatHPointFront, 6))
    row2.forEach((s) => expect(s.position.y).toBeCloseTo(P.seatHPointRear, 6))
  })

  it('驾驶位位于 Z 负侧（左舵：-Z = 驾驶员侧）', () => {
    const P = profileOf('sedan')
    const driver = seatGroupsOf(createSeatRow(P, 1)).find((s) => s.userData.isDriver)
    expect(driver).toBeTruthy()
    expect(driver.position.z).toBeLessThan(0)
  })

  it('皮卡第二排贴近驾驶室后壁（不按轿车排距后移）', () => {
    const P = profileOf('pickup')
    const row2 = seatGroupsOf(createSeatRow(P, 2))[0]
    expect(row2.position.x).toBeCloseTo(P.pickup.cabRearX + 0.28, 6)
  })
})

describe('createSeatRow — 渲染契约（阴影/层级/无贴图）', () => {
  it.each(ALL_TYPES)('%s 座椅不投外观阴影、接收阴影、renderOrder=2', (type) => {
    const P = profileOf(type)
    for (let row = 1; row <= P.seatRows; row++) {
      for (const mesh of meshesOf(createSeatRow(P, row))) {
        expect(mesh.castShadow).toBe(false)
        expect(mesh.receiveShadow).toBe(true)
        expect(mesh.renderOrder).toBe(2)
        // Car3D.updateCar() 以该标记统一重设投影
        expect(mesh.userData.noCastShadow).toBe(true)
      }
    }
  })

  it('材质无贴图依赖（沿用整车无 UV 体系）', () => {
    const P = profileOf('sedan')
    for (const mesh of meshesOf(createSeatRow(P, 1))) {
      expect(mesh.material.map).toBeNull()
      expect(mesh.material.alphaMap).toBeNull()
      expect(mesh.material.isMeshStandardMaterial).toBe(true)
    }
  })

  it('同排各座共享同一套几何（3 座不产生 3 倍几何对象）', () => {
    const P = profileOf('sedan')
    const row2 = createSeatRow(P, 2)
    const cushionGeoms = new Set()
    row2.traverse((o) => { if (o.isMesh && o.name === 'seat-cushion') cushionGeoms.add(o.geometry) })
    expect(cushionGeoms.size).toBe(1)
    expect(seatGroupsOf(row2).length).toBe(3)
  })

  it('单座含坐垫/靠背/头枕/双侧翼五件，靠背枢轴锚在 H 点', () => {
    const P = profileOf('sedan')
    const seat = seatGroupsOf(createSeatRow(P, 1))[0]
    const names = []
    seat.traverse((o) => { if (o.isMesh) names.push(o.name) })
    expect(names.sort()).toEqual([
      'seat-backrest', 'seat-bolster-left', 'seat-bolster-right', 'seat-cushion', 'seat-headrest'
    ].sort())
    const pivot = seat.getObjectByName('seat-backrest-pivot')
    expect(pivot.position.toArray()).toEqual([0, 0, 0])
    expect(pivot.rotation.z).toBeGreaterThan(0)   // 正倾角 = 顶部向车尾
  })
})

describe('createSeatRow — 材质预设解析', () => {
  it('车型默认预设覆盖全部 6 车型', () => {
    for (const type of ALL_TYPES) {
      expect(SEAT_PRESET_BY_CAR_TYPE[type]).toBeDefined()
      expect(SEAT_MATERIAL_PRESETS[SEAT_PRESET_BY_CAR_TYPE[type]]).toBeDefined()
    }
  })

  it('车型参数显式指定优先；非法值与未知车型回退 standard', () => {
    expect(resolveSeatPreset('suv', { interior: { material_preset: 'luxury' } })).toBe('luxury')
    expect(resolveSeatPreset('suv', { interior: { material_preset: 'bogus' } })).toBe('standard')
    expect(resolveSeatPreset('sport', {})).toBe('sport')
    expect(resolveSeatPreset('unknown', {})).toBe('standard')
    expect(resolveSeatPreset('unknown', { interior: { material_preset: 'executive' } })).toBe('executive')
  })

  it('materialVariant 透传至排组与单座 userData', () => {
    const P = profileOf('mpv')
    const g = createSeatRow(P, 1, { materialVariant: 'luxury' })
    expect(g.userData.materialVariant).toBe('luxury')
    seatGroupsOf(g).forEach((s) => expect(s.userData.materialVariant).toBe('luxury'))
  })

  it('非法 materialVariant 回退 standard 且不抛错', () => {
    const P = profileOf('sedan')
    const g = createSeatRow(P, 1, { materialVariant: 'nope' })
    expect(g.userData.materialVariant).toBe('standard')
    expect(seatGroupsOf(g).length).toBe(2)
  })
})
