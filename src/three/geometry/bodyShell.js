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
import { smoothNormalsKeepHardEdges, splitTrianglesAtY } from './smoothing.js'

/**
 * 车身壳装配（P5 批次 2）：侧围轮廓 → 洞口 → 挤出 → greenhouse 收窄 → 洞壁内饰化。
 *
 * 真源单向：轮廓来自 carProfile.bodySideOutline，洞口/玻璃常量直接取 carGlass，
 * 不经 composable 转发；本模块不读 props/ref，坐标与参数全部来自入参。
 */

/**
 * 车身洞口内壁 + 风挡暗舱底材质分组
 *
 * 车身由侧围轮廓整宽挤出：一切轮廓内 holes（门洞/侧窗分片洞口）沿 Z 贯穿，
 * 洞壁因此横贯整车宽度；若保留车身色，洞口里会看到大片车漆板——即「多余车身」。
 * 把三角形重心落在任一口径矩形内、且不在外蒙皮端面（|z| 接近半车宽的倒角环带
 * 保留车身色作门框/窗框唇边）的三角形归入材质组 1，用深色内饰材质渲染，
 * 洞内读作座舱内壁；柱条/车顶的外蒙皮保持车身色 → 车身色顶部边界与玻璃清晰区分。
 *
 * 风挡/后风挡斜面无法挖 Z 向洞（斜面是挤出侧壁而非端盖）：把斜面玻璃带覆盖的
 * 中央区三角形改判为内饰深色（带平面法向朝上、|z| 在玻璃半宽内），
 * 透过透明玻璃读到的是深色舱影而非车身色壁；A/C 柱区（玻璃半宽以外）保持车身色。
 *
 * @param {THREE.BufferGeometry} geom 车身挤出几何（非索引，就地重排）
 * @param {Array<{x0:number,x1:number,y0:number,y1:number}>} rects 洞口矩形列表（米）
 * @param {number} zCap 外蒙皮端面保留带宽（|z| ≥ zCap 的三角形保持车身色）
 * @param {Array<{x1,y1,x2,y2,bottomInset,topInset,halfWidth}>} [bands] 斜面玻璃带暗舱底
 * @param {Function} [taperK] greenhouse 收窄比例（y）→ ratio（bands 的 |z| 判据用）
 * @param {Function} [isBodyMaterial] (x,y)→bool：点是否在车身实体内（外轮廓内且不在洞口内）。
 *   用于把「位置落在洞口口径矩形内」的外皮三角形（轮廓线上的车顶前缘/风挡边框）排除，
 *   只改判真正横贯车宽的洞口隧道壁。
 * @returns {number} 归入内饰组的三角形数
 */
