import * as THREE from 'three'
import { archLinerProfile } from '../../utils/carProfile.js'

/**
 * 车轮 / 轮腔衬 / 底盘升力风道（P2 拆分：原 Car3D.vue 挤出路径的三段几何）
 *
 * 只做装配：轮心 X/Z、半径、胎宽、车身全宽与轮腔轮廓全部由 carProfile 派生后传入；
 * 材质（轮毂/胎/轮辋盘/亮银/镀铬/内衬）一律由调用方提供实例——`chromeMat` 与门把手
 * 共用，模块内重建会导致镀铬件出现两套高光。
 *
 * 硬性约束：
 * - 离地基准 `position.set(x, wheelR, z)` 不动（整车 bbox 最低点即轮底）；
 * - `outboard = Math.sign(z) || 1` 不能统一成 +1（否则一侧轮辋朝内、读作「无轮黑洞」）；
 * - 轮腔衬 `archLinerProfile(P, side, 0.012)` 的 12mm 内缩与全宽 `bodyExtentZ` 原值保留。
 *
 * 与 NURBS 路径的 `createNurbsWheel` 是两套实现（mm→m 换算、缺省 radius/width），
 * 不在此模块内合并。
 */

/** 单轮：胎 + 轮辋盘 + 轮唇 + 轮毂盖 + 5 根径向辐条（按 `z` 决定外侧方向） */
export function createWheel({
  x, z, wheelR, tireW,
  wheelMat, rimDiscMat, rimMat, chromeMat
}) {
  const wheelGroup = new THREE.Group()
  // 外侧方向：轮辋盘面/辐条必须装在朝向车外的一侧，否则整轮被轮胎端盖
  // 遮成一块纯黑圆盘（侧视读作「无轮」黑洞）
  const outboard = Math.sign(z) || 1

  const tireWidth = tireW
  const tireGeom = new THREE.CylinderGeometry(wheelR, wheelR, tireWidth, 28)
  tireGeom.rotateX(Math.PI / 2)
  const tire = new THREE.Mesh(tireGeom, wheelMat)
  wheelGroup.add(tire)

  // 轮辋盘：贴在外侧胎侧之外 6mm，半径 0.68R（露出胎侧黑边作胎壁）。
  // 盘面用深一档的枪灰，辐条/轮唇用亮银——同色会把辐条吃掉，整轮仍是「平盘」
  const rimR = wheelR * 0.68
  const rimGeom = new THREE.CylinderGeometry(rimR, rimR, 0.02, 28)
  rimGeom.rotateX(Math.PI / 2)
  const rim = new THREE.Mesh(rimGeom, rimDiscMat)
  rim.position.z = outboard * (tireWidth / 2 - 0.004)
  wheelGroup.add(rim)

  // 轮唇：轮辋外圈的亮银环，勾勒轮辋与胎壁的分界
  const lipGeom = new THREE.TorusGeometry(rimR, 0.008, 8, 28)
  const rimLip = new THREE.Mesh(lipGeom, rimMat)
  rimLip.position.z = outboard * (tireWidth / 2 + 0.006)
  wheelGroup.add(rimLip)

  // 轮毂中心盖：亮银圆盘凸出于轮辋盘
  const hubGeom = new THREE.CylinderGeometry(rimR * 0.30, rimR * 0.30, 0.016, 16)
  hubGeom.rotateX(Math.PI / 2)
  const hub = new THREE.Mesh(hubGeom, chromeMat)
  hub.position.z = outboard * (tireWidth / 2 + 0.010)
  wheelGroup.add(hub)

  // 辐条：5 根径向辐板，绕轮轴（Z）均布，压在轮辋盘外侧
  const spokeLen = rimR * 0.9
  for (let i = 0; i < 5; i++) {
    const spokeGeom = new THREE.BoxGeometry(rimR * 0.26, spokeLen, 0.014)
    spokeGeom.translate(0, spokeLen / 2, 0)
    const spoke = new THREE.Mesh(spokeGeom, rimMat)
    spoke.rotation.z = (i * Math.PI * 2) / 5
    spoke.position.z = outboard * (tireWidth / 2 + 0.012)
    wheelGroup.add(spoke)
  }

  wheelGroup.position.set(x, wheelR, z)
  return wheelGroup
}

/** 四轮：前轴/后轴 × 左右（添加顺序保持前两轮 → 后两轮） */
export function createWheels({ parent, frontX, rearX, wheelZ, ...rest }) {
  parent.add(createWheel({ x: frontX, z: wheelZ, ...rest }))
  parent.add(createWheel({ x: frontX, z: -wheelZ, ...rest }))
  parent.add(createWheel({ x: rearX, z: wheelZ, ...rest }))
  parent.add(createWheel({ x: rearX, z: -wheelZ, ...rest }))
}

/**
 * 轮腔内衬：与拱口同形的内嵌椭圆拱壳（半椭圆上缘 + 竖直唇落至底板）。
 * 圆形筒对椭圆拱口必然四周互穿（前后壁/顶部戳出 = 拓扑破面），改用 archLinerProfile
 * 纯函数生成的拱形开壳，整体内缩 12mm 严格位于空腔内，横跨全宽挡住对侧亮色 bevel。
 */
export function addArchLiners({ parent, P, bodyExtentZ, material, sides = ['front', 'rear'] }) {
  for (const side of sides) {
    const prof = archLinerProfile(P, side, 0.012)
    const L = bodyExtentZ
    const positions = []
    for (const [x, y] of prof) positions.push(x, y, -L, x, y, L)
    const indices = []
    for (let i = 0; i < prof.length - 1; i++) {
      const a = i * 2, b = i * 2 + 1, c = (i + 1) * 2, d = (i + 1) * 2 + 1
      indices.push(a, b, c, b, d, c)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
    g.setIndex(indices)
    g.computeVertexNormals()
    const liner = new THREE.Mesh(g, material)
    liner.receiveShadow = true
    parent.add(liner)
  }
}

/**
 * 底盘上升装置风道盘 + 亮银唇（6~8 台）。
 *
 * 布局必须由调用方用 `deriveLiftDevices(P, liftFans)` 算好后传入：同一份布局也是
 * 悬停风扇环（`ensureFlightFx`）的定位来源，两处若各算一次会出现环与风道错位。
 * 风道口下沉 12mm，不构成额外最低点（整车最低点仍是轮底）。
 */
export function createLiftDucts({ parent, liftLayout, ductMat, lipMat }) {
  for (const d of liftLayout.devices) {
    const duct = new THREE.Mesh(new THREE.CylinderGeometry(d.r, d.r * 1.04, 0.02, 28), ductMat)
    duct.position.set(d.x, liftLayout.y, d.z)
    duct.userData.noCastShadow = true
    parent.add(duct)
    const lip = new THREE.Mesh(new THREE.TorusGeometry(d.r * 0.99, 0.009, 8, 28), lipMat)
    lip.rotation.x = Math.PI / 2
    lip.position.set(d.x, liftLayout.y - 0.01, d.z)
    lip.userData.noCastShadow = true
    parent.add(lip)
  }
}
