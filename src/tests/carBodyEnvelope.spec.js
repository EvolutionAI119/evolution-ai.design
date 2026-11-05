// 车身包络回归门禁：六车型 × 全部内饰件「零可见穿模」
//
// 为什么需要这一层：外观与内饰长期只靠「比车顶高度」的单点断言，
// 溜背/尾门斜面、车顶收窄、轮拱腔体三处全部是盲区——车顶最高点合规 ≠ 尾段合规。
// 本 spec 以 bodyEnvelope（真实侧视轮廓 + 收窄侧壁 + 轮拱椭圆腔体）为唯一判据，
// 把每个内饰件的 AABB 八角点逐个投进去：任一角点落在车身外表面之外即失败。
//
// 轮拱腔体是例外区：腔体内但被轮胎遮挡（|z| 在轮胎横向区间且低于该 X 处轮胎顶面）
// 记为 MASK——几何上仍在腔体内，但外观不可见，不判为穿模。
//
// 坐标系同 carProfile：X+ 车头、Y+ 向上、Z+ 副驾侧，地面 Y=0，米制。
import { describe, it, expect } from 'vitest'
import { deriveCarProfile } from '../utils/carProfile.js'
import { carTypeParams } from '../config/carPresets.js'
import {
  deriveInteriorLayout, deriveInteriorTrim, deriveIpConsoleLayout, deriveLuggageLayout
} from '../utils/carInteriorLayout.js'
import {
  bodyEnvelope, boxOutside, archRearEdgeX, tireTopAt, bodyTopAt
} from '../utils/carBodyEnvelope.js'
import { BODY_BEVEL_SIZE } from '../utils/carGlass.js'

const ALL_TYPES = ['sedan', 'suv', 'coupe', 'sport', 'mpv', 'pickup']
const profileOf = (type) => deriveCarProfile({ ...carTypeParams[type] }, type)
// 与车身挤出倒角外扩量同源的容差：外表面位于轮廓之外 BODY_BEVEL_SIZE
const TOL = BODY_BEVEL_SIZE + 0.002

const boxOf = (b) => ({ x0: b.x0, x1: b.x1, y0: b.y0, y1: b.y1, z0: b.z0, z1: b.z1 })
const withHalfZ = (b) => ({ ...boxOf(b), z0: -b.halfZ, z1: b.halfZ })

/**
 * 收集全部「内饰实体件」的 AABB（不含轮拱饰盒——它按定义占据轮腔，是边界本身）。
 * 座位按真实构件分别取（坐垫矩形 + 靠背/头枕多边形角点），
 * 避免斜放靠背 + 头枕的整体 AABB 把不存在的角点判成穿模。
 */
const interiorBoxes = (P) => {
  const L = deriveInteriorLayout(P)
  const T = deriveInteriorTrim(P)
  const C = deriveIpConsoleLayout(P)
  const G = deriveLuggageLayout(P)
  const out = []
  const add = (name, b) => b && out.push([name, boxOf(b)])

  // ---- 仪表台 / 中控 ----
  add('ip.upper', C.shells.upper)
  add('ip.lower', C.shells.lower)
  add('ip.cluster', C.cluster)
  add('ip.display', C.display)
  C.vents.center.forEach((b, i) => add(`ip.ventCenter${i}`, b))
  C.vents.side.forEach((b, i) => add(`ip.ventSide${i}`, b))
  add('ip.glovebox', C.glovebox)
  add('ip.airbagDoor', C.airbagDoor)
  add('ip.kneePanel', C.kneePanel)
  add('console.wirelessPad', C.wirelessPad)
  add('console.shifter', C.shifter)
  C.cups.forEach((b, i) => add(`console.cup${i}`, b))
  add('console.armrestLid', C.armrestLid)
  add('console.rearVent', C.rearVent)

  // ---- 方向盘（圆环以外周 AABB 近似）----
  const sw = L.steerWheel
  add('steerWheel', {
    x0: sw.x - sw.r, x1: sw.x + sw.r, y0: sw.y - sw.r, y1: sw.y + sw.r,
    z0: sw.z - 0.04, z1: sw.z + 0.04
  })

  // ---- 座舱包裹层 / 门板 / 安全带 ----
  ;(T.carpet.spans ?? [T.carpet]).forEach((sp, i) => add(`trim.carpet${i}`, {
    x0: sp.x0, x1: sp.x1, y0: T.carpet.y0, y1: T.carpet.y1, z0: -sp.halfZ, z1: sp.halfZ
  }))
  add('trim.headliner', withHalfZ(T.headliner))
  add('trim.tunnel.rear', { ...withHalfZ(T.tunnel.rear), z0: -T.tunnel.halfZ, z1: T.tunnel.halfZ })
  T.doors.forEach((d) => add(`trim.door.${d.key}${d.side > 0 ? 'R' : 'L'}`, d))
  T.armrests.forEach((a) => add(`trim.armrest.${a.key}${a.side > 0 ? 'R' : 'L'}`, a))
  T.belts.forEach((b) => add(`trim.belt.${b.kind}.r${b.row}${b.side > 0 ? 'R' : 'L'}`, {
    x0: b.x - 0.02, x1: b.x + 0.02, y0: b.y - 0.02, y1: b.y + 0.02, z0: b.z - 0.02, z1: b.z + 0.02
  }))

  // ---- 座椅（按构件）----
  for (const row of L.rows) {
    const cz = row.seat.centers
    const hw = row.seat.width / 2
    const e = row.envelope
    cz.forEach((c, i) => {
      add(`seat.r${row.row}s${i}.cushion`, {
        x0: e.cushion.x0, x1: e.cushion.x1, y0: e.cushion.y0, y1: e.cushion.y1,
        z0: c - hw, z1: c + hw
      })
      for (const [tag, poly] of [['back', e.backrest.points], ['head', e.headrest.points]]) {
        poly.forEach((p, k) => add(`seat.r${row.row}s${i}.${tag}${k}`, {
          x0: p[0] - 0.005, x1: p[0] + 0.005, y0: p[1] - 0.005, y1: p[1] + 0.005,
          z0: c - hw, z1: c + hw
        }))
      }
    })
  }

  // ---- 前/后行李舱 ----
  if (G.frunk) {
    add('frunk.tub', {
      x0: G.frunk.x0, x1: G.frunk.x1, y0: G.frunk.floorY, y1: G.frunk.topY,
      z0: -G.frunk.halfZ, z1: G.frunk.halfZ
    })
  }
  const r = G.rear
  add('cargo.floor', r.floorCarpet)
  r.sideLiners.forEach((b, i) => add(`cargo.sideLiner${i}`, b))
  add('cargo.frontLiner', r.frontLiner)
  add('cargo.lidInner', r.lidInner)
  add('cargo.sillPlate', r.sillPlate)
  add('cargo.underfloorWell', r.underfloorWell)
  return out
}

