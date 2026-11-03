import * as THREE from 'three'
import {
  bandGlassSpine,
  buildDloStripRange,
  BODY_BEVEL_SIZE,
  GLASS_SURFACE_GAP
} from '../../utils/carGlass.js'

/**
 * 座舱玻璃（P2 拆分：原 Car3D.vue 的 addBandGlass / addDloPane）
 *
 * 只做几何组装，不做坐标推导：脊柱线、DLO 条带多边形全部来自 carGlass 纯函数真源，
 * 材质实例、锥化比例、分组与门片收集数组一律由调用方显式传入（模块内无闭包状态）。
 */

/** 侧窗面片沿高度细分的条带数（四角面片无法表达桶面曲率） */
export const DLO_ROWS = 16

/**
 * 斜面玻璃带（前风挡 / 后风挡）：脊柱线由 carGlass.bandGlassSpine 生成（可单测），
 * 含车顶 G1 圆角包裹采样与顶面搭接，玻璃随车身同一圆角弯曲。
 *
 * 偏移量 = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP：ExtrudeGeometry 的 bevel 会把整个侧壁
 * 沿 X-Y 外扩 bevelSize(=BODY_BEVEL_SIZE)，车身真实壁面因此在原始轮廓外该尺寸；
 * 玻璃必须骑在这层外扩壁面上，再留贴面间隙避免共面 z-fighting。
 * minOffsetRatio=1：全程保持同一偏移——旧实现让法线转向车顶时偏移渐减到 0，
 * 玻璃在 A 柱顶/C 柱顶瞬间沉入车身 30mm，肉眼即 COWL/车顶前缘的台阶折痕。
 *
 * @param {THREE.Object3D} group      挂载父级
 * @param {THREE.Material} material   玻璃材质实例（调用方持有，便于统一释放）
 * @param {(y:number)=>number} taperK greenhouse 收窄比例（y）→ ratio，决定 |z| 半宽
 */
export function addBandGlass({
  group, material, taperK,
  x1, y1, x2, y2, width,
  topInset = 0, bottomInset = 0, fillet = null
}) {
  const glassGap = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP
  const spine = bandGlassSpine(x1, y1, x2, y2, {
    topInset, bottomInset, offset: glassGap, minOffsetRatio: 1, fillet
  })
  const hw = width / 2
  const verts = []
  for (let i = 0; i < spine.length - 1; i++) {
    const [ax, ay] = spine[i]
    const [bx, by] = spine[i + 1]
    const az = hw * taperK(ay)
    const bz = hw * taperK(by)
    verts.push(ax, ay, -az, ax, ay, az, bx, by, -bz)
    verts.push(ax, ay, az, bx, by, bz, bx, by, -bz)
  }
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3))
  g.computeVertexNormals()
  const m = new THREE.Mesh(g, material)
  m.userData.noCastShadow = true
  group.add(m)
}

/**
 * 侧窗 DLO 分片（A 柱前固定片 / 前门片 / 后门片 / C 柱后固定片）。
 *
 * 多边形与 2D windowPath 逐点同源，顶部两角内收避开 G1 圆角；
 * Z 轮廓 = tumblehome 线性内收 + barrel 桶面圆弧鼓肚（dloZAt 纯函数，可单测）。
 * 面片沿高度细分成条带网格。
 *
 * 门片（hingeKey 非空）不直接挂到 group，而是推入调用方的 `doorGlass` 收集数组：
 * 收集时机由调用方统一决定，随后交给 createDoorRig 按铰链轴平移并重挂，
 * 保证玻璃与门板同轴同角度开合（顺序改变会导致门玻璃与门板错位）。
 *
 * @param {Array<{key:string, zSide:number, mesh:THREE.Mesh}>} doorGlass 门片收集数组
 * @param {object} cabin     deriveCabinGlass 结果（只用 cabin.dlo）
 * @param {object} dloFrame  buildDloFrame 结果（截面 Z 基准）
 * @param {number} zSide     ±1 侧别
 * @param {string|null} hingeKey 门片归属（'front' / 'rear'，固定片为 null）
 */
export function addDloPane({
  group, material, doorGlass = [],
  cabin, dloFrame,
  xFront, xRear, zSide, hingeKey,
  rows = DLO_ROWS
}) {
  const positions = buildDloStripRange(cabin.dlo, dloFrame, rows, zSide, xFront, xRear)
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
  g.computeVertexNormals()
  const panel = new THREE.Mesh(g, material)
  panel.userData.noCastShadow = true
  if (hingeKey) doorGlass.push({ key: hingeKey, zSide, mesh: panel })
  else group.add(panel)
}
