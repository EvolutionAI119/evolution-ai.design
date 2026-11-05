// 车身面片归属（平台侧采纳《SISA 提案 PROPOSAL_TO_PLATFORM_PANEL_TOPOLOGY》修法 2）
//
// 为什么要有这一层
// --------------
// 提案的 R2 根因是「分件按参数矩形各自取条带 ⟹ 同一批面片被两个分件各取一次
// ⟹ 分件在空间上重叠 ⟹ 渲染即穿模」。平台侧存在**同构**缺陷：车身壳的
// 「洞壁内饰化」原用「三角形重心落在口径矩形 bbox 内」的**判定式**改判，
//   1) bbox 是洞口的粗近似（实测 fixedFront 多边形外占比 53%、door-lower 45%），
//      矩形分支把真实洞口之外的车身三角形也改判成内饰 → 洞口下沿锯齿；
//   2) 判定式是多条判据链各自命中即改判，同一面片可能被两条链重复命中；
//   3) 斜面玻璃带分支用重心判「是否落在玻璃半宽内」，而斜面墙几何是
//      **整宽大三角形**（重心 cz ≈ 0）⟹ 整片被染成暗舱深色 → 黑带 + 齿状边。
//
// 平台侧修法（与提案修法 2 等价）
// ------------------------------
//   1) 判据由「bbox 近似」换成「**真实洞口多边形的等距带**」：
//      polygonEdgeDistance ≤ APERTURE_BAND。覆盖面积从 bbox 的 ~10 倍降到 ~1.1 倍，
//      且边界严格贴合洞口轮廓 ⟹ 洞口下沿不再锯齿。
//   2) 归属由「判定式」换成「**面片归属**」：每个三角形在一次遍历中拿到
//      **恰好一个** owner（车漆 / 洞壁内饰）⟹ 天然互斥（A2）且穷尽（A1）。
//   3) 斜面玻璃带**不再改判车身面片**（提案 R2 同构根因）：舱影改为独立几何，
//      覆盖区与玻璃逐点同源（同一条脊柱线 + 同一逐点半宽）⟹ 两件不可能重叠。
//
// 判据口径（全部为米，坐标系 X+ 车头 / Y+ 向上 / Z+ 副驾侧）
//   - 洞壁带：三角重心到最近洞口多边形边界的距离 ≤ APERTURE_BAND
//   - 端盖排除：|nz| > 0.6 的三角形是 ±Z 端盖（车侧可见漆面）⟹ 必为车漆
//   - 水平壁排除：|ny| > 0.8 的三角形是门槛/窗台水平面 ⟹ 必为车漆
//   - 外蒙皮排除：isBodyMaterial 为 false（贴外轮廓线）⟹ 必为车漆
//
// 时间口径（对应「检测频率」）：归属在**装配期一次性**求解（每次参数变更
// 重建车身时），不在渲染帧循环里做逐帧检测 ⟹ 零逐帧开销。

import * as THREE from 'three'
import { polygonEdgeDistance, BODY_BEVEL_SIZE } from '../../utils/carGlass.js'

/** 车身壳面片归属枚举 */
export const SHELL_OWNER = {
  /** 车漆面（外蒙皮 / 门框唇边 / 柱条 / 水平壁） */
  PAINT: 0,
  /** 洞口内壁（座舱读作深色内饰） */
  APERTURE_LINER: 1
}

/**
 * 洞口带容差（米）。
 *
 * ExtrudeGeometry 的 bevel 对**洞**是收缩：洞壁面实际落在洞口多边形**内侧**
 * BODY_BEVEL_SIZE 处（实测车身壳洞壁三角形重心距洞口边界 12.0mm = bevelSize）。
 * 因此判定带必须覆盖 bevelSize，再留 2mm 余量吃掉倒角环带的三角形。
 */
export const APERTURE_BAND = BODY_BEVEL_SIZE + 0.002

/** 端盖（±Z 侧漆面）法向门控：|nz| 超过此值即端盖，必为车漆 */
export const CAP_NORMAL_LIMIT = 0.6
/** 水平壁（门槛顶面 / 窗台）法向门控 */
export const LEDGE_NORMAL_LIMIT = 0.8

/**
 * 求解每个车身面片的归属（互斥且穷尽）。
 *
 * @param {THREE.BufferGeometry} geom 车身几何（非索引）
 * @param {object} o
 * @param {Array<{key:string, pts:Array<number[]>}>} o.apertures 真实洞口多边形（与挖洞用的同一份）
 * @param {(y:number)=>number} o.zCapAt 内腔界（外蒙皮端面保留带）随收窄联动
 * @param {(x:number,y:number)=>boolean} [o.isBodyMaterial] 点是否在车身实体内（排除贴轮廓线的外皮）
 * @param {number} [o.band] 洞口带容差
 * @returns {{ owners: Uint8Array, paint: number, liner: number }} owners[i] = 面片 i 的归属
 */