export function splitBodyAperturesInterior(geom, rects, zCap, bands = [], taperK = null, isBodyMaterial = null) {
  const pos = geom.attributes.position
  const arr = pos.array
  const nTri = pos.count / 3
  const exterior = []
  const interior = []
  // 玻璃带平面单位法线：暗舱底只改判**与带平面平行**的三角形。旧判据「法向朝上
  // ny>0.35」会连带把车顶前缘/COWL 等近水平面（ny≈1）也染成暗色，形成车顶黑边；
  // 用与带面法线的点积（|dot|>0.9）可精确锁定斜面墙本身。
  const bandNormals = bands.map((b) => {
    const dx = b.x2 - b.x1
    const dy = b.y2 - b.y1
    const len = Math.hypot(dx, dy) || 1
    return [dy / len, -dx / len]
  })
  for (let i = 0; i < nTri; i++) {
    const o = i * 9
    const cx = (arr[o] + arr[o + 3] + arr[o + 6]) / 3
    const cy = (arr[o + 1] + arr[o + 4] + arr[o + 7]) / 3
    const cz = (arr[o + 2] + arr[o + 5] + arr[o + 8]) / 3
    let inside = false
    if (Math.abs(cz) < zCap) {
      for (const r of rects) {
        if (cx > r.x0 && cx < r.x1 && cy > r.y0 && cy < r.y1) {
          // 外皮（车顶前缘/引擎盖/门槛等轮廓线上的三角形）重心也在矩形内，
          // 但它们属于外形，必须保留车身色；只有实体内部（洞口隧道壁）改判内饰。
          if (!isBodyMaterial || isBodyMaterial(cx, cy)) inside = true
          break
        }
      }
    }
    if (!inside && bands.length && taperK) {
      // 面几何法线（位置叉积；判据只取朝向，无需顶点法线）
      const e1x = arr[o + 3] - arr[o]; const e1y = arr[o + 4] - arr[o + 1]; const e1z = arr[o + 5] - arr[o + 2]
      const e2x = arr[o + 6] - arr[o]; const e2y = arr[o + 7] - arr[o + 1]; const e2z = arr[o + 8] - arr[o + 2]
      let nx = e1y * e2z - e1z * e2y
      let ny = e1z * e2x - e1x * e2z
      let nz = e1x * e2y - e1y * e2x
      const nl = Math.hypot(nx, ny, nz) || 1
      nx /= nl; ny /= nl; nz /= nl
      // 斜面墙：非端盖（|nz|<0.5）且法线与带平面法线近乎平行（|dot|>0.9）
      if (Math.abs(nz) < 0.5) {
        for (let bi = 0; bi < bands.length; bi++) {
          const b = bands[bi]
          const bn = bandNormals[bi]
          if (Math.abs(nx * bn[0] + ny * bn[1]) <= 0.9) continue
          const dx = b.x2 - b.x1; const dy = b.y2 - b.y1
          const len2 = dx * dx + dy * dy || 1e-12
          const len = Math.sqrt(len2)
          const t = ((cx - b.x1) * dx + (cy - b.y1) * dy) / len2
          if (t < b.bottomInset / len || t > 1 - b.topInset / len) continue
          const px = b.x1 + dx * t; const py = b.y1 + dy * t
          if (Math.hypot(cx - px, cy - py) > 0.03) continue          // 斜面墙条带（含 bevel 外扩）
          if (Math.abs(cz) > b.halfWidth * taperK(cy) - 0.004) continue // A/C 柱区留车身色
          inside = true
          break
        }
      }
    }
    ;(inside ? interior : exterior).push(o)
  }
  if (!interior.length) return 0
  const out = new Float32Array(arr.length)
  let k = 0
  for (const o of exterior) for (let j = 0; j < 9; j++) out[k++] = arr[o + j]
  const extVerts = k / 3
  for (const o of interior) for (let j = 0; j < 9; j++) out[k++] = arr[o + j]
  geom.setAttribute('position', new THREE.BufferAttribute(out, 3))
  geom.deleteAttribute('uv')          // 顶点重排后 uv 失效；本模型不使用贴图
  smoothNormalsKeepHardEdges(geom)    // normal 属性不随重排走，必须整面重算
  geom.clearGroups()
  geom.addGroup(0, extVerts, 0)
  geom.addGroup(extVerts, k / 3 - extVerts, 1)
  return interior.length
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
  // 洞壁内饰化口径矩形（外扩 8mm 兜住洞壁边界三角形，见 splitBodyAperturesInterior）
  const apertureRects = []
  // A 柱前固定片 / C 柱后固定片：各自独立挖洞
  for (const ap of glassApertures) {
    if (doorPaneKeys.has(ap.key)) continue
    const p = new THREE.Path()
    p.moveTo(ap.points[0][0], ap.points[0][1])
    for (let i = 1; i < ap.points.length; i++) p.lineTo(ap.points[i][0], ap.points[i][1])
    p.closePath()
    bodyShape.holes.push(p)
    const xs = ap.points.map((q) => q[0])
    const ys = ap.points.map((q) => q[1])
    apertureRects.push({
      x0: Math.min(...xs) - 0.008, x1: Math.max(...xs) + 0.008,
      y0: Math.min(...ys) - 0.008, y1: Math.max(...ys) + 0.008
    })
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
  // 口径矩形：门洞下半（到肩线）+ 每个门片塔楼各自 bbox——不能用合并多边形的
  // 总 bbox，否则塔楼之间的 B 柱会被改判成深色内饰
  apertureRects.push({
    x0: doorRearEdge - 0.008, x1: doorFrontEdge + 0.008,
    y0: doorHoleBottom - 0.008, y1: shoulderY + 0.004
  })
  for (const ap of doorTowers) {
    const xs = ap.points.map((q) => q[0])
    const ys = ap.points.map((q) => q[1])
    apertureRects.push({
      x0: Math.min(...xs) - 0.008, x1: Math.max(...xs) + 0.008,
      y0: Math.min(...ys) - 0.008, y1: Math.max(...ys) + 0.008
    })
  }

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
  // 先把横跨腰带线的长三角形切开，否则收窄后折板会渲染成大面积渐变破面
  splitTrianglesAtY(bodyGeom, dloFrame.dloYBot)
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

  // 洞壁内饰化：门洞 + 全部侧窗分片洞口的洞壁（横贯车宽）改判深色内饰材质，
  // |z| ≥ 外蒙皮端面的倒角环带保留车身色作门框/窗框唇边；风挡/后风挡斜面玻璃带
  // 中央区改判暗舱底（A/C 柱区留车身色）——透明玻璃后读到的是舱影而非车漆壁。
  // 车顶边框：风挡/后风挡玻璃顶边停在柱顶圆角切点下方 FRONT_GLASS_TOP_BORDER 处——
  // 玻璃不包裹圆角、不搭上车顶；车顶圆角（车身色）本身即「车身色顶部边界」。
  // 暗舱底（内饰深色）只改判到玻璃顶边：玻璃覆盖区读作舱影，玻璃以上全是车身色，
  // 不再出现「玻璃上方一条宽深色厚板」的观感。
  const glassBands = [
    { x1: cabin.windshield.x1, y1: cabin.windshield.y1,
      x2: cabin.windshield.x2, y2: cabin.windshield.y2,
      bottomInset: cabin.windshield.bottomInset + 0.01,
      topInset: cabin.windshield.topInset + FRONT_GLASS_TOP_BORDER,
      halfWidth: cabin.windshield.width / 2 }
  ]
  if (cabin.rearWindow) {
    glassBands.push({
      x1: cabin.rearWindow.x1, y1: cabin.rearWindow.y1,
      x2: cabin.rearWindow.x2, y2: cabin.rearWindow.y2,
      bottomInset: ROOF_FILLETS.cPillarBottom + 0.01,
      topInset: cabin.rearWindow.topInset + FRONT_GLASS_TOP_BORDER,
      halfWidth: cabin.rearWindow.width / 2
    })
  }
  splitBodyAperturesInterior(bodyGeom, apertureRects, bodyDepth / 2, glassBands, taperK, isBodyMaterial)

  return {
    bodyGeom,
    outlineShape: outlinePts.shape,
    bodyExtentZ,
    dloFrame,
    taperK,
    shoulderY
  }
}
