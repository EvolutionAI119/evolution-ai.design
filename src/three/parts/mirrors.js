import * as THREE from 'three'
import { shellHalfZAt } from '../../utils/carGlass.js'

/**
 * 外后视镜（P2 拆分：原 Car3D.vue 的 mirrorGlassAlpha + createMirror）
 *
 * 只做装配：安装点高度（hoodLineY）与机盖末端 X（hoodEndX）由 carProfile 派生后传入；
 * A 柱根部真实侧壁半宽必须走 shellHalfZAt(mountY, dloFrame, bodyExtentZ) 真源，
 * 不能用车身最大半宽代替（否则镜座与车身之间出现悬空缝）。
 *
 * 左右镜像约定：`zSide` 必须显式贯穿镜壳雕刻（pos.getZ(i) * zSide）、housingZ、
 * neck、gasket、镜片位置的每一个 ±z 计算；模块内按 [+1, -1] 顺序挂载。
 *
 * 亚毫米偏移（防 z-fighting，逐字保留，勿统一间隙）：
 * - 底座 `mountZ + 0.002`
 * - 密封圈 `rearTipX - 0.0006`
 * - 镜片 `rearTipX - 0.0024`
 *
 * 贴花：左右两片镜共用同一张 CanvasTexture（每次构建新建一张），不接 materials.js
 * 全局缓存——disposeMaterial 会按材质逐个释放 alphaMap，跨构建共享会重复释放。
 */
