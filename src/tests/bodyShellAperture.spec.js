import { describe, it, expect } from 'vitest'
import * as THREE from 'three'
import { carTypeParams } from '../config/carPresets.js'
import { deriveCarProfile, deriveDoorLayout } from '../utils/carProfile.js'
import { deriveCabinGlass, deriveDloPaneRanges } from '../utils/carGlass.js'
import { buildBodyShell } from '../three/geometry/bodyShell.js'
import { splitTrianglesAtAbsZ } from '../three/geometry/smoothing.js'
import { createMaterialSet } from '../three/materials.js'

const TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']

/** 逐三角形面法线（位置叉积归一化） */
function faceNormal(arr, o) {
  const e1x = arr[o + 3] - arr[o], e1y = arr[o + 4] - arr[o + 1], e1z = arr[o + 5] - arr[o + 2]
  const e2x = arr[o + 6] - arr[o], e2y = arr[o + 7] - arr[o + 1], e2z = arr[o + 8] - arr[o + 2]
  let nx = e1y * e2z - e1z * e2y
  let ny = e1z * e2x - e1x * e2z
  let nz = e1x * e2y - e1y * e2x
  const l = Math.hypot(nx, ny, nz) || 1
  return [nx / l, ny / l, nz / l]
}

function shellFor(type) {
  const P = deriveCarProfile({ ...carTypeParams[type] }, type)
  const cabin = deriveCabinGlass(P, { carType: type })
  const dl = deriveDoorLayout(P, cabin, { carType: type })
  const paneRanges = deriveDloPaneRanges(dl, 8)
  return buildBodyShell({ P, carType: type, cabin, doorLayout: dl, paneRanges })
}

describe('车身壳洞口内饰化：只改判洞内竖壁，不污染可见漆面', () => {
  for (const type of TYPES) {
    it(`${type}：内饰组不含外蒙皮/水平洞口壁三角形`, () => {
      const geom = shellFor(type).bodyGeom
      const group = geom.groups.find((g) => g.materialIndex === 1)
      expect(group).toBeTruthy()
      const arr = geom.attributes.position.array
      const startTri = group.start / 3
      const nTri = group.count / 3
      let sideFacing = 0
      let upHorizontal = 0
      for (let t = startTri; t < startTri + nTri; t++) {
        const o = t * 9
        const n = faceNormal(arr, o)
        // 端盖/倒角外蒙皮（侧视可见的车漆面）绝不能被改判为深色内饰
        if (Math.abs(n[2]) > 0.6) sideFacing++
        // 洞口上沿/门槛顶面这类**朝上的水平面**从车外俯视可见，必须保持车漆色。
        // 只认朝上（ny > 0）：朝下的水平薄片（如风挡下沿的翻边底面）从车外看不到，
        // 判成舱内深色是合理的；同时排除风挡/后风挡斜面暗舱底——斜面顶点 y 沿 X 渐变，
        // 虽然 |ny| 也可能 >0.8（25° 斜面 ny≈0.91），但不是水平面。
        const yMin = Math.min(arr[o + 1], arr[o + 4], arr[o + 7])
        const yMax = Math.max(arr[o + 1], arr[o + 4], arr[o + 7])
        if (n[1] > 0.8 && yMax - yMin < 1e-3) upHorizontal++
      }
      expect(sideFacing).toBe(0)
      expect(upHorizontal).toBe(0)
      // 仍应保留一定量的洞内竖壁（否则等于没做内饰化）
      expect(nTri).toBeGreaterThan(20)
    })
  }
})

describe('车身漆面与内饰材质：锁住「一直存在的黑楔形」修复', () => {
  it('bodyMat 双面渲染（ExtrudeGeometry 扫掠壁绕序不总朝外，单面会被背面剔除成纯黑块）', () => {
    const set = createMaterialSet({ carColor: '#4ade80', wireframe: false })
    expect(set.bodyMat.side).toBe(THREE.DoubleSide)
    // 车身 group 顺序固定 [bodyMat, interiorMat]：调换会让洞内壁变成车漆色
    expect(set.bodyMats[0]).toBe(set.bodyMat)
    expect(set.bodyMats[1]).toBe(set.interiorMat)
    expect(set.interiorMat.side).toBe(THREE.DoubleSide)
  })
})

describe('splitTrianglesAtAbsZ：整宽洞壁按 |z| 切分外环带与内腔', () => {
  it('切开横跨 ±zLim 的三角形且面积守恒、绕序不变', () => {
    const geom = new THREE.BufferGeometry()
    // 一个横跨全宽（z 从 -1 到 +1）的三角形，平面 y=0 上的一点在 z=0
    geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array([
      0, 0, -1,
      1, 0, 1,
      1, 2, 1
    ]), 3))
    const beforeArea = 0.5 * Math.hypot(2, 0, 0) * 2 // 底 2 × 高 2 ⇒ 2（占位，下面按三角形算）
    void beforeArea
    const areaOf = (g) => {
      const a = g.attributes.position.array
      let sum = 0
      for (let o = 0; o < a.length; o += 9) {
        const ux = a[o + 3] - a[o], uy = a[o + 4] - a[o + 1], uz = a[o + 5] - a[o + 2]
        const vx = a[o + 6] - a[o], vy = a[o + 7] - a[o + 1], vz = a[o + 8] - a[o + 2]
        sum += Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2
      }
      return sum
    }
    const areaBefore = areaOf(geom)
    const zLim = 0.5
    splitTrianglesAtAbsZ(geom, zLim)
    const after = geom.attributes.position.array
    // 1) 面积守恒（切分不增不减材质）
    expect(areaOf(geom)).toBeCloseTo(areaBefore, 6)
    // 2) 不再有三角形跨越切面
    for (let o = 0; o < after.length; o += 9) {
      const zs = [after[o + 2], after[o + 5], after[o + 8]]
      const inner = zs.every((z) => Math.abs(z) <= zLim + 1e-6)
      const outer = zs.every((z) => Math.abs(z) >= zLim - 1e-6)
      expect(inner || outer).toBe(true)
    }
    // 3) 绕序保持（法线方向与原三角形一致朝向 +y/-y）
    const n0 = faceNormal(new Float32Array([0, 0, -1, 1, 0, 1, 1, 2, 1]), 0)
    for (let o = 0; o < after.length; o += 9) {
      const n = faceNormal(after, o)
      expect(n[2] * n0[2] >= -1e-9).toBe(true)
    }
  })
})
