// 中试（pilot）· 后端真实链路批量跑
// 前端参数集（src/config/carPresets.js）→ POST /api/v1/car/generate（算法生成）
// → /api/v1/import-export 会话（参数校验 + 3D 预览点云）→ 导出 STEP/GLB/STL/OBJ/JSON
// → 通过 /download 取回并做格式校验。逐次记录成功/失败、耗时、失败环节、后端内存/句柄。
//
// 用法：node scripts/pilot_api_run.mjs [--runs 10] [--out pilot-artifacts/api] [--clamp-generate]
//   --clamp-generate：生成阶段先尝试原始前端参数（严格校验下预期 422），
//   再用夹紧到后端区间的参数重试，用于在参数源裁决前验证「生成→导出」链路。
import fs from 'node:fs'
import path from 'node:path'
import { execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { carTypeParams } from '../src/config/carPresets.js'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const BASE = 'http://127.0.0.1:8000'
const args = process.argv.slice(2)
const argOf = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const OUT_DIR = path.resolve(ROOT, argOf('--out', 'pilot-artifacts/api'))
const TOTAL = Number(argOf('--runs', 10))
const CLAMP_GENERATE = args.includes('--clamp-generate')
fs.mkdirSync(OUT_DIR, { recursive: true })

const PLAN = [
  ...Array(4).fill('sedan'),
  ...Array(3).fill('suv'),
  ...Array(3).fill('pickup')
]

// 前端扁平参数 → 后端分组参数（含前端/后端同名不同义的已知别名）
const toGroups = (p) => {
  const groups = {
    整车尺寸: {
      overall_length: p.overall_length,
      overall_width: p.overall_width,
      overall_height: p.overall_height,
      wheelbase: p.wheel_base,
      track_width: p.track_width,
      ground_clearance: p.ground_clearance
    },
    车身部件: {
      hood_length: p.hood_length,
      roof_length: p.roof_height,
      wheel_diameter: p.wheel_diameter,
      door_open_angle: p.door_open_angle,
      wheel_arch_flatten: p.wheel_arch_flatten
    },
    造型角度: {
      windshield_angle: p.windshield_angle,
      rear_window_angle: p.rear_window_angle,
      c_pillar_angle: p.rear_slant_angle,
      side_glass_angle: p.side_glass_angle,
      glass_barrel_angle: p.glass_barrel_angle
    }
  }
  return groups
}

// 已知后端区间（用于“夹紧后重试”，只为验证导出链路仍可产出，不掩盖前端越界事实）
const RANGES = {
  整车尺寸: {
    overall_length: [3000, 6000], overall_width: [1500, 2200], overall_height: [1200, 2000],
    wheelbase: [2000, 4000], track_width: [1400, 1800], ground_clearance: [100, 300]
  },
  车身部件: {
    hood_length: [1000, 1600], roof_length: [1200, 2000], wheel_diameter: [350, 600],
    door_open_angle: [0, 80], wheel_arch_flatten: [0, 0.5]
  },
  造型角度: {
    windshield_angle: [55, 75], rear_window_angle: [10, 60], c_pillar_angle: [20, 45],
    side_glass_angle: [1, 40], glass_barrel_angle: [0, 20]
  }
}
const clampGroups = (groups) => {
  const out = {}
  for (const [g, items] of Object.entries(groups)) {
    out[g] = {}
    for (const [k, v] of Object.entries(items)) {
      const r = RANGES[g]?.[k]
      out[g][k] = r ? Math.min(r[1], Math.max(r[0], v)) : v
    }
  }
  return out
}

// 分组参数 → 扁平参数（后端规范键，/car/generate 的扁平索引可直接命中）
const flatOfGroups = (groups) => {
  const out = {}
  for (const items of Object.values(groups)) Object.assign(out, items)
  return out
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function backendPid() {
  try {
    const out = execSync('netstat -ano', { encoding: 'utf8' })
    const line = out.split(/\r?\n/).find((l) => /:8000 .*LISTENING/.test(l))
    if (!line) return null
    const parts = line.trim().split(/\s+/)
    return Number(parts[parts.length - 1]) || null
  } catch { return null }
}

function backendStat(pid) {
  if (!pid) return null
  try {
    const out = execSync(
      `powershell -NoProfile -Command "$p=Get-Process -Id ${pid}; Write-Output \\"$($p.WorkingSet64) $($p.PrivateMemorySize64) $($p.HandleCount)\\""`,
      { encoding: 'utf8' }).trim()
    const [ws, priv, handles] = out.split(/\s+/).map(Number)
    return { wsMB: +(ws / 1048576).toFixed(1), privMB: +(priv / 1048576).toFixed(1), handles }
  } catch { return null }
}

async function req(method, url, body, timeoutMs = 180000) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  const t0 = Date.now()
  try {
    const res = await fetch(BASE + url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal
    })
    const ct = res.headers.get('content-type') || ''
    const data = ct.includes('json') || ct.includes('text') ? await res.text() : await res.arrayBuffer()
    return { ok: res.ok, status: res.status, ms: Date.now() - t0, data }
  } catch (e) {
    return { ok: false, status: 0, ms: Date.now() - t0, error: e.name === 'AbortError' ? 'timeout' : String(e.message || e) }
  } finally {
    clearTimeout(timer)
  }
}

