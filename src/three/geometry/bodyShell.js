import * as THREE from 'three'
import { bodySideOutline } from '../../utils/carProfile.js'
import {
  deriveDloApertures,
  buildDloFrame,
  buildDoorAperturePolygon,
  shellHalfZAt,
  insideBodyMaterial,
  ROOF_FILLETS,
  BODY_BEVEL_SIZE,
  DLO_APERTURE_INSET
} from '../../utils/carGlass.js'
import { smoothNormalsKeepHardEdges, splitTrianglesAtY, splitTrianglesAtAbsZ, subdivideSideCapLongEdges } from './smoothing.js'
import { assignShellOwners, groupShellByOwner } from './panelOwnership.js'

/**
 * 车身壳装配（P5 批次 2）：侧围轮廓 → 洞口 → 挤出 → greenhouse 收窄 → 洞壁内饰化。
 *
 * 真源单向：轮廓来自 carProfile.bodySideOutline，洞口/玻璃常量直接取 carGlass，
 * 不经 composable 转发；本模块不读 props/ref，坐标与参数全部来自入参。
 */

/**
 * 车身洞口内壁材质分组（平台侧「面片归属」修法，采纳 SISA 提案修法 2）
 *
 * 车身由侧围轮廓整宽挤出：一切轮廓内 holes（门洞/侧窗分片洞口）沿 Z 贯穿，
 * 洞壁因此横贯整车宽度；若保留车身色，洞口里会看到大片车漆板——即「多余车身」。
 * 洞壁三角形归入材质组 1（深色内饰），洞内读作座舱内壁。
 *
 * 归属判据（与提案 A1/A2 对齐）：
 *   - **穷尽 + 互斥**：每个面片在一次遍历中拿到恰好一个归属（车漆 / 洞壁内饰），
 *     不存在「被两条判据链各改判一次」的重叠可能；
 *   - 判据用的是**真实洞口多边形的等距带**（polygonEdgeDistance ≤ APERTURE_BAND），
 *     不再是 bbox 近似（bbox 会把洞口外的车身三角形误判成内饰 → 洞口下沿锯齿）；
 *   - 端盖（|nz|>0.6，车侧漆面）与水平壁（|ny|>0.8，门槛/窗台）必留车漆；
 *   - 贴外轮廓线的外皮由 isBodyMaterial 排除。
 *
 * 风挡/后风挡斜面**不再改判车身面片**：斜面墙是整宽大三角形，任何「按重心判
 * 是否落在玻璃半宽内」的写法都会把整片斜面墙染成深色（黑带 + 齿状边）。
 * 舱影改为独立几何（见 parts/glass.js 的 addBandCabinShadow），其覆盖区与玻璃
 * 逐点同源 ⟹ 两件不可能重叠。
 *
 * @param {THREE.BufferGeometry} geom 车身挤出几何（非索引，就地重排）
 * @param {Array<{key:string, pts:Array<number[]>}>} apertures 真实洞口多边形（与挖洞同一份）
 * @param {number|Function} zCap 外蒙皮端面保留带宽（可传 (y)=>收窄后的外皮界）
 * @param {Function} [isBodyMaterial] (x,y)→bool：点是否在车身实体内（外轮廓内且不在洞口内）
 * @param {number[]} [hardEdgesY] 需要钉成硬边的高度（腰带线）——重排后重算法线必须
 *   沿用同一组硬边，否则收窄拐点被焊接平均，翼子板/后围会出现斜向明暗条带
 * @returns {number} 归入内饰组的三角形数
 */
export function splitBodyAperturesInterior(geom, apertures, zCap, isBodyMaterial = null, hardEdgesY = null) {
  const { owners } = assignShellOwners(geom, { apertures, zCapAt: zCap, isBodyMaterial })
  const counts = groupShellByOwner(geom, owners)
  // normal 属性不随重排走，必须整面重算；硬边集合必须与收窄前一致
  smoothNormalsKeepHardEdges(geom, 1e-4, 32, hardEdgesY)
  return counts.liner
}

/**
 * 前/后风挡玻璃顶边距柱顶圆角的留边（米）：玻璃不包裹车顶圆角、不搭上车顶。
 * 车身壳（玻璃带暗舱底判据）与玻璃面板共用同一常量，避免两处各写一个数。
 */
export const FRONT_GLASS_TOP_BORDER = 0.004

/**
 * 构建车身壳几何（含洞口与锥化）。
 *
 * @param {Object} args
 * @param {Object} args.P carProfile 输出
 * @param {string} args.carType 车型（外轮廓 G1 圆角口径）
 * @param {Object} args.cabin deriveCabinGlass 输出
 * @param {Object} args.doorLayout deriveDoorLayout 输出
 * @param {Array} args.paneRanges deriveDloPaneRanges 输出
 * @returns {{ bodyGeom, outlineShape, bodyExtentZ, dloFrame, taperK, shoulderY }}
 */
