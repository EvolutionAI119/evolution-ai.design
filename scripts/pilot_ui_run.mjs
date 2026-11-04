// 中试（pilot）· 前端真实链路批量跑
// 真实 Vite 前端（5173）→ /api/v1 代理 → 真实后端（8000）→ 算法生成，
// 每次记录：生成请求状态与耗时、3D 场景 mesh/三角数、2D SVG 产物、截图、
// JS 堆内存、页面错误/失败请求，并把 2D 图纸独立落成可直接打开的 HTML。
// 每次运行使用全新页面（避免页面内多实例渲染在软件 WebGL 下累积导致超时），
// 页面关闭前后对比浏览器进程树内存/句柄，用于观察是否泄漏。
//
// 用法：node scripts/pilot_ui_run.mjs [--runs 10] [--out pilot-artifacts/ui]
import fs from 'node:fs'
import path from 'node:path'
import { existsSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const EDGE_CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe'
]
const EDGE = EDGE_CANDIDATES.find((p) => existsSync(p))
const args = process.argv.slice(2)
const argOf = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const OUT_DIR = path.resolve(ROOT, argOf('--out', 'pilot-artifacts/ui'))
const TOTAL = Number(argOf('--runs', 10))
const PORT = Number(process.env.VITE_PORT || 5173)
const APP_URL = `http://127.0.0.1:${PORT}/#/designer`
fs.mkdirSync(OUT_DIR, { recursive: true })

if (!EDGE) {
  console.error('未找到 Microsoft Edge（Chromium）')
  process.exit(2)
}

// 车型宫格顺序与 src/config/carPresets.js 一致：sedan, suv, coupe, sport, mpv, pickup
const TYPE_INDEX = { sedan: 0, suv: 1, coupe: 2, sport: 3, mpv: 4, pickup: 5 }
const PLAN = [...Array(4).fill('sedan'), ...Array(3).fill('suv'), ...Array(3).fill('pickup')]

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function countPoints(node) {
  if (Array.isArray(node)) {
    if (node.length === 3 && node.every((n) => typeof n === 'number')) return 1
    return node.reduce((a, n) => a + countPoints(n), 0)
  }
  return 0
}

// 浏览器进程树（主进程 + 渲染/GPU 子进程）内存与句柄
function processTreeStat(rootPid) {
  if (!rootPid) return null
  try {
    const ps = `$root=${rootPid}; $all=Get-CimInstance Win32_Process; ` +
      `$ids=@($root); do { $new=@($all | Where-Object { $ids -contains $_.ParentProcessId -and $ids -notcontains $_.ProcessId } | ForEach-Object { $_.ProcessId }); $ids += $new } while($new.Count -gt 0); ` +
      `$p=Get-Process -Id $ids -ErrorAction SilentlyContinue; ` +
      `Write-Output ('{0} {1} {2}' -f [math]::Round(($p|Measure-Object WorkingSet64 -Sum).Sum/1MB,1), ($p|Measure-Object HandleCount -Sum).Sum, $p.Count)`
    const out = execFileSync('powershell', ['-NoProfile', '-Command', ps], { encoding: 'utf8' })
    const [wsMB, handles, procs] = out.trim().split(/\s+/).map(Number)
    return { wsMB, handles, procs }
  } catch { return null }
}

const GL_ARGS = process.env.PILOT_GL === 'hw'
  ? ['--use-gl=angle', '--use-angle=d3d11']
  : ['--enable-unsafe-swiftshader', '--use-angle=swiftshader']
const launchBrowser = () => puppeteer.launch({
  executablePath: EDGE,
  headless: 'new',
  args: [
    '--no-sandbox',
    '--hide-scrollbars',
    '--force-device-scale-factor=1',
    ...GL_ARGS,
    '--js-flags=--expose-gc'
  ],
  defaultViewport: { width: 1600, height: 1000, deviceScaleFactor: 1 }
})

