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
