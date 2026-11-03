import * as THREE from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'

/**
 * 门内板补面（M2 D-1 B 方案）
 *
 * 门板本体是单层车漆薄板（BoxGeometry），开门后从座舱/门洞看过去只有一块同色
 * 薄板。这里在门板内侧补三件深色内饰几何（主饰面 + 门槛过渡 + 扶手托板），
 * 挂在同一铰链下随门同角度开合。
 *
 * 三件几何先按铰链局部坐标烘焙，再合并成**单个 Mesh**：每门 1 次 draw call
 * （4 门共 4 次，满足 D-1「draw call 增量 ≤ 4/车」）。合并后仍复用同一材质。
 *
 * 坐标约定：`offsetX` 为门板中心相对铰链轴的 X 偏移；`zSide` 为 ±1（+1=右侧门）。
 * 内侧方向恒为 `-zSide`（朝座舱）。
 */
export function createDoorInnerPanel({ width, height, offsetX, bottomY, zSide, wireframe = false }) {
  const w = Math.max(width * 0.96, 0.04)
  const h = Math.max(Math.min(height * 0.62, height - 0.1), 0.05)
  const padH = Math.min(h * 0.45, 0.085)
  const inner = -zSide

  const trim = new THREE.BoxGeometry(w, h, 0.006)
    .translate(offsetX, bottomY + h / 2, inner * 0.004)
  const sill = new THREE.BoxGeometry(w, 0.016, 0.028)
    .translate(offsetX, bottomY + 0.008, inner * 0.006)
  const pad = new THREE.BoxGeometry(w * 0.82, padH, 0.02)
    .translate(offsetX, bottomY + h * 0.52, inner * 0.013)

  const merged = mergeGeometries([trim, sill, pad], false)
  trim.dispose(); sill.dispose(); pad.dispose()

  const mesh = new THREE.Mesh(merged, new THREE.MeshStandardMaterial({
    color: 0x2a2d33, metalness: 0.08, roughness: 0.9, wireframe
  }))
  mesh.name = 'door-inner-trim'
  mesh.userData.noCastShadow = true   // initScene 遍历时据此关掉投影
  return mesh
}