export function createMirrors({
  parent,
  hoodLineY,
  hoodEndX,
  bodyMat,
  dloFrame,
  bodyExtentZ,
  wireframe = false
}) {
  // 凸面镜片圆角贴花：两片镜共用一张（disposeObject 统一随材质释放）
  const mirrorGlassAlpha = (() => {
    const c = document.createElement('canvas')
    c.width = 256; c.height = 128
    const ctx = c.getContext('2d')
    ctx.fillStyle = '#000'
    ctx.fillRect(0, 0, 256, 128)
    ctx.fillStyle = '#fff'
    ctx.beginPath()
    ctx.roundRect(5, 5, 246, 118, 24)
    ctx.fill()
    return new THREE.CanvasTexture(c)
  })()

  const createMirror = (zSide) => {
    const mirrorGroup = new THREE.Group()
    // A 柱根部已随 greenhouse 内收，安装点必须取该高度的真实侧壁半宽，
    // 不能仍用车身最大半宽，否则镜座与车身之间会出现悬空缝隙。
    const mountY = hoodLineY + 0.03
    const mountZ = shellHalfZAt(mountY, dloFrame, bodyExtentZ)
    const armLength = 0.025

    const baseGeom = new THREE.SphereGeometry(0.025, 20, 12)
    baseGeom.scale(1.15, 0.7, 0.35)
    const base = new THREE.Mesh(baseGeom, bodyMat)
    base.position.set(0, 0, zSide * (mountZ + 0.002))
    mirrorGroup.add(base)

    const armGeom = new THREE.CylinderGeometry(0.014, 0.011, armLength, 20)
    armGeom.rotateX(Math.PI / 2)
    const arm = new THREE.Mesh(armGeom, bodyMat)
    arm.position.set(0, 0, zSide * (mountZ + armLength / 2))
    mirrorGroup.add(arm)

    // ---- 镜壳：球体雕刻的水滴形壳体（替代圆角盒） ----
    // 旧圆角盒顶面接近平面，顶面高光沿整个平面摊成一条宽亮带。真实镜壳为
    // 曲面壳：舷外渐缩（俯视水滴轮廓）+ 外端底部上挑（气动下切），顶面
    // 高光随曲面法线连续滚转、沿弧面自然衰减——符合物理光照逻辑。
    const housingLength = 0.12    // X：前→后
    const housingHeight = 0.095   // Y：高
    const housingDepth = 0.155    // Z：内→外
    const flatStartX = -housingLength * 0.385  // 尾部拍扁起点
    const flatKeep = 0.25                       // 拍扁保留率（越小越平）
    const housingGeom = new THREE.SphereGeometry(1, 48, 32)
    housingGeom.scale(housingLength / 2, housingHeight / 2, housingDepth / 2)
    {
      const pos = housingGeom.attributes.position
      for (let i = 0; i < pos.count; i++) {
        let x = pos.getX(i)
        let y = pos.getY(i)
        const zOut = pos.getZ(i) * zSide
        const t = Math.min(Math.max(zOut / housingDepth + 0.5, 0), 1)  // 0 内端 → 1 外端
        x *= 1 - 0.30 * t ** 1.6              // 俯视渐缩：外端收窄（水滴轮廓）
        y *= 1 - 0.22 * t * t                 // 侧视渐缩：外端压低
        if (y < 0) y += (housingHeight / 2) * 0.16 * t * t   // 外端底部上挑（气动下切）
        if (x < flatStartX) x = flatStartX + (x - flatStartX) * flatKeep  // 尾部拍扁承托镜片
        pos.setXYZ(i, x, y, pos.getZ(i))
      }
      pos.needsUpdate = true
      // 索引球面：重算即得雕刻后的连续平滑法线（高光连续滚转的前提）
      housingGeom.computeVertexNormals()
    }
    const housingZ = mountZ + armLength + housingDepth * 0.42
    const housingY = 0.02
    const housing = new THREE.Mesh(housingGeom, bodyMat)
    housing.position.set(0, housingY, zSide * housingZ)
    mirrorGroup.add(housing)

    // 连接颈：从镜臂末端向上托住镜壳底，消除壳体悬空感
    const neckGeom = new THREE.CylinderGeometry(0.009, 0.012, 0.038, 14)
    const neck = new THREE.Mesh(neckGeom, bodyMat)
    neck.position.set(0, housingY - 0.028, zSide * (mountZ + armLength - 0.002))
    mirrorGroup.add(neck)

    // 尾部实际拍扁面位置（镜片/密封圈贴附基准）
    const rearTipX = flatStartX + (-housingLength / 2 - flatStartX) * flatKeep

    const roundedFace = (width, height, radius) => {
      const x = -width / 2
      const y = -height / 2
      const shape = new THREE.Shape()
      shape.moveTo(x + radius, y)
      shape.lineTo(x + width - radius, y)
      shape.quadraticCurveTo(x + width, y, x + width, y + radius)
      shape.lineTo(x + width, y + height - radius)
      shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
      shape.lineTo(x + radius, y + height)
      shape.quadraticCurveTo(x, y + height, x, y + height - radius)
      shape.lineTo(x, y + radius)
      shape.quadraticCurveTo(x, y, x + radius, y)
      return new THREE.ShapeGeometry(shape, 8)
    }

    // 密封圈：深色圆角垫片，贴在拍扁尾面外侧，遮住镜片与壳体间的缝隙
    const gasket = new THREE.Mesh(
      roundedFace(0.118, 0.056, 0.012),
      new THREE.MeshStandardMaterial({ color: 0x11141a, metalness: 0.1, roughness: 0.55, wireframe })
    )
    gasket.rotation.y = -Math.PI / 2
    gasket.position.set(rearTipX - 0.0006, housingY, zSide * housingZ)
    mirrorGroup.add(gasket)

    // ---- 凸面镜片：真车侧后视镜为凸面镜（扩大视野）。R=1.2m 球面矢高仅
    // ~1.3mm，但足以把平面镜的整片眩光收敛为一个随视线移动的小亮点——
    // 高光形态符合物理光照逻辑；圆角由 alphaMap 贴花裁切（亚像素边缘）。
    const glassW = 0.108, glassH = 0.046, glassR = 1.2
    const mirrorGeom = new THREE.PlaneGeometry(glassW, glassH, 28, 14)
    {
      const pos = mirrorGeom.attributes.position
      for (let i = 0; i < pos.count; i++) {
        const u = pos.getX(i), v = pos.getY(i)
        const sag = glassR - Math.sqrt(Math.max(glassR * glassR - u * u - v * v, 1e-9))
        pos.setZ(i, -sag)   // rotation.y=-90° 后中心向车尾（驾驶员）外凸
      }
      pos.needsUpdate = true
      mirrorGeom.computeVertexNormals()
    }
    const mirrorFace = new THREE.Mesh(
      mirrorGeom,
      new THREE.MeshStandardMaterial({
        color: 0xd7e2e8,
        metalness: 1.0,
        roughness: 0.12,
        envMapIntensity: 1.0,
        alphaMap: mirrorGlassAlpha,
        alphaTest: 0.5,
        wireframe
      })
    )
    mirrorFace.rotation.y = -Math.PI / 2
    mirrorFace.position.set(rearTipX - 0.0024, housingY, zSide * housingZ)
    mirrorGroup.add(mirrorFace)

    mirrorGroup.position.set(hoodEndX + 0.02, mountY, 0)
    return mirrorGroup
  }

  for (const zSide of [1, -1]) parent.add(createMirror(zSide))
}
