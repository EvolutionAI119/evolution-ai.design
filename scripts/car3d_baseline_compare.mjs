// Car3D 基线比对：指标容差 + 像素差（pixelmatch）
// 用法：node scripts/car3d_baseline_compare.mjs [--base docs/preview/car3d-baseline] [--cur <新采集目录>]
//       [--threshold 0.01] [--metric 0.005]
// 退出码：0 全部通过；1 有差异；2 缺文件/参数错误。
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const args = process.argv.slice(2)
const argOf = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const BASE_DIR = path.resolve(ROOT, argOf('--base', 'docs/preview/car3d-baseline'))
const CUR_DIR = path.resolve(ROOT, argOf('--cur', BASE_DIR))
const PIXEL_THRESHOLD = Number(argOf('--threshold', 0.01))
const METRIC_THRESHOLD = Number(argOf('--metric', 0.005))

if (!existsSync(BASE_DIR)) {
  console.error(`基线目录不存在：${BASE_DIR}`)
  process.exit(2)
}

const baseManifest = JSON.parse(readFileSync(path.join(BASE_DIR, 'manifest.json'), 'utf8'))
const curManifest = CUR_DIR === BASE_DIR
  ? baseManifest
  : JSON.parse(readFileSync(path.join(CUR_DIR, 'manifest.json'), 'utf8'))

const rel = (a, b) => (Math.abs(a - b) / Math.max(Math.abs(a), 1e-9))
const results = []

for (const b of baseManifest.shots) {
  const c = curManifest.shots.find((s) => s.name === b.name)
  if (!c) { results.push({ shot: b.name, ok: false, reason: '缺少当前采集同名分镜' }); continue }
  const metricDiff = {
    meshes: rel(c.meshes, b.meshes),
    triangles: rel(c.triangles, b.triangles)
  }
  let bboxDiff = 0
  if (b.bbox && c.bbox) {
    for (let i = 0; i < 3; i++) {
      bboxDiff = Math.max(bboxDiff,
        rel(c.bbox.min[i], b.bbox.min[i]), rel(c.bbox.max[i], b.bbox.max[i]))
    }
  }
  const metricOk = metricDiff.meshes <= METRIC_THRESHOLD &&
    metricDiff.triangles <= METRIC_THRESHOLD && bboxDiff <= METRIC_THRESHOLD * 10

  const basePng = path.join(BASE_DIR, `${b.name}.png`)
  const curPng = path.join(CUR_DIR, `${b.name}.png`)
  let pixelOk = true
  let diffRatio = 0
  if (existsSync(basePng) && existsSync(curPng)) {
    const a = PNG.sync.read(readFileSync(basePng))
    const bb = PNG.sync.read(readFileSync(curPng))
    if (a.width !== bb.width || a.height !== bb.height) {
      pixelOk = false
      diffRatio = 1
    } else {
      const diff = new PNG({ width: a.width, height: a.height })
      const n = pixelmatch(a.data, bb.data, diff.data, a.width, a.height, { threshold: 0.1 })
      diffRatio = n / (a.width * a.height)
      pixelOk = diffRatio <= PIXEL_THRESHOLD
      if (!pixelOk) writeFileSync(path.join(CUR_DIR, `${b.name}.diff.png`), PNG.sync.write(diff))
    }
  } else {
    pixelOk = false
  }

  results.push({
    shot: b.name,
    ok: metricOk && pixelOk,
    metricDiff, bboxDiff, diffRatio, metricOk, pixelOk
  })
}

const failed = results.filter((r) => !r.ok)
for (const r of results) {
  const tag = r.ok ? 'PASS' : 'FAIL'
  console.log(`[compare] ${tag} ${r.shot}` +
    (r.reason ? ` (${r.reason})` :
      ` tris±${(r.metricDiff.triangles * 100).toFixed(2)}% bbox±${(r.bboxDiff * 100).toFixed(2)}% pixel ${(r.diffRatio * 100).toFixed(2)}%`))
}
writeFileSync(path.join(CUR_DIR, 'compare-report.json'), JSON.stringify({ results, thresholds: { pixel: PIXEL_THRESHOLD, metric: METRIC_THRESHOLD } }, null, 2), 'utf8')
console.log(`[compare] ${results.length - failed.length}/${results.length} 通过`)
process.exit(failed.length ? 1 : 0)
