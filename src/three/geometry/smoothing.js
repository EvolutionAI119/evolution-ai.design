/**
 * 车身几何法线后处理（自 Car3D.vue P1 拆分，纯函数，无场景依赖）
 */
import * as THREE from 'three'

/**
 * 按位置焊接后平滑法线（保留硬边）
 *
 * ExtrudeGeometry 为非索引几何：每个三角形持有一份独立法线。greenhouse 收窄是随 y 变化的
 * 线性 Z 缩放，会把原本平坦的侧围端盖变成双曲面；此时 computeVertexNormals() 只能给出
 * 逐面法线——侧围 / 车顶 / 倒角上因此出现一片片明暗不同的三角面（用户读作「亮色破面」），
 * 车顶薄倒角更会被切成一串高亮细条（读作「尖刺」）。
 * 这里按位置把法线焊接平均，只合并夹角小于阈值的面，腰线、轮拱等硬边仍是硬边。
 *
 * hardEdgesY：按高度钉死的硬边（米）。greenhouse 收窄在腰带线（DLO 底边）处存在
 * 斜率拐点（tumblehome 8°~26°，小于上面的焊接阈值 32°）——若放任焊接平均，拐点两侧
 * 法线渐变扫过，整条腰线在掠射角下渲染成一条宽泛的爆白亮带（白带异常）。真车腰线
 * 是一条锐利折痕：高光收成一条细亮线、上下两块面各自均匀过渡（层次感）。本参数把
 * 「三角形重心分居拐点高度两侧」的面对排除在焊接之外，拐点因此保持真正的硬边。
 */
export function smoothNormalsKeepHardEdges(geom, tol = 1e-4, angleDeg = 32, hardEdgesY = null) {
  const pos = geom.attributes.position
  const arr = pos.array
  const n = pos.count
  const cosT = Math.cos((angleDeg * Math.PI) / 180)
  const keyOf = (i) => `${Math.round(arr[i * 3] / tol)}_${Math.round(arr[i * 3 + 1] / tol)}_${Math.round(arr[i * 3 + 2] / tol)}`

  // 位置 → 落在该位置上的所有顶点索引
  const buckets = new Map()
  for (let i = 0; i < n; i++) {
    const k = keyOf(i)
    const b = buckets.get(k)
    if (b) b.push(i); else buckets.set(k, [i])
  }

  // 逐三角形面法线（同一三角形的三个顶点共用）；同时记录面心高度供硬边跨侧判定
  const face = new Float32Array(n * 3)
  const triCY = new Float32Array(n / 3)
  for (let t = 0; t < n; t += 3) {
    const o = t * 3
    const ux = arr[o + 3] - arr[o], uy = arr[o + 4] - arr[o + 1], uz = arr[o + 5] - arr[o + 2]
    const vx = arr[o + 6] - arr[o], vy = arr[o + 7] - arr[o + 1], vz = arr[o + 8] - arr[o + 2]
    let nx = uy * vz - uz * vy
    let ny = uz * vx - ux * vz
    let nz = ux * vy - uy * vx
    const len = Math.hypot(nx, ny, nz) || 1
    nx /= len; ny /= len; nz /= len
    for (let j = 0; j < 3; j++) {
      const w = (t + j) * 3
      face[w] = nx; face[w + 1] = ny; face[w + 2] = nz
    }
    triCY[t / 3] = (arr[o + 1] + arr[o + 4] + arr[o + 7]) / 3
  }

  // 焊接平均：仅合并与自身面夹角小于阈值、且不与自身面分居硬边两侧的相邻面
  const out = new Float32Array(n * 3)
  for (let i = 0; i < n; i++) {
    const own = i * 3
    const f0x = face[own], f0y = face[own + 1], f0z = face[own + 2]
    const ci = triCY[(i / 3) | 0]
    let sx = 0, sy = 0, sz = 0
    for (const j of buckets.get(keyOf(i))) {
      const q = j * 3
      if (face[q] * f0x + face[q + 1] * f0y + face[q + 2] * f0z < cosT) continue
      if (hardEdgesY) {
        const cj = triCY[(j / 3) | 0]
        let straddle = false
        for (const ye of hardEdgesY) {
          if ((ci - ye) * (cj - ye) < 0) { straddle = true; break }
        }
        if (straddle) continue
      }
      sx += face[q]; sy += face[q + 1]; sz += face[q + 2]
    }
    const len = Math.hypot(sx, sy, sz) || 1
    out[own] = sx / len; out[own + 1] = sy / len; out[own + 2] = sz / len
  }
  geom.setAttribute('normal', new THREE.BufferAttribute(out, 3))
}

