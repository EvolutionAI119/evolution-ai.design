import { describe, it, expect } from 'vitest'
import * as THREE from 'three'
import { disposeMaterial, disposeObject } from '../three/dispose.js'

describe('资源释放（P2 materials 收口：幂等保护）', () => {
  it('同一材质被多个 mesh 引用时只释放一次', () => {
    const mat = new THREE.MeshStandardMaterial()
    let n = 0
    mat.addEventListener('dispose', () => { n++ })
    const geo = new THREE.BoxGeometry(1, 1, 1)
    const group = new THREE.Group()
    for (let i = 0; i < 3; i++) group.add(new THREE.Mesh(geo, mat))
    disposeObject(group)
    expect(n).toBe(1)
  })

  it('共享贴图（alphaMap）跨材质只释放一次', () => {
    const tex = new THREE.Texture()
    let n = 0
    tex.addEventListener('dispose', () => { n++ })
    const a = new THREE.MeshStandardMaterial({ alphaMap: tex })
    const b = new THREE.MeshStandardMaterial({ alphaMap: tex })
    const group = new THREE.Group()
    group.add(new THREE.Mesh(new THREE.PlaneGeometry(1, 1), a))
    group.add(new THREE.Mesh(new THREE.PlaneGeometry(1, 1), b))
    disposeObject(group)
    expect(n).toBe(1)
  })

  it('同一几何被多个 mesh 复用只释放一次（含根节点自身不重复）', () => {
    const geo = new THREE.BoxGeometry(1, 1, 1)
    let n = 0
    geo.addEventListener('dispose', () => { n++ })
    const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial())
    mesh.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial()))
    disposeObject(mesh)
    expect(n).toBe(1)
  })

  it('disposeMaterial 独立调用时同样幂等（默认新建会话集合）', () => {
    const mat = new THREE.MeshStandardMaterial()
    let n = 0
    mat.addEventListener('dispose', () => { n++ })
    disposeMaterial(mat)
    disposeMaterial(mat)
    expect(n).toBe(2)   // 两次独立会话各释放一次（互不影响），但会话内不重复
    const tex = new THREE.Texture()
    let t = 0
    tex.addEventListener('dispose', () => { t++ })
    const seen = new WeakSet()
    disposeMaterial(new THREE.MeshStandardMaterial({ alphaMap: tex }), seen)
    disposeMaterial(new THREE.MeshStandardMaterial({ alphaMap: tex }), seen)
    expect(t).toBe(1)
  })
})