export function assignShellOwners(geom, {
  apertures = [], zCapAt, isBodyMaterial = null, band = APERTURE_BAND
}) {
  const pos = geom.attributes.position
  const arr = pos.array
  const nTri = pos.count / 3
  const owners = new Uint8Array(nTri)
  let paint = 0
  let liner = 0
  const zCap = typeof zCapAt === 'function' ? zCapAt : () => (zCapAt ?? Infinity)
  for (let i = 0; i < nTri; i++) {
    const o = i * 9
    const cx = (arr[o] + arr[o + 3] + arr[o + 6]) / 3
    const cy = (arr[o + 1] + arr[o + 4] + arr[o + 7]) / 3
    const cz = (arr[o + 2] + arr[o + 5] + arr[o + 8]) / 3
    let owner = SHELL_OWNER.PAINT
    if (apertures.length && Math.abs(cz) < zCap(cy)) {
      // 面几何法线（位置叉积；判据只取朝向）
      const e1x = arr[o + 3] - arr[o], e1y = arr[o + 4] - arr[o + 1], e1z = arr[o + 5] - arr[o + 2]
      const e2x = arr[o + 6] - arr[o], e2y = arr[o + 7] - arr[o + 1], e2z = arr[o + 8] - arr[o + 2]
      let nx = e1y * e2z - e1z * e2y
      let ny = e1z * e2x - e1x * e2z
      let nz = e1x * e2y - e1y * e2x
      const nl = Math.hypot(nx, ny, nz) || 1
      nx /= nl; ny /= nl; nz /= nl
      // 端盖（车侧漆面）与水平壁（门槛/窗台）从车外可见 ⟹ 必留车漆
      if (Math.abs(nz) <= CAP_NORMAL_LIMIT && Math.abs(ny) <= LEDGE_NORMAL_LIMIT) {
        let d = Infinity
        for (let a = 0; a < apertures.length; a++) {
          const dd = polygonEdgeDistance(cx, cy, apertures[a].pts)
          if (dd < d) d = dd
        }
        if (d <= band && (!isBodyMaterial || isBodyMaterial(cx, cy))) {
          owner = SHELL_OWNER.APERTURE_LINER
        }
      }
    }
    owners[i] = owner
    if (owner === SHELL_OWNER.APERTURE_LINER) liner++
    else paint++
  }
  return { owners, paint, liner }
}

/**
 * 按归属把面片重排为两个材质组（组 0 = 车漆，组 1 = 洞壁内饰）。
 * 重排后每个面片**恰好出现一次**（互斥），且全部面片都被两组穷尽。
 *
 * @param {THREE.BufferGeometry} geom
 * @param {Uint8Array} owners
 * @returns {{ paint: number, liner: number }} 两组面片数
 */
export function groupShellByOwner(geom, owners) {
  const arr = geom.attributes.position.array
  const nTri = owners.length
  let paint = 0
  for (let i = 0; i < nTri; i++) if (owners[i] === SHELL_OWNER.PAINT) paint++
  const out = new Float32Array(arr.length)
  let k = 0
  // 车漆组在前，洞壁内饰组在后（材质数组顺序固定为 [bodyMat, interiorMat]）
  for (let pass = 0; pass < 2; pass++) {
    for (let i = 0; i < nTri; i++) {
      if (owners[i] !== pass) continue
      const o = i * 9
      for (let j = 0; j < 9; j++) out[k++] = arr[o + j]
    }
  }
  // three.js 的 group start/count 单位是**顶点**数（不是三角形数）
  const paintVerts = paint * 3
  geom.setAttribute('position', new THREE.BufferAttribute(out, 3))
  geom.deleteAttribute('uv')            // 顶点重排后 uv 失效；本模型不使用贴图
  geom.clearGroups()
  geom.addGroup(0, paintVerts, 0)
  geom.addGroup(paintVerts, nTri * 3 - paintVerts, 1)
  return { paint, liner: nTri - paint }
}

/**
 * 归属审计（对应提案 A1 / A2 的平台等价判据）。
 *
 * A1 穷尽：两个组的面片数之和 == 几何面片总数（无面片被丢弃）。
 * A2 互斥：两个组在顶点区间上**不重叠**且完整覆盖（无面片被两个组各取一次）。
 * A2' 无污染：内饰组不含端盖（|nz| > 0.6）与水平壁（|ny| > 0.8）。
 *
 * @param {THREE.BufferGeometry} geom
 * @returns {{ total:number, paint:number, liner:number, exhaustive:boolean, exclusive:boolean, clean:boolean }}
 */
export function auditShellOwners(geom) {
  const arr = geom.attributes.position.array
  const nTri = arr.length / 9
  const nVerts = arr.length / 3
  const groups = geom.groups
  let paint = 0
  let liner = 0
  let exclusive = true
  let cursor = 0
  for (const g of groups) {
    if (g.start !== cursor) exclusive = false       // 组间有空隙或重叠
    cursor = g.start + g.count
    if (g.materialIndex === 0) paint += g.count / 3
    else liner += g.count / 3
  }
  if (cursor !== nVerts) exclusive = false
  // 内饰组洁净度：不得含端盖 / 水平壁
  let clean = true
  const linerGroup = groups.find((g) => g.materialIndex === 1)
  if (linerGroup) {
    const startTri = linerGroup.start / 3
    const countTri = linerGroup.count / 3
    for (let t = startTri; t < startTri + countTri; t++) {
      const o = t * 9
      const e1x = arr[o + 3] - arr[o], e1y = arr[o + 4] - arr[o + 1], e1z = arr[o + 5] - arr[o + 2]
      const e2x = arr[o + 6] - arr[o], e2y = arr[o + 7] - arr[o + 1], e2z = arr[o + 8] - arr[o + 2]
      let nx = e1y * e2z - e1z * e2y
      let ny = e1z * e2x - e1x * e2z
      let nz = e1x * e2y - e1y * e2x
      const l = Math.hypot(nx, ny, nz) || 1
      nx /= l; ny /= l; nz /= l
      if (Math.abs(nz) > CAP_NORMAL_LIMIT || Math.abs(ny) > LEDGE_NORMAL_LIMIT) { clean = false; break }
    }
  }
  return {
    total: nTri,
    paint,
    liner,
    exhaustive: paint + liner === nTri,
    exclusive,
    clean
  }
}