/**
 * 细分侧围端盖上的长边三角形（就地重建 position）。
 *
 * earcut 会把侧围端盖切成跨越整个车门/后翼子板的大三角形：三角形本身共面，
 * 但它的角点常常落在倒角/洞口等法线突变处，顶点法线差异被线性插值铺满整块面板，
 * 渲染成一条横贯翼子板的斜向明暗渐变（用户读作「拓扑错误/破面」）。
 * 平滑法线只能在顶点之间插值，无法修正长距离跨度；因此先按最长边二分，把端盖
 * 三角形细分到 maxEdge 以内——法线差异只残留 0.12m 级小面内，肉眼不可见。
 *
 * 只处理端盖（面法线 |nz| > 0.95，即与车身侧面平行的平面），倒角/顶面/底面
 * 不细分，避免无意义地增加三角形。二分点严格落在原边上（与相邻面共线），
 * 不产生裂缝；细分后法线由 smoothNormalsKeepHardEdges 统一重算。
 *
 * @param {THREE.BufferGeometry} geom 非索引车身挤出几何
 * @param {number} [maxEdge=0.12] 允许的最长边（米）
 * @param {number} [maxPasses=8] 最多二分轮数
 */
export function subdivideSideCapLongEdges(geom, maxEdge = 0.12, maxPasses = 8) {
  let arr = geom.attributes.position.array
  const limit2 = maxEdge * maxEdge
  let changedAny = false

  for (let pass = 0; pass < maxPasses; pass++) {
    const out = []
    let changed = 0
    for (let o = 0; o < arr.length; o += 9) {
      const ax = arr[o], ay = arr[o + 1], az = arr[o + 2]
      const bx = arr[o + 3], by = arr[o + 4], bz = arr[o + 5]
      const cx = arr[o + 6], cy = arr[o + 7], cz = arr[o + 8]
      // 面法线 z 分量为端盖判据（挤出端盖与 Z 轴平行；倒角/顶面/底面不参与）
      const ux = bx - ax, uy = by - ay, uz = bz - az
      const vx = cx - ax, vy = cy - ay, vz = cz - az
      const nx = uy * vz - uz * vy
      const ny = uz * vx - ux * vz
      const nz = ux * vy - uy * vx
      const nl = Math.hypot(nx, ny, nz) || 1
      if (Math.abs(nz / nl) <= 0.95) { out.push(ax, ay, az, bx, by, bz, cx, cy, cz); continue }
      const ab = (bx - ax) ** 2 + (by - ay) ** 2 + (bz - az) ** 2
      const bc = (cx - bx) ** 2 + (cy - by) ** 2 + (cz - bz) ** 2
      const ca = (ax - cx) ** 2 + (ay - cy) ** 2 + (az - cz) ** 2
      const longest = Math.max(ab, bc, ca)
      if (longest <= limit2) { out.push(ax, ay, az, bx, by, bz, cx, cy, cz); continue }
      // 最长边二分；拆分保持原绕序，避免法线/背面剔除翻转
      if (longest === ab) {
        const mx = (ax + bx) / 2, my = (ay + by) / 2, mz = (az + bz) / 2
        out.push(ax, ay, az, mx, my, mz, cx, cy, cz)
        out.push(mx, my, mz, bx, by, bz, cx, cy, cz)
      } else if (longest === bc) {
        const mx = (bx + cx) / 2, my = (by + cy) / 2, mz = (bz + cz) / 2
        out.push(ax, ay, az, bx, by, bz, mx, my, mz)
        out.push(ax, ay, az, mx, my, mz, cx, cy, cz)
      } else {
        const mx = (cx + ax) / 2, my = (cy + ay) / 2, mz = (cz + az) / 2
        out.push(ax, ay, az, bx, by, bz, mx, my, mz)
        out.push(bx, by, bz, cx, cy, cz, mx, my, mz)
      }
      changed++
    }
    if (!changed) break
    changedAny = true
    arr = new Float32Array(out)
  }

  if (!changedAny) return 0
  geom.setAttribute('position', new THREE.BufferAttribute(arr, 3))
  geom.deleteAttribute('uv')       // 重排后 uv 数量不再匹配；本模型不使用贴图
  geom.deleteAttribute('normal')   // 收窄后由 smoothNormalsKeepHardEdges 统一重算
  return arr.length / 9
}

