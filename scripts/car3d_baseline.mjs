// Car3D 视觉基线采集（P0）
// 用法：node scripts/car3d_baseline.mjs [--out docs/preview/car3d-baseline] [--keep-server]
// 依赖：puppeteer-core + 本机 Microsoft Edge；Vite dev server（脚本可自动拉起 5173）。
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const EDGE_CANDIDATES = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe'
]
const EDGE = EDGE_CANDIDATES.find((p) => existsSync(p))
const VITE_BIN = path.join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js')

const args = process.argv.slice(2)
const argOf = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback
}
const OUT_DIR = path.resolve(ROOT, argOf('--out', 'docs/preview/car3d-baseline'))
const KEEP_SERVER = args.includes('--keep-server')
const PORT = Number(process.env.VITE_PORT || 5173)
const BASE = `http://127.0.0.1:${PORT}/scripts/car3d-baseline/harness.html`

// 固定机位：正 / 侧 / 45° / 内饰（Car3D 无内饰预设，用 perspective + 开门作为座舱观察位）
const VIEWS = [
  { id: 'front', view: 'front', note: '正视（正交）' },
  { id: 'left', view: 'left', note: '左侧视（正交，驾驶员侧）' },
  { id: 'iso45', view: 'isometric', note: '45° 等轴（透视）' },
  { id: 'interior', view: 'perspective', note: '内饰观察位（透视 + 开门）' }
]
const DOOR_STATES = [0, 1]

if (!EDGE) {
  console.error('未找到 Microsoft Edge（Chromium），无法采集基线。')
  process.exit(2)
}
mkdirSync(OUT_DIR, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function ensureServer() {
  try {
    const res = await fetch(BASE, { method: 'GET' })
    if (res.ok) return null
  } catch {
    /* not running */
  }
  console.log('[baseline] 启动 Vite dev server ...')
  const child = spawn(process.execPath, [VITE_BIN, '--port', String(PORT), '--strictPort'], {
    cwd: ROOT, stdio: 'ignore'
  })
  for (let i = 0; i < 120; i++) {
    await sleep(500)
    try {
      const res = await fetch(BASE)
      if (res.ok) return child
    } catch {
      /* retry */
    }
  }
  child.kill()
  throw new Error('Vite dev server 60s 内未就绪')
}

const started = await ensureServer()
const browser = await puppeteer.launch({
  executablePath: EDGE,
  headless: 'new',
  args: [
    '--no-sandbox',
    '--hide-scrollbars',
    '--force-device-scale-factor=1',
    '--enable-unsafe-swiftshader',
    '--use-angle=swiftshader'
  ],
  defaultViewport: { width: 1280, height: 800, deviceScaleFactor: 1 }
})

const shots = []
const metrics = []
try {
  for (const v of VIEWS) {
    for (const door of DOOR_STATES) {
      shots.push({
        name: `${v.id}-door${door}`,
        view: v.view,
        door,
        note: `${v.note} · ${door ? '开门 70°' : '关门'}`
      })
    }
  }
  for (const shot of shots) {
    const page = await browser.newPage()
    await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: 1 })
    const url = `${BASE}?view=${shot.view}&door=${shot.door}&w=1280&h=800&type=sedan`
    await page.goto(url, { waitUntil: 'load', timeout: 30000 })
    await page.waitForFunction(
      () => window.__CAR3D_SCENES__ && window.__CAR3D_SCENES__.length > 0,
      { timeout: 20000 }
    )
    await page.waitForFunction(
      () => document.getElementById('baseline-metrics')?.textContent !== 'pending',
      { timeout: 20000 }
    )
    const data = JSON.parse(await page.$eval('#baseline-metrics', (el) => el.textContent))
    await page.screenshot({ path: path.join(OUT_DIR, `${shot.name}.png`) })
    metrics.push({ name: shot.name, note: shot.note, ...data })
    console.log(`[baseline] ${shot.name} meshes=${data.meshes} tris=${data.triangles} hingeY=${data.hingeMaxY}`)
    await page.close()
  }
  const manifest = {
    version: 'P0-2026-11-03',
    viewport: { width: 1280, height: 800 },
    renderer: 'Microsoft Edge headless + puppeteer-core（SwiftShader ANGLE）',
    car: { type: 'sedan', color: '#4ade80' },
    camera: {
      front: '正交，dist=5（半视口高 3）',
      left: '正交，dist=5（半视口高 3）',
      iso45: '透视，rotation=(π/4, π/4)，dist=10',
      interior: '透视 + 开门，默认 rotation=(0.4, 0.8)，dist=8'
    },
    doorAngle: '默认 70°（carParams.door_open_angle），由开门按钮驱动缓动',
    shots: metrics
  }
  writeFileSync(path.join(OUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8')
  console.log(`[baseline] 完成：${metrics.length} 张截图 + manifest.json -> ${OUT_DIR}`)
} finally {
  await browser.close()
  if (started && !KEEP_SERVER) {
    started.kill()
    await sleep(300)
  }
}