function bboxOfComponents(components) {
  let min = [Infinity, Infinity, Infinity]
  let max = [-Infinity, -Infinity, -Infinity]
  let points = 0
  const walk = (node) => {
    if (Array.isArray(node)) {
      if (node.length === 3 && node.every((n) => typeof n === 'number')) {
        points++
        for (let i = 0; i < 3; i++) {
          if (node[i] < min[i]) min[i] = node[i]
          if (node[i] > max[i]) max[i] = node[i]
        }
        return
      }
      for (const n of node) walk(n)
    }
  }
  for (const c of components) walk(c.points)
  if (!points) return null
  return {
    points,
    min: min.map((v) => Math.round(v * 10) / 10),
    max: max.map((v) => Math.round(v * 10) / 10),
    span: max.map((v, i) => Math.round((v - min[i]) * 10) / 10),
    // 生成器坐标：x=车长, y=车宽, z=车高（z 从地面起算）
    lengthMm: Math.round((max[0] - min[0]) * 10) / 10,
    widthMm: Math.round((max[1] - min[1]) * 10) / 10,
    heightMm: Math.round(max[2] * 10) / 10
  }
}

const magic = {
  step: (buf) => {
    const s = buf.toString('utf8', 0, 40)
    return s.startsWith('ISO-10303-21') && buf.toString('utf8').includes('END-ISO-10303-21')
  },
  glb: (buf) => buf.length > 12 && buf.toString('ascii', 0, 4) === 'glTF',
  stl: (buf) => buf.length > 84 && (/^solid/.test(buf.toString('utf8', 0, 5)) || buf.length >= 84 + 50),
  obj: (buf) => /\nv /.test(buf.toString('utf8', 0, 4000)) && /\nf /.test(buf.toString('utf8')),
  json: (buf) => {
    try { JSON.parse(buf.toString('utf8')) ; return true } catch { return false }
  }
}

const results = []
let pid = backendPid()
const statStart = backendStat(pid)