/**
 * 沿 |z| = zLim 平面把三角形切成「外环带 / 内腔壁」两组（就地重建 position）。
 *
 * 车身是整宽挤出：门洞/侧窗洞口的横贯隧道壁在 ExtrudeGeometry 里每条洞边只有
 * **一个横跨全宽的四边形**（两个三角形，顶点落在两端外蒙皮上）。洞壁内饰化只能对
 * 整个三角形做整块改判——要么全深色（外缘缺一圈车色门框，洞口边缘露出锯齿状深色
 * 三角），要么全车色（开门后洞内是一块车漆板）。
 * 先在收窄前把横跨 |z| 的三角形切开，把「外环带」与「内腔」分离：外环带保留车身色
 * 作门框/窗框唇边，内腔改判深色，且两者之间的分界线是一条沿 Z 的直线（不再锯齿）。
 *
 * 必须在 greenhouse 收窄（z 随 y 缩放）之前调用：收窄后同一 z 平面变成曲面，
 * 切分点不再与 `zCapAt(y) = zLim·taperK(y)` 判据重合。
 *
 * @param {THREE.BufferGeometry} geom 非索引车身挤出几何
 * @param {number} zLim 切面（米，正值；对称切 ±zLim）
 * @returns {number} 被切分的三角形数
 */
export function splitTrianglesAtAbsZ(geom, zLim) {
  const pos = geom.attributes.position
  const arr = pos.array
  const out = []
  let splitCount = 0

  // 凸多边形按单个 z 半空间裁剪，保持原顶点绕序（扇形三角化后朝向不变）
  const clipByZ = (poly, limit, keepAbove) => {
    const f = (p) => (keepAbove ? p[2] - limit : limit - p[2])
    const res = []
    for (let i = 0; i < poly.length; i++) {
      const A = poly[i]
      const B = poly[(i + 1) % poly.length]
      const fa = f(A)
      const fb = f(B)
      if (fa >= 0) res.push(A)
      if ((fa >= 0) !== (fb >= 0)) {
        const t = fa / (fa - fb)
        res.push([
          A[0] + (B[0] - A[0]) * t,
          A[1] + (B[1] - A[1]) * t,
          A[2] + (B[2] - A[2]) * t
        ])
      }
    }
    return res
  }
  // 扇形三角化；丢弃退化片（顶点重合 / 面积≈0），否则会留下零面积三角形
  const emit = (poly) => {
    if (poly.length < 3) return
    let area = 0
    for (let i = 0; i < poly.length; i++) {
      const A = poly[i]
      const B = poly[(i + 1) % poly.length]
      const C = poly[(i + 2) % poly.length]
      const ux = B[0] - A[0], uy = B[1] - A[1], uz = B[2] - A[2]
      const vx = C[0] - A[0], vy = C[1] - A[1], vz = C[2] - A[2]
      const cx = uy * vz - uz * vy
      const cy = uz * vx - ux * vz
      const cz = ux * vy - uy * vx
      area += Math.hypot(cx, cy, cz) / 2
    }
    if (area < 1e-9) return
    for (let i = 1; i < poly.length - 1; i++) {
      out.push(...poly[0], ...poly[i], ...poly[i + 1])
    }
  }

  for (let o = 0; o < arr.length; o += 9) {
    const tri = [
      [arr[o], arr[o + 1], arr[o + 2]],
      [arr[o + 3], arr[o + 4], arr[o + 5]],
      [arr[o + 6], arr[o + 7], arr[o + 8]]
    ]
    // 区域编号：-1 = −z 外环带，0 = 内腔，+1 = +z 外环带。
    // 注意不能用 |z| ≥ zLim 判断「整体在外」：整宽洞壁的两个三角形顶点都在
    // ±bodyDepth/2，但三角形本身横跨内腔，必须切开。
    const regionOf = (z) => (z >= zLim ? 1 : z <= -zLim ? -1 : 0)
    const r0 = regionOf(tri[0][2])
    const r1 = regionOf(tri[1][2])
    const r2 = regionOf(tri[2][2])
    if (r0 === r1 && r1 === r2) {
      out.push(...tri[0], ...tri[1], ...tri[2])
      continue
    }
    // 内腔：|z| ≤ zLim
    emit(clipByZ(clipByZ(tri, -zLim, true), zLim, false))
    // 外环带：+z 侧 / −z 侧
    emit(clipByZ(tri, zLim, true))
    emit(clipByZ(tri, -zLim, false))
    splitCount++
  }

  if (!splitCount) return 0
  geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(out), 3))
  geom.deleteAttribute('uv')       // 重排后 uv 数量不再匹配；本模型不使用贴图
  geom.deleteAttribute('normal')   // 收窄后由 smoothNormalsKeepHardEdges 统一重算
  return splitCount
}