const results = []
for (let i = 0; i < TOTAL; i++) {
  const type = PLAN[i % PLAN.length]
  const runId = `run${String(i + 1).padStart(2, '0')}-${type}`
  const dir = path.join(OUT_DIR, runId)
  fs.mkdirSync(dir, { recursive: true })
  const pageErrors = []
  const consoleErrors = []
  const failedReqs = []
  let lastGenerate = null
  let generateT0 = 0
  const rec = { run: i + 1, runId, carType: type, ok: false, failStage: null, error: null }
  const t0 = Date.now()
  const browser = await launchBrowser()
  const browserPid = browser.process()?.pid
  const browserStatStart = processTreeStat(browserPid)
  const page = await browser.newPage()
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 1 })
  page.on('pageerror', (e) => pageErrors.push(String(e)))
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 400)) })
  page.on('requestfailed', (r) => failedReqs.push(`${r.method()} ${r.url()} :: ${r.failure()?.errorText}`))
  page.on('response', async (res) => {
    const url = res.url()
    if (!url.includes('/api/v1/car/generate') || res.request().method() !== 'POST') return
    try {
      const body = await res.json()
      lastGenerate = {
        status: res.status(), components: body?.components?.length ?? 0,
        surfaces: body?.total_surfaces ?? 0,
        g2: body?.nurbs_quality?.g2_continuous,
        measured: body?.nurbs_quality?.measured,
        nFlat: body?.nurbs_quality?.n_flat_surfaces,
        cp: body?.nurbs_quality?.control_points_total,
        points: body?.components?.reduce((a, c) => a + (c.points ? countPoints(c.points) : 0), 0),
        timeMs: generateT0 ? Date.now() - generateT0 : null
      }
    } catch { lastGenerate = { status: res.status(), parseError: true } }
  })

  try {
    await page.goto(APP_URL, { waitUntil: 'load', timeout: 60000 })
    await page.waitForSelector('.generate-btn', { timeout: 40000 })
    await page.waitForFunction(() => (window.__CAR3D_SCENES__ || []).length >= 1, { timeout: 40000 })
    // 切换车型（与用户点击同一路径；sedan 也点一次以统一流程）
    await page.evaluate((idx) => {
      const cards = document.querySelectorAll('.car-type-card')
      if (!cards[idx]) throw new Error(`car-type-card[${idx}] missing`)
      cards[idx].click()
    }, TYPE_INDEX[type])
    await sleep(400)

    generateT0 = Date.now()
    const waitResp = page.waitForResponse(
      (res) => res.url().includes('/api/v1/car/generate') && res.request().method() === 'POST',
      { timeout: 120000 }
    )
    await page.click('.generate-btn')
    const resp = await waitResp
    rec.httpStatus = resp.status()
    if (!resp.ok()) {
      rec.failStage = 'backend/api'
      rec.error = `HTTP ${resp.status()}`
    } else {
      // 等 3D 场景把 NURBS 网格挂上（两个视口都走 NURBS 路径）
      await page.waitForFunction(() => {
        const list = (window.__CAR3D_SCENES__ || []).filter((s) => s.userData?.__car3d__?.nurbs)
        return list.length > 0 && list.every((sc) => {
          let n = 0
          sc.traverse((o) => { if (o.isMesh) n++ })
          return n > 20
        })
      }, { timeout: 60000 })
      await sleep(600)
      const ui = await page.evaluate(() => {
        const scenes = window.__CAR3D_SCENES__ || []
        const sceneStats = scenes.map((sc) => {
          let meshes = 0, tris = 0
          sc.traverse((o) => {
            if (!o.isMesh) return
            meshes++
            const g = o.geometry
            if (!g) return
            if (g.index && g.index.count) tris += g.index.count / 3
            else if (g.attributes?.position) tris += g.attributes.position.count / 3
          })
          return {
            wireframe: !!sc.userData?.__car3d__?.wireframe,
            nurbs: !!sc.userData?.__car3d__?.nurbs,
            meshes, triangles: Math.round(tris),
            geometries: sc.children.length
          }
        })
        const svgs = [...document.querySelectorAll('svg.car-2d-svg')].map((el) => ({
          outer: el.outerHTML,
          paths: el.querySelectorAll('path').length,
          texts: el.querySelectorAll('text').length,
          viewBox: el.getAttribute('viewBox'),
          bytes: new Blob([el.outerHTML]).size
        }))
        const heap = performance.memory
          ? { usedMB: +(performance.memory.usedJSHeapSize / 1048576).toFixed(1),
              totalMB: +(performance.memory.totalJSHeapSize / 1048576).toFixed(1) }
          : null
        return { sceneStats, svgs, heap, title: document.title }
      })
      rec.sceneStats = ui.sceneStats
      rec.heap = ui.heap
      rec.scenesRegistered = ui.sceneStats.length
      rec.svg = ui.svgs.map(({ outer, ...rest }) => rest)
      rec.generate = lastGenerate

      // 2D 图纸 HTML（独立可打开）
      const big = ui.svgs.slice().sort((a, b) => b.bytes - a.bytes)[0]
      if (big) {
        const html = `<!doctype html><html lang="zh"><head><meta charset="utf-8">` +
          `<title>EVOLUTION-AI · ${runId} 2D 图纸</title>` +
          `<style>body{margin:0;background:#0b1020;color:#cfd8e3;font:14px/1.5 system-ui}` +
          `main{padding:16px}svg{width:100%;height:auto;background:#0b1020;border:1px solid #223}` +
          `</style></head><body><main><h3>${type} · ${runId} · 2D 图纸（Car2D 实渲 SVG）</h3>` +
          `<p>paths=${big.paths} texts=${big.texts} viewBox=${big.viewBox}</p>${big.outer}</main></body></html>`
        fs.writeFileSync(path.join(dir, '2d-drawing.html'), html, 'utf8')
        rec.svgIndependent = true
      }
      await page.screenshot({ path: path.join(dir, 'designer.png'), fullPage: false })

      // 独立打开 2D HTML 验证（file:// 渲染，确认产物不依赖当前页状态）
      if (rec.svgIndependent) {
        const p2 = await browser.newPage()
        const fileUrl = 'file:///' + path.join(dir, '2d-drawing.html').replace(/\\/g, '/')
        let openOk = false
        try {
          await p2.goto(fileUrl, { waitUntil: 'load', timeout: 20000 })
          openOk = await p2.evaluate(() => {
            const svg = document.querySelector('svg')
            return !!svg && svg.querySelectorAll('path').length > 0
          })
        } catch (e) { rec.svgOpenError = String(e) }
        rec.svgOpenable = openOk
        await p2.close()
      }

      rec.ok = !!(rec.generate?.components > 0) && ui.sceneStats.some((s) => s.nurbs && s.meshes > 20) &&
        rec.svgOpenable === true && !consoleErrors.some((m) => /Global error|ReferenceError/.test(m))
      if (!rec.ok) {
        rec.failStage = !rec.generate?.components ? 'backend/empty'
          : (!rec.svgOpenable ? 'frontend/2d' : 'frontend/3d')
        if (consoleErrors.length) rec.error = consoleErrors.slice(0, 3).join(' | ')
      }
      await page.evaluate(() => { if (window.gc) window.gc() })
      await sleep(200)
      rec.heapAfterGc = await page.evaluate(() => performance.memory
        ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(1) : null)
    }
  } catch (e) {
    rec.failStage = rec.failStage || 'frontend/render'
    rec.error = String(e.message || e)
  }
  rec.elapsedMs = Date.now() - t0
  rec.newPageErrors = pageErrors.slice()
  rec.newConsoleErrors = consoleErrors.slice()
  rec.newFailedRequests = failedReqs.slice()
  results.push(rec)
  const browserStatEnd = processTreeStat(browserPid)
  rec.browserStat = { start: browserStatStart, end: browserStatEnd }
  console.log(`[pilot-ui ${i + 1}/${TOTAL}] ${runId} ok=${rec.ok} ${rec.elapsedMs}ms ` +
    `gen=${rec.generate?.timeMs ?? '?'}ms comp=${rec.generate?.components ?? '?'} ` +
    `scenes=${rec.scenesRegistered ?? '?'} meshes=${rec.sceneStats?.[0]?.meshes ?? '?'} ` +
    `svgPaths=${rec.svg?.[0]?.paths ?? '?'} heap=${rec.heapAfterGc ?? rec.heap?.usedMB ?? '?'}MB` +
    ` browserWS=${rec.browserStat.start?.wsMB ?? '?'}->${rec.browserStat.end?.wsMB ?? '?'}MB` +
    ` handles=${rec.browserStat.start?.handles ?? '?'}->${rec.browserStat.end?.handles ?? '?'}` +
    (rec.error ? ` ERR=${rec.error}` : ''))
  await browser.close().catch(() => {})
  fs.writeFileSync(path.join(dir, 'metrics.json'), JSON.stringify(rec, null, 2), 'utf8')
}