for (let i = 0; i < TOTAL; i++) {
  const type = PLAN[i % PLAN.length]
  const params = carTypeParams[type]
  const runId = `run${String(i + 1).padStart(2, '0')}-${type}`
  const dir = path.join(OUT_DIR, runId)
  fs.mkdirSync(dir, { recursive: true })
  const rec = {
    run: i + 1, runId, carType: type,
    params: {
      overall_length: params.overall_length, overall_width: params.overall_width,
      overall_height: params.overall_height, wheelbase: params.wheel_base,
      windshield_angle: params.windshield_angle, wheel_diameter: params.wheel_diameter
    },
    stages: {}, ok: true, failStage: null, error: null,
    memBefore: backendStat(pid)
  }

  // 1) 算法生成（严格校验后前端原始参数可能越界：默认如实记录 422；
  //    传 --clamp-generate 时再用夹紧参数重试，保证「生成→导出」链路仍可验证）
  const groups = toGroups(params)
  let gen = await req('POST', '/api/v1/car/generate', { car_type: type, params })
  let genData = null
  try { genData = JSON.parse(gen.data) } catch { genData = null }
  rec.stages.generateExact = {
    ok: gen.ok, ms: gen.ms, status: gen.status,
    detail: !gen.ok ? String(gen.data || gen.error).slice(0, 400) : null
  }
  if (!gen.ok && CLAMP_GENERATE) {
    gen = await req('POST', '/api/v1/car/generate', {
      car_type: type, params: flatOfGroups(clampGroups(groups))
    })
    genData = null
    try { genData = JSON.parse(gen.data) } catch { genData = null }
    rec.note = '前端原始参数越界，生成阶段改用夹紧参数（原值失败已记录）'
  }
  rec.stages.generate = {
    ok: gen.ok && !!genData?.components?.length,
    ms: gen.ms, status: gen.status, components: genData?.components?.length ?? 0,
    surfaces: genData?.total_surfaces ?? 0,
    quality: genData?.nurbs_quality || null,
    bbox: genData ? bboxOfComponents(genData.components) : null
  }
  if (!rec.stages.generate.ok) {
    rec.ok = false; rec.failStage = 'algorithm/generate'
    rec.error = gen.error || (genData ? 'empty components' : (gen.data || '').toString().slice(0, 300))
    results.push(rec); continue
  }
  const g = rec.stages.generate
  rec.fidelity = {
    lengthErrPct: +(Math.abs(g.bbox.lengthMm - params.overall_length) / params.overall_length * 100).toFixed(2),
    widthErrPct: +(Math.abs(g.bbox.widthMm - params.overall_width) / params.overall_width * 100).toFixed(2),
    heightErrPct: +(Math.abs(g.bbox.heightMm - params.overall_height) / params.overall_height * 100).toFixed(2)
  }
  fs.writeFileSync(path.join(dir, 'generate.response.json'), JSON.stringify(genData, null, 2), 'utf8')

  // 2) 导入改参导出会话（先用前端原始值，预期被区间校验拒绝；再夹紧重试保证导出链路可验证）
  const imp = await req('POST', '/api/v1/import-export/import', { name: `${type}-pilot-${i + 1}`, params: groups })
  let impData = null
  try { impData = JSON.parse(imp.data) } catch { impData = null }
  rec.stages.importExact = {
    ok: imp.ok, ms: imp.ms, status: imp.status,
    detail: !imp.ok ? String(imp.data || imp.error).slice(0, 500) : null
  }
  let sid = imp.ok ? impData.session_id : null
  if (!sid) {
    const imp2 = await req('POST', '/api/v1/import-export/import', { name: `${type}-pilot-${i + 1}-clamped`, params: clampGroups(groups) })
    let d2 = null
    try { d2 = JSON.parse(imp2.data) } catch { d2 = null }
    rec.stages.importClamped = { ok: imp2.ok, ms: imp2.ms, status: imp2.status }
    if (!imp2.ok) {
      rec.ok = false; rec.failStage = 'backend/import'
      rec.error = String(imp2.data || imp2.error).slice(0, 500)
      results.push(rec); continue
    }
    sid = d2.session_id
    rec.note = '前端原始参数越界，导入改参阶段改用夹紧参数（原值失败已记录）'
  }

  // 3) 预览点云（前端 3D 网格的真实数据源）
  const pv = await req('GET', `/api/v1/import-export/${sid}/preview`)
  let pvData = null
  try { pvData = JSON.parse(pv.data) } catch { pvData = null }
  rec.stages.preview = {
    ok: pv.ok && !!pvData?.components?.length, ms: pv.ms, status: pv.status,
    components: pvData?.components?.length ?? 0,
    bbox: pvData ? bboxOfComponents(pvData.components) : null
  }
  if (!rec.stages.preview.ok) {
    rec.ok = false; rec.failStage = 'backend/preview'
    rec.error = String(pv.data || pv.error).slice(0, 500)
    results.push(rec); continue
  }
  fs.writeFileSync(path.join(dir, 'preview.response.json'), JSON.stringify(pvData, null, 2), 'utf8')

  // 4) 导出
  const formats = ['step', 'glb', 'stl', 'obj', 'json']
  const ex = await req('POST', `/api/v1/import-export/${sid}/export`, { formats, name: runId })
  let exData = null
  try { exData = JSON.parse(ex.data) } catch { exData = null }
  rec.stages.export = { ok: ex.ok, ms: ex.ms, status: ex.status, files: exData?.files || [] }
  if (!ex.ok) {
    rec.ok = false; rec.failStage = 'export'
    rec.error = String(ex.data || ex.error).slice(0, 500)
    results.push(rec); continue
  }

  // 5) 下载并校验产物
  const check = []
  for (const f of exData.files) {
    const dl = await req('GET', `/api/v1/import-export/${sid}/download/${encodeURIComponent(f.filename)}`)
    if (!dl.ok) { check.push({ format: f.format, ok: false, reason: `download HTTP ${dl.status}` }); continue }
    const buf = Buffer.isBuffer(dl.data) ? dl.data : Buffer.from(dl.data)
    const outPath = path.join(dir, f.filename)
    fs.writeFileSync(outPath, buf)
    check.push({
      format: f.format, filename: f.filename, bytes: buf.length,
      serverBytes: f.size, ok: buf.length > 0 && magic[f.format]?.(buf) === true,
      magic: magic[f.format]?.(buf) === true
    })
  }
  rec.stages.validate = { ok: check.every((c) => c.ok), files: check }
  if (!rec.stages.validate.ok) {
    rec.ok = false; rec.failStage = 'export/validate'
    rec.error = check.filter((c) => !c.ok).map((c) => `${c.format}:${c.reason || 'bad-magic'}`).join('; ')
  }

  rec.memAfter = backendStat(pid)
  results.push(rec)
  console.log(`[pilot-api ${i + 1}/${TOTAL}] ${runId} gen=${gen.ms}ms export=${ex.ms}ms stages=${
    Object.entries(rec.stages).map(([k, v]) => `${k}:${v.ok ? 'ok' : 'FAIL'}`).join(',')}`)
}