const fmt = (b) => `x[${[b.x0, b.x1].map((v) => Math.round(v * 1000))}] ` +
  `y[${[b.y0, b.y1].map((v) => Math.round(v * 1000))}] ` +
  `z[${[b.z0, b.z1].map((v) => Math.round(v * 1000))}]`

describe('车身包络判据（carBodyEnvelope）自身正确性', () => {
  it.each(ALL_TYPES)('%s 轮廓取样闭合并包住车身极值', (type) => {
    const P = profileOf(type)
    const env = bodyEnvelope(P)
    expect(env.poly.length).toBeGreaterThan(20)
    expect(env.frontX).toBeCloseTo(P.frontX, 6)
    expect(env.rearX).toBeCloseTo(P.rearX, 6)
    // 采样必须全部有限——出现 NaN 会让上界/侧壁判定整体失效（静默放行）
    expect(env.poly.every((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]))).toBe(true)
    // 车顶最高点取样 ≈ roofTopY（采样误差 ≤ 5mm）
    let top = -Infinity
    for (const p of env.poly) top = Math.max(top, p[1])
    expect(Math.abs(top - P.roofTopY)).toBeLessThan(0.005)
    expect(bodyTopAt(env.poly, P.frontWheelX)).toBeGreaterThan(P.archY)
  })

  it.each(ALL_TYPES)('%s 轮拱后缘与轮胎顶面随高度单调收敛', (type) => {
    const P = profileOf(type)
    const env = bodyEnvelope(P)
    for (const a of env.arches) {
      // 拱心高度的后缘最靠后（腔体最深）
      expect(archRearEdgeX(a, a.cy)).toBeLessThan(archRearEdgeX(a, a.cy + a.ry * 0.5))
      // 超出拱顶 → 该高度无腔体
      expect(archRearEdgeX(a, a.cy + a.ry + 0.01)).toBe(-Infinity)
      // 轮胎顶面在轮心处最高 = 2×轮半径
      const top = tireTopAt(P, a.cx, a.side)
      expect(top).toBeCloseTo(P.archY + (P.wheelR ?? P.archY), 6)
      expect(tireTopAt(P, a.cx + 1.0, a.side)).toBe(-Infinity)
    }
  })
})

describe('六车型全部内饰件零可见穿模', () => {
  it.each(ALL_TYPES)('%s 每个内饰件都落在车身外表面之内', (type) => {
    const P = profileOf(type)
    const env = bodyEnvelope(P)
    const fails = []
    const masked = []
    for (const [name, box] of interiorBoxes(P)) {
      const res = boxOutside(env, box, TOL)
      if (!res) continue
      if (res.visibleCount > 0) {
        fails.push(`${name} ${fmt(box)} -> ${res.worst.kind}${res.worst.side ? ':' + res.worst.side : ''} ` +
          `@(${Math.round(res.worst.x * 1000)},${Math.round(res.worst.y * 1000)},${Math.round(res.worst.z * 1000)})`)
      } else {
        masked.push(name)
      }
    }
    // 可见穿模：必须为 0（逐件列出尺寸，便于定位）
    expect(fails, `${type} 可见穿模：\n${fails.join('\n')}`).toEqual([])
    // 其余命中均为「进了轮腔但被轮胎挡住」——几何上应尽量归位，但外观不可见，不判失败
    expect(masked.length).toBeLessThan(interiorBoxes(P).length)
  })
})
