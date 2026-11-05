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
 * 舱影底板相对玻璃面的内收量（米）。
 *
 * 舱影必须严格夹在「车身斜面墙（外表面 = 轮廓 + BODY_BEVEL_SIZE）」与「玻璃面
 * （= 轮廓 + BODY_BEVEL_SIZE + GLASS_SURFACE_GAP）」之间：与墙共面会 z-fighting，
 * 与玻璃共面同样 z-fighting。0.5mm 使两侧各留 0.5mm 间隙，斜射视角下也不闪烁。
 */
export const CABIN_SHADOW_GAP = 0.0005

/**
 * 斜面玻璃带的覆盖区几何（脊柱线 + 逐点半宽）——玻璃面板与「舱影底板」的唯一共源。
 *
 * 两者必须逐点共用同一份覆盖区定义：面板边缘即舱影边缘，二者在同一条 z 界上收口，
 * 不会出现「玻璃边外一条黑带」或「玻璃边内一条车漆带」。
 *
 * @param {object} o
 * @param {number} o.x1 底缘 X @param {number} o.y1 底缘 Y
 * @param {number} o.x2 顶缘 X @param {number} o.y2 顶缘 Y
 * @param {number} o.width 覆盖区总宽（米）
 * @param {number} o.topInset 顶缘内退 @param {number} o.bottomInset 底缘内退
 * @param {number} o.offset 相对玻璃离面量的偏移（米）：0 = 与玻璃共面，负 = 更靠车身
 * @param {(y:number)=>number} o.taperK greenhouse 收窄比例（y）→ ratio
 * @param {object} [o.fillet] 车顶 G1 圆角包裹参数（玻璃与舱影必须同值，否则顶角不共源）
 * @returns {{ positions: number[] }} 三角形顶点序列（每段两三角形）
 */
function bandCoverGeometry({ x1, y1, x2, y2, width, topInset, bottomInset, offset, taperK, fillet = null }) {
  const glassGap = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP
  const spine = bandGlassSpine(x1, y1, x2, y2, {
    topInset, bottomInset, offset: glassGap + offset, minOffsetRatio: 1, fillet
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
  return { positions: verts }
}

/**
 * 舱影底板（风挡 / 后风挡斜面玻璃后方的深色内舱面）。
 *
 * 根因修法（旧实现是「把车身侧壁上的大三角形整块改判内饰深色」）：
 * 车身是侧围轮廓整宽挤出的，斜面墙在 3D 里是**整宽大三角形**——用三角形重心
 * 判「是否落在玻璃半宽内」必然整片命中，于是玻璃边外的 A/C 柱区被染成深色
 * （黑带），且染色边界落在粗三角形的边上（锯齿齿）。
 * 本实现改为：舱影是一块**独立几何**，其覆盖区与玻璃面板逐点同源
 * （同一脊柱线、同一逐点半宽 = width/2·taperK(y)），因此
 *   1) 舱影不会溢出到玻璃之外（无黑带）；
 *   2) 舱影边界 = 玻璃边界（无锯齿）；
 *   3) 车身斜面墙恢复纯车漆色，不再需要任何「按重心染色」的几何启发式。
 *
 * 离面量 = 玻璃离面量 − CABIN_SHADOW_GAP（0.5mm）：必须严格夹在
 * 「车身斜面墙（外表面 = 轮廓 + BODY_BEVEL_SIZE）」与「玻璃面
 * （= 轮廓 + BODY_BEVEL_SIZE + GLASS_SURFACE_GAP）」之间——与墙共面会 z-fighting，
 * 与玻璃共面同样 z-fighting。两侧各留 0.5mm 间隙，斜射视角下也不闪烁。
 *
 * @param {THREE.Object3D} group 挂载父级
 * @param {THREE.Material} material 深色不透明材质
 * @param {object} [fillet] 车顶 G1 圆角包裹参数（必须与玻璃面板同值）
 */
export function addBandCabinShadow({
  group, material, taperK,
  x1, y1, x2, y2, width,
  topInset = 0, bottomInset = 0, fillet = null
}) {
  const { positions } = bandCoverGeometry({
    x1, y1, x2, y2, width, topInset, bottomInset,
    offset: -CABIN_SHADOW_GAP, taperK, fillet
  })
  if (!positions.length) return null
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
  g.computeVertexNormals()
  const m = new THREE.Mesh(g, material)
  m.userData.noCastShadow = true
  m.userData.noReceiveShadow = true
  group.add(m)
  return m
}

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
  // 与舱影底板共用 bandCoverGeometry ⟹ 面板边缘即舱影边缘（唯一共源定义）
  const { positions } = bandCoverGeometry({
    x1, y1, x2, y2, width, topInset, bottomInset,
    offset: 0, taperK, fillet
  })
  if (!positions.length) return null
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
  g.computeVertexNormals()
  const m = new THREE.Mesh(g, material)
  m.userData.noCastShadow = true
  group.add(m)
  return m
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