export function buildBodyShell({ P, carType, cabin, doorLayout, paneRanges }) {
  const bodyShape = new THREE.Shape()

  // ---- 侧围外轮廓（2D/3D 唯一真源 bodySideOutline：顶边 G1 圆角 + 底边轮拱 notch + 接近/离去角切角）----
  // 轮拱做进外轮廓（非 holes 共线孔）→ bevel 沿轮廓走，拱底无残留车身色薄片，真正挖通
  const outlineCmds = bodySideOutline(P, carType, ROOF_FILLETS, P.ramps)
  for (const c of outlineCmds) {
    if (c.k === 'M') bodyShape.moveTo(c.x, c.y)
    else if (c.k === 'L') bodyShape.lineTo(c.x, c.y)
    else if (c.k === 'Q') bodyShape.quadraticCurveTo(c.cx, c.cy, c.x, c.y)
    else if (c.k === 'A') bodyShape.absellipse(c.cx, c.cy, c.rx, c.ry, c.a0, c.a1, c.cw)
  }
  bodyShape.closePath()

  // 门洞**常挖**（与开合状态无关）：门板是覆盖门洞的唯一几何——车门唯一一份，
  // 关门盖住洞口封闭，开门外摆后原位全空。上下缘与门板留 2~8mm 叠压量保证封闭。
  // 注意：用 holes 而非压平轮廓，避免挤出 bevel 在压平区产生折叠/顶点爆炸。
  const doorRearEdge = (doorLayout.rearSeamX === null ? doorLayout.midSeamX : doorLayout.rearSeamX) - 0.004
  const doorFrontEdge = doorLayout.frontSeamX + 0.004
  const doorHoleBottom = P.bodyBottomY + 0.028
  // 肩线 = 玻璃洞口底边（DLO 底边 + 内缩）：门洞必须与门片玻璃洞口**合并**为
  // 单一多边形，否则两者之间残留一条 20mm 车身色腰带横条，开门后横贯门洞遮挡。
  const shoulderY = cabin.dlo[0][1] + DLO_APERTURE_INSET

  // 侧窗分片玻璃洞口**常挖**：玻璃因此成为真透明件（洞沿 Z 贯通左右侧壁）。
  // 洞口较玻璃四缘内缩 12mm（关门玻璃叠压封闭）；相邻洞口间保留车身色竖条
  // （A/B/C 柱剪影）与车顶横梁——车身色顶部边界与玻璃清晰区分。
  // 开门时门片玻璃随铰链外摆，原车门玻璃位置即为全空通透孔洞，无任何遮挡物。
  const glassApertures = deriveDloApertures(cabin.dlo, paneRanges)
  const doorPaneKeys = new Set(paneRanges.filter((p) => p.hingeKey).map((p) => p.key))
  const doorTowers = glassApertures.filter((ap) => doorPaneKeys.has(ap.key))
  // 洞壁内饰化的**真实洞口多边形**（与挖洞用的是同一份数据 ⟹ 判据与几何同源）：
  // 洞壁归属用「到洞口多边形边界的等距带」，不再用 bbox 近似
  // （bbox 会把洞口外的车身三角形误判成内饰 → 洞口下沿锯齿）。
  const apertures = []
  // A 柱前固定片 / C 柱后固定片：各自独立挖洞
  for (const ap of glassApertures) {
    if (doorPaneKeys.has(ap.key)) continue
    const p = new THREE.Path()
    p.moveTo(ap.points[0][0], ap.points[0][1])
    for (let i = 1; i < ap.points.length; i++) p.lineTo(ap.points[i][0], ap.points[i][1])
    p.closePath()
    bodyShape.holes.push(p)
    apertures.push({ key: ap.key, pts: ap.points })
  }
  // 门洞 + 门片玻璃洞口 → 单一简单多边形（腰带处不再有车身色横带）；
  // 退化时退回纯门洞矩形（不产生自交 holes，玻璃仍覆盖实体车身）
  const doorPoly = buildDoorAperturePolygon({
    frontEdge: doorFrontEdge, rearEdge: doorRearEdge,
    bottomY: doorHoleBottom, shoulderY,
    panes: doorTowers.map((ap) => ap.points)
  }) || [
    [doorRearEdge, doorHoleBottom], [doorFrontEdge, doorHoleBottom],
    [doorFrontEdge, shoulderY], [doorRearEdge, shoulderY]
  ]
  const doorHole = new THREE.Path()
  doorHole.moveTo(doorPoly[0][0], doorPoly[0][1])
  for (let i = 1; i < doorPoly.length; i++) doorHole.lineTo(doorPoly[i][0], doorPoly[i][1])
  doorHole.closePath()
  bodyShape.holes.push(doorHole)
  // 门洞连同门片塔楼是**一个**洞口多边形（B 柱之间的肩线段是其边界的一部分），
  // 因此归属判据也用这一份多边形——塔楼之间的 B 柱位于多边形内部，
  // 不会被等距带扫到 ⟹ B 柱仍是车身色竖条。
  apertures.push({ key: 'door', pts: doorPoly })

  // 外轮廓多边形：内外测试口径，供洞壁内饰化排除「外皮/倒角外扩带」三角形——
  // 轮廓上的车顶前缘、风挡边框必须保留车身色（见下方判据）。
  const outlinePts = bodyShape.extractPoints(16)
  const isBodyMaterial = (x, y) => insideBodyMaterial(x, y, outlinePts.shape)

  // 车身挤出深度 = W − 2×bevel：three.js 的 bevel 在 Z 两端各扩展 bevelThickness，
  // 因此整车宽度 = depth + 2×bevelThickness = W（不被倒角撑大）。
  // bodyExtentZ = (depth + 2×bevel) / 2 = W / 2，即车身侧壁外表面 |z| = W/2。
  const bodyDepth = P.W - BODY_BEVEL_SIZE * 2
  const bodyThickness = BODY_BEVEL_SIZE
  const bodyExtentZ = (bodyDepth + bodyThickness * 2) / 2

  const extrudeSettings = {
    depth: bodyDepth,
    bevelEnabled: true,
    bevelThickness: bodyThickness,
    bevelSize: bodyThickness,
    bevelSegments: 3,
    curveSegments: 16
  }

  const bodyGeom = new THREE.ExtrudeGeometry(bodyShape, extrudeSettings)
  bodyGeom.translate(0, 0, -bodyDepth / 2)

  const dloFrame = buildDloFrame(cabin, bodyExtentZ + 0.002)

  // 车身 greenhouse 收窄：DLO 底边（腰带线）以上的侧壁/车顶按与 DLO 玻璃面同公式
  // 内收——A/B/C 柱剪影与车顶随玻璃角度/桶面联动，玻璃面始终位于车身外侧同间隙
  // （shellHalfZAt 为唯一 Z 公式：车身、风挡带、DLO 玻璃共用同一条内收曲线）
  const taperK = (y) => shellHalfZAt(y, dloFrame, bodyExtentZ) / bodyExtentZ
  // earcut 会切出跨越整块翼子板/车门的超长边端盖三角形：共面但角点落在法线突变处，
  // 平滑法线沿长边线性插值会铺出一条斜向明暗渐变。先细分端盖长边（≤0.12m），
  // 再按腰带线切分收窄，最后统一重算法线。
  subdivideSideCapLongEdges(bodyGeom, 0.12)
  // 先把横跨腰带线的长三角形切开，否则收窄后折板会渲染成大面积渐变破面
  splitTrianglesAtY(bodyGeom, dloFrame.dloYBot)
  // 洞口隧道壁在 ExtrudeGeometry 里是横跨全宽的长四边形：不切开就只能整块改判——
  // 全深色会让洞口外缘缺一圈车色门框，并在窗台/门缝边缘露出锯齿状深色三角。
  // 先沿 |z| 切成「外环带（车门框，保留车身色）+ 内腔（深色内饰）」两块，
  // 分界线成为沿 Z 的直线，洞口边缘干净。收窄前切分点 = 收窄后的 zCapAt 曲线。
  const apertureFrameLip = 0.03
  const interiorHalfZ = bodyDepth / 2 - apertureFrameLip
  splitTrianglesAtAbsZ(bodyGeom, interiorHalfZ)
  {
    const pos = bodyGeom.attributes.position
    for (let i = 0; i < pos.count; i++) {
      pos.setZ(i, pos.getZ(i) * taperK(pos.getY(i)))
    }
    pos.needsUpdate = true
  }
  // 收窄后侧围端盖已成双曲面：必须按位置焊接求平滑法线，否则逐面法线烧出三角破面；
  // 腰带线（DLO 底边）钉为硬边——收窄拐点若被焊接平均扫过，腰线高光会晕染成一条
  // 宽泛爆白的「白带」；硬边让高光收成一条锐利折线，上下板面各自均匀过渡。
  smoothNormalsKeepHardEdges(bodyGeom, 1e-4, 32, [dloFrame.dloYBot])

  // 洞壁内饰化（面片归属）：门洞 + 全部侧窗分片洞口的洞壁（横贯车宽）改判深色
  // 内饰材质，|z| ≥ 外蒙皮端面的倒角环带保留车身色作门框/窗框唇边。
  // 判据随收窄联动：内腔界 = interiorHalfZ·taperK(y)（切分点同源）。
  // 用固定 bodyDepth/2 会把收窄后的 A/B/C 柱、车顶前缘、后侧围外蒙皮一并改判深色。
  // 风挡/后风挡斜面**不在此改判**：舱影改由独立几何承担（parts/glass.js
  // addBandCabinShadow），覆盖区与玻璃逐点同源 ⟹ 不可能出现黑带/重叠。
  splitBodyAperturesInterior(
    bodyGeom, apertures, (y) => interiorHalfZ * taperK(y), isBodyMaterial, [dloFrame.dloYBot]
  )

  return {
    bodyGeom,
    outlineShape: outlinePts.shape,
    bodyExtentZ,
    dloFrame,
    taperK,
    shoulderY,
    // 真实洞口多边形（与挖洞、洞壁归属判据同一份）：供 A1–A5 等价判据审计
    apertures
  }
}