const okRuns = results.filter((r) => r.ok)
const p95 = (arr) => {
  const s = [...arr].sort((a, b) => a - b)
  return s.length ? s[Math.min(s.length - 1, Math.ceil(s.length * 0.95) - 1)] : null
}
const heaps = results.map((r) => r.heapAfterGc).filter((v) => typeof v === 'number')
const summary = {
  at: new Date().toISOString(),
  appUrl: APP_URL,
  runs: results.length,
  success: okRuns.length,
  successRate: +(okRuns.length / results.length * 100).toFixed(1),
  p95UiElapsedMs: p95(results.map((r) => r.elapsedMs)),
  p95GenerateRequestMs: p95(results.map((r) => r.generate?.timeMs).filter(Boolean)),
  svgOpenRate: +(results.filter((r) => r.svgOpenable).length / results.length * 100).toFixed(1),
  sceneRegistryStable: results.every((r) => r.scenesRegistered === 2),
  meshSeries: results.map((r) => r.sceneStats?.[0]?.meshes ?? null),
  triSeries: results.map((r) => r.sceneStats?.[0]?.triangles ?? null),
  heapSeriesMB: heaps,
  heapStartMB: heaps[0] ?? null,
  heapEndMB: heaps[heaps.length - 1] ?? null,
  browserStatSeries: results.map((r) => r.browserStat),
  pageErrors: results.reduce((a, r) => a + r.newPageErrors.length, 0),
  consoleErrors: results.reduce((a, r) => a + r.newConsoleErrors.length, 0),
  failedRequests: results.reduce((a, r) => a + r.newFailedRequests.length, 0),
  results
}
fs.writeFileSync(path.join(OUT_DIR, 'pilot-ui-summary.json'), JSON.stringify(summary, null, 2), 'utf8')

console.log('\n=== pilot-ui summary ===')
console.log(`success ${summary.success}/${summary.runs} (${summary.successRate}%)`)
console.log(`P95 UI ${summary.p95UiElapsedMs}ms | generate ${summary.p95GenerateRequestMs}ms`)
console.log(`2D SVG openable ${summary.svgOpenRate}% | scene registry stable=${summary.sceneRegistryStable}`)
console.log(`meshes ${summary.meshSeries.join(',')}`)
console.log(`tris ${summary.triSeries.join(',')}`)
console.log(`heap ${summary.heapStartMB}MB -> ${summary.heapEndMB}MB | series ${summary.heapSeriesMB.join(',')}`)
console.log(`browser per-run WS ${summary.browserStatSeries.map((s) => `${s?.start?.wsMB ?? '?'}->${s?.end?.wsMB ?? '?'}`).join(',')}`)
console.log(`browser per-run handles ${summary.browserStatSeries.map((s) => `${s?.start?.handles ?? '?'}->${s?.end?.handles ?? '?'}`).join(',')}`)
console.log(`pageErrors ${summary.pageErrors} | consoleErrors ${summary.consoleErrors} | failedRequests ${summary.failedRequests}`)
process.exit(0)
