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
  mesh.userData.noCastShadow = true   // 装配层 applyShadowFlags 遍历时据此关掉投影
  return mesh
}

/**
 * 车门装置（P2 拆分：原 Car3D.vue `mkDoor` 本体 + 分缝线 + 门片玻璃挂载）
 *
 * 职责：生成前后门分缝条、门板、门把手、门内板，并把侧窗门片玻璃重挂到对应铰链。
 * 组装完成后返回 `{ hinges, seams }`，由调用方持有引用供动画逐帧读取旋转/显隐。
 *
 * 只做几何组装，不推导坐标：所有 X/Y 基准（分缝、把手、门洞上下缘）均由
 * carProfile / carGlass 的真源经调用方算好后以入参传入，本模块不做二次换算。
 *
 * 运动学约定（拆分前后一致）：
 * - 铰链轴为竖直轴，position = (hingeX, 0, zSide·wall)，动画只写 `rotation.y`；
 * - 门板宽 = 缝到缝 − 4mm（门洞内缩 8mm → 四缘叠压 2mm），关门时是唯一门几何；
 * - 门片玻璃把几何按铰链轴平移后挂到同名铰链，与门板同轴同角度外摆；
 * - 门缝条独立于铰链挂在车身，开门时隐藏（否则悬在空洞中央遮挡视线）。
 */
export function createDoorRig({
  parent,
  wall,
  doorLayout,
  bodyBottomY,
  shoulderY,
  bodyMat,
  chromeMat,
  doorSeamWidth = 8,
  doorGlass = [],
  wireframe = false
}) {
  const dl = doorLayout
  // 分缝线：前缝/B柱缝/后缝 竖向暗色薄槽（sill→腰带线）
  const seamMat = new THREE.MeshStandardMaterial({ color: 0x08080c, metalness: 0.3, roughness: 0.8, wireframe })
  const doorMat = bodyMat   // 门板与车身共用同一车漆，避免腰线两侧高光/色差断裂
  const handleGeom = new THREE.BoxGeometry(0.14, 0.022, 0.02)
  const doorBottom = bodyBottomY + 0.02
  // 门板顶边 = 玻璃洞口肩线（而非腰带线）：合并门洞从门槛一直开到玻璃底，
  // 门板必须同样覆盖到肩线，否则关门时腰带线到玻璃底之间留一条 24mm 横缝。
  const doorTop = shoulderY
  const doorH = doorTop - doorBottom
  const seamW = doorSeamWidth / 1000
  const hinges = []
  const seams = []

  const addSeam = (x) => {
    for (const zSide of [1, -1]) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(seamW, doorH, 0.004), seamMat)
      s.name = 'door-seam'
      s.position.set(x, doorBottom + doorH / 2, zSide * (wall + 0.002))
      parent.add(s)
      seams.push(s)   // 开门时随动画隐藏：否则细缝条会悬在空洞中央形成遮挡
    }
  }
  addSeam(dl.frontSeamX); addSeam(dl.midSeamX)
  if (dl.rearSeamX !== null) addSeam(dl.rearSeamX)

  // 门板 + 铰链（常规前铰：前门铰链在前缝、后门铰链在 B柱缝，均向后开）
  // 门板宽度 = 缝到缝 − 4mm：门洞（缝到缝 − 8mm）四缘被门板叠压 2mm → 门板是全车
  // 唯一门几何且关门严密封闭；门缝观感由门洞边缘内缩的深色洞壁读出（真车 shut line）。
  const mkDoor = (key, hingeX, leadX, trailX, handleX, zSide) => {
    const hinge = new THREE.Group()
    // 具名：视觉基线/调试按名定位门铰链（不改运动学，仅便于外部读取）
    hinge.name = `door-hinge-${key}-${zSide > 0 ? 'right' : 'left'}`
    hinge.position.set(hingeX, 0, zSide * wall)
    const w = Math.max(Math.abs(trailX - leadX) - 0.004, 0.05)   // X+ 朝车头：leading 边 X 更大，取绝对宽
    const panel = new THREE.Mesh(new THREE.BoxGeometry(w, doorH, 0.012), doorMat)
    panel.position.set((leadX + trailX) / 2 - hingeX, doorBottom + doorH / 2, zSide * 0.006)
    panel.castShadow = true
    hinge.add(panel)
    const h = new THREE.Mesh(handleGeom, chromeMat)
    h.position.set(handleX - hingeX, dl.handleY, zSide * 0.016)
    hinge.add(h)
    // 门内板补面（D-1 B 方案）：内饰面 + 门槛过渡 + 扶手托板，随铰链同角度开合
    hinge.add(createDoorInnerPanel({
      width: w, height: doorH, offsetX: (leadX + trailX) / 2 - hingeX,
      bottomY: doorBottom, zSide, wireframe
    }))
    parent.add(hinge)
    hinges.push({ hinge, sign: zSide, key })
  }
  for (const zSide of [1, -1]) {
    mkDoor('front', dl.frontSeamX, dl.frontSeamX, dl.midSeamX, dl.frontHandleX, zSide)
    if (dl.rearSeamX !== null) mkDoor('rear', dl.midSeamX, dl.midSeamX, dl.rearSeamX, dl.rearHandleX, zSide)
  }

  // 侧窗门片挂到对应车门铰链：几何按铰链轴平移（几何原为世界坐标），
  // 之后与门板同轴同角度旋转 → 玻璃随门一同打开、与门板上下沿严格对齐
  for (const dg of doorGlass) {
    const target = hinges.find((d) => d.key === dg.key && d.sign === dg.zSide)
    if (!target) continue
    dg.mesh.geometry.translate(-target.hinge.position.x, 0, -target.hinge.position.z)
    target.hinge.add(dg.mesh)
  }

  return { hinges, seams }
}