const statEnd = backendStat(pid)
const okRuns = results.filter((r) => r.ok)
const p95 = (arr) => {
  const s = [...arr].sort((a, b) => a - b)
  return s.length ? s[Math.min(s.length - 1, Math.ceil(s.length * 0.95) - 1)] : null
}
const summary = {
  at: new Date().toISOString(),
  backendPid: pid,
  runs: results.length,
  success: okRuns.length,
  successRate: +(okRuns.length / results.length * 100).toFixed(1),
  p95GenerateMs: p95(results.map((r) => r.stages.generate?.ms).filter(Boolean)),
  p95ExportMs: p95(results.map((r) => r.stages.export?.ms).filter(Boolean)),
  p95TotalMs: p95(results.map((r) =>
    Object.values(r.stages).reduce((a, s) => a + (s.ms || 0), 0)).filter(Boolean)),
  productOpenRate: +(results.filter((r) => r.stages.validate?.ok).length / results.length * 100).toFixed(1),
  paramFidelity: results.filter((r) => r.fidelity).map((r) => ({ runId: r.runId, ...r.fidelity })),
  exactImportRejected: results.filter((r) => r.stages.importExact && !r.stages.importExact.ok)
    .map((r) => ({ runId: r.runId, status: r.stages.importExact.status, detail: r.stages.importExact.detail })),
  memStart: statStart,
  memEnd: statEnd,
  results
}
fs.writeFileSync(path.join(OUT_DIR, 'pilot-api-summary.json'), JSON.stringify(summary, null, 2), 'utf8')

console.log('\n=== pilot-api summary ===')
console.log(`success ${summary.success}/${summary.runs} (${summary.successRate}%)`)
console.log(`P95 generate ${summary.p95GenerateMs}ms | export ${summary.p95ExportMs}ms | total ${summary.p95TotalMs}ms`)
console.log(`products openable ${summary.productOpenRate}%`)
console.log(`backend WS ${statStart?.wsMB}MB -> ${statEnd?.wsMB}MB | handles ${statStart?.handles} -> ${statEnd?.handles}`)
console.log(`exact-import rejected ${summary.exactImportRejected.length}/${results.length}`)
for (const r of summary.paramFidelity) console.log(`fidelity ${r.runId}: L±${r.lengthErrPct}% W±${r.widthErrPct}% H±${r.heightErrPct}%`)
process.exit(0)