/**
 * 沿 y = yCut 平面切分跨越该高度的三角形（就地重建 position）。
 *
 * ExtrudeGeometry 的侧围端盖由 earcut 生成，其中存在大量细长三角形，部分会横跨
 * 腰带线。greenhouse 收窄在腰带线处存在斜率拐点（t 由钳位区进入倾角/桶面段），
 * 横跨拐点的三角形被压成「折板」：整个三角形只能持有一条面法线，无法表达上下
 * 两块板面的差异，掠射角下渲染成一块大面积渐变亮面（拓扑破面）。
 * 在收窄前把这类三角形沿拐点切成上/下两组（中间四边形拆两个三角形），
 * 使每个三角形只落在单侧平面或单侧曲面内；腰线仍由 smoothNormalsKeepHardEdges
 * 钉成硬边——高光收成锐利折线，不再出现跨越腰线的破面。
 *
 * @param {THREE.BufferGeometry} geom 非索引车身挤出几何
 * @param {number} yCut 切分高度（米），取 DLO 底边
 * @param {number} [eps=1e-4] 落在切面附近视为已在切面上（不拆，避免退化三角形）
 * @returns {number} 被切分的三角形数
 */
export function splitTrianglesAtY(geom, yCut, eps = 1e-4) {
  const pos = geom.attributes.position
  const arr = pos.array
  const out = []
  let splitCount = 0

  const pushTri = (a, b, c) => {
    out.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2])
  }

  for (let o = 0; o < arr.length; o += 9) {
    const v = [
      [arr[o], arr[o + 1], arr[o + 2]],
      [arr[o + 3], arr[o + 4], arr[o + 5]],
      [arr[o + 6], arr[o + 7], arr[o + 8]]
    ]
    const s = v.map((p) => (p[1] > yCut + eps ? 1 : p[1] < yCut - eps ? -1 : 0))
    // 全部同侧，或已有顶点压在切面上：保持原三角形（不制造退化面）
    if (s.includes(0) || !s.includes(1) || !s.includes(-1)) {
      pushTri(v[0], v[1], v[2])
      continue
    }
    // 唯一异侧顶点：循环移位到首位，保持原绕序不变
    let lone = 0
    for (let i = 0; i < 3; i++) {
      if (s[i] !== s[(i + 1) % 3] && s[i] !== s[(i + 2) % 3]) { lone = i; break }
    }
    const A = v[lone]
    const B = v[(lone + 1) % 3]
    const C = v[(lone + 2) % 3]
    const t1 = (yCut - A[1]) / (B[1] - A[1])
    const P = [A[0] + (B[0] - A[0]) * t1, yCut, A[2] + (B[2] - A[2]) * t1]
    const t2 = (yCut - A[1]) / (C[1] - A[1])
    const Q = [A[0] + (C[0] - A[0]) * t2, yCut, A[2] + (C[2] - A[2]) * t2]
    pushTri(A, P, Q)
    pushTri(B, P, Q)
    pushTri(B, Q, C)
    splitCount++
  }

  if (!splitCount) return 0
  geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(out), 3))
  geom.deleteAttribute('uv')       // 重排后 uv 数量不再匹配；本模型不使用贴图
  geom.deleteAttribute('normal')   // 收窄后由 smoothNormalsKeepHardEdges 统一重算
  return splitCount
}
