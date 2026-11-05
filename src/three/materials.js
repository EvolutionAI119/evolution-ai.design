import * as THREE from 'three'

/**
 * 单次构建的材质集合（P2 收尾：原 Car3D.vue 的共享材质段）
 *
 * 语义是**构建内工厂**，不是模块级单例：车色与线框都随 `updateCar()` 整体重建
 * （车色/参数/线框变化都会 dispose 旧 carGroup 后重新 createCar），所以每次构建
 * 必须新建一组材质，禁止跨 build 复用——否则切换车色或线框时旧材质会被复用。
 *
 * `bodyMats` 顺序固定 `[bodyMat, interiorMat]`，与车身几何的 group 顺序绑定：
 * 调换会让车内侧（门洞内壁）变成车漆色。
 *
 * 只允许被 parts/scene 引用；禁止 import Car3D 或任何 parts 模块（单向依赖）。
 */
export function createMaterialSet({ carColor, wireframe = false }) {
  // 金属底漆 + 柔化清漆：底漆提供车身色层次，低峰值清漆保留连续高光。
  // 避免高金属度/低粗糙度在机盖、腰线和尾盖的掠射角反射成一条爆白硬带。
  // 车身漆面必须双面渲染：车身是「侧围轮廓 + 洞口」整宽挤出的单一壳体，
  // ExtrudeGeometry 对轮廓/洞口扫掠壁的绕序并不总是朝外（车头肩部、机盖前缘、
  // 腰线一带会成片反绕）。单面材质下这些三角形被背面剔除 → 从车外看是成片
  // 纯黑楔形/锯齿（既一直存在，又极像穿模）。双面渲染 + three 对背面翻转法线，
  // 这些面按正确朝向着色，黑块消失；代价只是车身一层的额外光栅化。
  const bodyMat = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(carColor),
    metalness: 0.42,
    roughness: 0.34,
    clearcoat: 0.35,
    clearcoatRoughness: 0.24,
    envMapIntensity: 0.85,
    side: THREE.DoubleSide,
    wireframe
  })

  // 门洞内壁材质（开门状态）：深色内饰面，替代洞壁上的车身色 → 门洞里读作座舱，
  // 不再是一块横贯车宽的车身色板。DoubleSide 兜住洞壁朝向差异。
  const interiorMat = new THREE.MeshStandardMaterial({
    color: 0x1b1d22,
    metalness: 0.2,
    roughness: 0.9,
    side: THREE.DoubleSide,
    wireframe
  })

  const glassMat = new THREE.MeshPhysicalMaterial({
    color: 0xa8c4cc,
    transparent: true,
    opacity: 0.25,
    metalness: 0,
    roughness: 0.08,
    envMapIntensity: 0.6,
    side: THREE.DoubleSide,
    depthWrite: false,
    wireframe
  })

  const wheelMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a1f,
    metalness: 0.3,
    roughness: 0.8,
    wireframe
  })

  const rimMat = new THREE.MeshStandardMaterial({
    color: 0xaaaaaa,
    metalness: 0.9,
    roughness: 0.2,
    wireframe
  })

  // 轮辋盘面（比辐条深一档的枪灰）：与亮银辐条/轮唇形成明暗层次，
  // 否则同色材质会让辐条「消失」在盘面上，整轮仍读作一块平盘
  const rimDiscMat = new THREE.MeshStandardMaterial({
    color: 0x565b63,
    metalness: 0.85,
    roughness: 0.38,
    wireframe
  })

  // 镀铬：四轮轮毂盖 + 车门把手共用同一实例（模块内不得各建一份，否则两套高光）
  const chromeMat = new THREE.MeshStandardMaterial({
    color: 0xcccccc,
    metalness: 1.0,
    roughness: 0.1,
    wireframe
  })

  // 底盘升力风道盘 / 亮银唇 / 轮腔内衬
  const ductMat = new THREE.MeshStandardMaterial({
    color: 0x14161c, metalness: 0.6, roughness: 0.4, wireframe
  })
  const lipMat = new THREE.MeshStandardMaterial({
    color: 0xb8bcc4, metalness: 1.0, roughness: 0.15, wireframe
  })
  const linerMat = new THREE.MeshStandardMaterial({
    color: 0x101014, metalness: 0.2, roughness: 0.95, side: THREE.DoubleSide, wireframe
  })

  return {
    bodyMat,
    interiorMat,
    bodyMats: [bodyMat, interiorMat],
    glassMat,
    wheelMat,
    rimMat,
    rimDiscMat,
    chromeMat,
    ductMat,
    lipMat,
    linerMat
  }
}
