import * as THREE from 'three'
import { BODY_BEVEL_SIZE } from '../../utils/carGlass.js'

/**
 * 保险杠 + 前大灯 + 尾灯（P2 拆分：原 Car3D.vue 的保险杠/灯组段）
 *
 * 只做贴面装配，不做坐标推导：车宽/前后立面 X/门槛高/机盖与行李舱线全部由
 * carProfile 派生后显式传入；轮廓点只读，模块内不改写。
 * 材质在模块内新建（不接 materials.js 缓存），wireframe 为调用方快照的布尔，
 * 模块不读组件响应式状态。
 *
 * 坐标常量是本段最容易回归的部分，逐字保留：
 * - 保险杠 X = frontX + 0.005 / rearX − 0.005（±5mm 决定车身 X 向包围盒外沿）；
 * - 大灯立面 X = noseXAt(hlY) + BODY_BEVEL_SIZE − lensT/2 + 0.006；
 * - noseXAt 的 0.06 纵向取样容差；
 * - 尾灯 Z 复用头灯 hlZ（单一来源），不另起推导。
 */
export function createLightsBumpers({
  parent,
  W,
  frontX,
  rearX,
  bodyBottomY,
  hoodLineY,
  trunkLineY,
  wall,
  outlineShape,
  bodyMat,
  wireframe = false
}) {
  // ---- 保险杠：贴前/后立面外表面（旧值埋在车身实体内不可见，已修正）----
  const bumperGeom = new THREE.BoxGeometry(0.05, 0.15, W - 0.10)
  const frontBumper = new THREE.Mesh(bumperGeom, bodyMat)
  frontBumper.position.set(frontX + 0.005, bodyBottomY + 0.075, 0)
  parent.add(frontBumper)

  const rearBumper = new THREE.Mesh(bumperGeom, bodyMat)
  rearBumper.position.set(rearX - 0.005, bodyBottomY + 0.075, 0)
  parent.add(rearBumper)

  // ---- 前大灯：贴合前立面外表面 ----
  // 前立面并非平面：轮廓在机盖高度处前凸到 frontX+0.02 附近，且挤出 bevel 再外扩
  // BODY_BEVEL_SIZE。旧实现把灯盒中心放在 frontX（仅突出 25mm）→ 整颗灯埋在
  // 前脸实体内部，前视完全看不到。此处按灯高处的轮廓前缘 + bevel 求真实立面 X，
  // 灯罩只露 6mm，读作嵌入式灯组而非外挂方块。
  const noseXAt = (y, halfRange = 0.06) => {
    let maxX = frontX
    for (const p of outlineShape) {
      if (Math.abs(p.y - y) <= halfRange && p.x > maxX) maxX = p.x
    }
    return maxX
  }
  const headlightMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xffffcc,
    emissiveIntensity: 0.5,
    wireframe
  })
  const hlY = Math.max(hoodLineY - 0.16, bodyBottomY + 0.16)
  // 灯组内移：外侧端不得越过前脸的倒角圆角，否则灯罩会从前脸棱角"穿出去"
  // 在翼子板转角处露出一块白斑
  const hlZ = wall - 0.27
  const lensT = 0.016
  const headlightGeom = new THREE.BoxGeometry(lensT, 0.10, 0.24)
  const hlX = noseXAt(hlY) + BODY_BEVEL_SIZE - lensT / 2 + 0.006
  const hl1 = new THREE.Mesh(headlightGeom, headlightMat)
  hl1.position.set(hlX, hlY, hlZ)
  parent.add(hl1)
  const hl2 = new THREE.Mesh(headlightGeom, headlightMat)
  hl2.position.set(hlX, hlY, -hlZ)
  parent.add(hl2)

  // ---- 尾灯：嵌于后立面（与大灯同口径修正）----
  const taillightMat = new THREE.MeshStandardMaterial({
    color: 0xff0000,
    emissive: 0xff0000,
    emissiveIntensity: 0.4,
    wireframe
  })
  const taillightGeom = new THREE.BoxGeometry(0.04, 0.10, 0.20)
  const tlY = Math.max(trunkLineY - 0.18, bodyBottomY + 0.16)
  const tl1 = new THREE.Mesh(taillightGeom, taillightMat)
  tl1.position.set(rearX, tlY, hlZ)
  parent.add(tl1)
  const tl2 = new THREE.Mesh(taillightGeom, taillightMat)
  tl2.position.set(rearX, tlY, -hlZ)
  parent.add(tl2)
}
