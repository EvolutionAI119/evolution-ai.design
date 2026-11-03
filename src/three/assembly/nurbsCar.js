import * as THREE from 'three'
import { deriveNurbsFrame } from '../../utils/carProfile.js'

/**
 * NURBS 高位路径（P5 批次 1）：后端真实采样网格 → three 几何。
 *
 * 与挤出路径（geometry/bodyShell.js）**不共享任何状态**：本模块不读 props/ref，
 * 车色与线框按布尔/字符串显式传入；NURBS 路径不建门、不建升力装置——
 * 调用方据此把 doorHinges / liftLayout 显式置空。
 */

/**
 * 从后端 NURBS 采样网格构建高保真汽车（真实曲面，替代 ExtrudeGeometry 近似）
 *
 * 坐标映射：后端 canonical（X=车长, Y=车宽, Z=车高, mm）
 *           → three（x=车长, y=高, z=宽, m）
 *
 * @param {Object} mesh 后端网格 { parts, wheels }
 * @param {Object} opts
 * @param {string} opts.carColor 车漆件选色（BODY COLOR 面板）
 * @param {boolean} opts.wireframe 线框快照（构建期布尔，不持有 ref）
 * @returns {THREE.Group}
 */
export function createNurbsCar(mesh, { carColor, wireframe }) {
  const group = new THREE.Group()
  const M = 0.001

  for (const part of mesh.parts || []) {
    const pts = part.points
    if (!pts || pts.length < 2 || !pts[0] || pts[0].length < 2) continue
    const nu = pts.length
    const nv = pts[0].length
    const positions = new Float32Array(nu * nv * 3)
    let k = 0
    for (let i = 0; i < nu; i++) {
      for (let j = 0; j < nv; j++) {
        const p = pts[i][j]
        positions[k++] = p[0] * M   // X 车长
        positions[k++] = p[2] * M   // Z 车高 → three.y
        positions[k++] = p[1] * M   // Y 车宽 → three.z
      }
    }
    const indices = []
    for (let i = 0; i < nu - 1; i++) {
      for (let j = 0; j < nv - 1; j++) {
        const a = i * nv + j
        const b = i * nv + j + 1
        const c = (i + 1) * nv + j
        const d = (i + 1) * nv + j + 1
        indices.push(a, b, c, b, d, c)
      }
    }
    const geom = new THREE.BufferGeometry()
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geom.setIndex(indices)
    geom.computeVertexNormals()   // 共享顶点 → 平滑法线

    const isGlass = part.type === 'windshield' || part.type === 'rear_window'
      || part.type === 'side_glass'
    // 车漆件：BODY COLOR 面板选色优先（灯具/格栅/保险杠保留后端本色）
    const PAINT_TYPES = new Set(['body_shell', 'hood', 'roof', 'trunk', 'door', 'fender'])
    const isPaint = PAINT_TYPES.has(part.type)
    const paintColor = (isPaint && carColor) || part.color || carColor
    const material = isGlass
      ? new THREE.MeshPhysicalMaterial({
          color: part.color || '#a8c4cc',
          transparent: true,
          opacity: part.opacity ?? 0.25,
          metalness: 0,
          roughness: 0.08,
          envMapIntensity: 0.6,
          side: THREE.DoubleSide,
          depthWrite: false,
          wireframe
        })
      : new THREE.MeshPhysicalMaterial({
          color: paintColor,
          metalness: 0.72,
          roughness: 0.28,
          clearcoat: 1.0,
          clearcoatRoughness: 0.06,
          envMapIntensity: 1.5,
          side: THREE.DoubleSide,
          wireframe
        })
    const meshObj = new THREE.Mesh(geom, material)
    meshObj.castShadow = true
    meshObj.receiveShadow = true
    group.add(meshObj)
  }

  for (const w of mesh.wheels || []) {
    group.add(createNurbsWheel(w))
  }
  return group
}

/** 后端 wheel 部件 → three 轮子组（位置字典为 author 约定：y=高, z=宽） */
export function createNurbsWheel(w) {
  const M = 0.001
  const g = new THREE.Group()
  const r = w.radius * M
  const width = (w.width || 200) * M

  const tireGeom = new THREE.CylinderGeometry(r, r, width, 40)
  tireGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    tireGeom,
    new THREE.MeshStandardMaterial({ color: 0x26262b, metalness: 0.1, roughness: 0.85 })))

  // 轮毂/轮芯端面必须比胎面更宽才能外露（否则被轮胎实体完全包住）
  const rimGeom = new THREE.CylinderGeometry(r * 0.62, r * 0.62, width * 1.08, 24)
  rimGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    rimGeom,
    new THREE.MeshStandardMaterial({ color: 0xb8bdc4, metalness: 0.95, roughness: 0.2 })))

  const hubGeom = new THREE.CylinderGeometry(r * 0.18, r * 0.18, width * 1.16, 12)
  hubGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    hubGeom,
    new THREE.MeshStandardMaterial({ color: 0xd8dadd, metalness: 1.0, roughness: 0.15 })))

  const pos = w.position || {}
  g.position.set((pos.x || 0) * M, (pos.y || 0) * M, (pos.z || 0) * M)
  g.traverse((o) => { if (o.isMesh) o.castShadow = true })
  return g
}

/**
 * 将后端 NURBS 网格对齐到 carProfile 的居中坐标系。
 * 数学部分（平移/偏航/等比缩放）在 carProfile.deriveNurbsFrame 中，此处只负责落到 Three 变换上。
 */
export function alignNurbsToProfile(body, mesh, profile) {
  body.updateMatrixWorld(true)
  const box = new THREE.Box3().setFromObject(body)
  if (box.isEmpty()) return { valid: false, scale: 1, flip: false }

  const wheelXs = (mesh.wheels || []).map((w) => (w.position?.x || 0) * 0.001)
  const frame = deriveNurbsFrame(
    { min: { x: box.min.x, y: box.min.y, z: box.min.z },
      max: { x: box.max.x, y: box.max.y, z: box.max.z } },
    wheelXs,
    profile
  )
  if (!frame) return { valid: false, scale: 1, flip: false }

  body.rotation.y = frame.rotationY
  body.scale.setScalar(frame.scale)
  body.position.set(frame.position.x, frame.position.y, frame.position.z)
  body.updateMatrixWorld(true)
  return { valid: true, scale: frame.scale, flip: frame.flip }
}
