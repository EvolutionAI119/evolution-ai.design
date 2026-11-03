// Car3D P0 视觉基线采集页：固定机位 + 固定分辨率 + 可选开门，输出可解析的场景指标。
// 仅用于 docs/preview/car3d-baseline 的回归采集，不参与生产构建。
import { createApp, h } from 'vue'
import * as THREE from 'three'
import Car3D from '../../src/components/Car3D.vue'
import i18n from '../../src/i18n.js'
import { carTypeParams } from '../../src/config/carPresets.js'

const q = new URLSearchParams(location.search)
const view = q.get('view') || 'perspective'
const door = q.get('door') === '1'
const type = q.get('type') || 'sedan'
const width = Number(q.get('w') || 1280)
const height = Number(q.get('h') || 800)

const root = document.getElementById('app')
root.style.width = `${width}px`
root.style.height = `${height}px`

const app = createApp({
  render: () => h(Car3D, {
    carParams: { ...carTypeParams[type] },
    carType: type,
    carColor: '#4ade80',
    viewAngle: view
  })
})
app.use(i18n)
app.mount(root)

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/** 选场景中网格最多的 Group 作为车身主体，计算 bbox */
const pickBodyGroup = (scene) => {
  let best = null
  let bestCount = -1
  for (const child of scene.children) {
    if (!child.isGroup) continue
    let count = 0
    child.traverse((o) => { if (o.isMesh) count++ })
    if (count > bestCount) { best = child; bestCount = count }
  }
  return best
}

const collectMetrics = () => {
  const scene = window.__CAR3D_SCENES__?.[0]
  if (!scene) return { error: 'scene-not-ready' }
  let meshes = 0
  let triangles = 0
  scene.traverse((o) => {
    if (!o.isMesh || !o.geometry) return
    meshes++
    const g = o.geometry
    const count = g.index ? g.index.count : g.attributes.position.count
    triangles += Math.round(count / 3)
  })
  const body = pickBodyGroup(scene)
  const box = body ? new THREE.Box3().setFromObject(body) : null
  // 门开合代理指标：具名铰链的 rotation.y 峰值（0=关门；≈1.22 rad=70° 开门）
  let hingeMaxY = 0
  scene.traverse((o) => {
    if (o.name?.startsWith('door-hinge')) hingeMaxY = Math.max(hingeMaxY, Math.abs(o.rotation.y))
  })
  const doorBtnActive = document.querySelector('.door-btn')?.classList.contains('active') ?? null
  const doorNames = []
  scene.traverse((o) => { if (o.name?.includes('door')) doorNames.push(o.name) })
  const round = (v) => Math.round(v * 1000) / 1000
  return {
    view,
    door,
    type,
    width,
    height,
    meshes,
    triangles,
    hingeMaxY: round(hingeMaxY),
    doorBtnActive,
    bbox: box
      ? {
          min: [round(box.min.x), round(box.min.y), round(box.min.z)],
          max: [round(box.max.x), round(box.max.y), round(box.max.z)]
        }
      : null
  }
}

const run = async () => {
  // 等场景注册（轮询上限 6s）
  for (let i = 0; i < 60; i++) {
    if (window.__CAR3D_SCENES__?.length) break
    await wait(100)
  }
  // 先等车身与门铰链构建完成，再切换固定机位（按钮与组件预设同源）
  await wait(600)
  // 关闭自动旋转（第 3 个控制按钮），否则 perspective 分镜角度随帧漂移
  document.querySelectorAll('.control-buttons .ctrl-btn')[2]
    ?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
  await wait(200)
  // 瞬时定位到预设机位（与帧率解耦），再留一帧让渲染落地
  window.__CAR3D_SCENES__?.[0]?.userData?.__car3d__?.setViewInstant?.(view)
  await wait(250)
  if (door) {
    // 瞬时摆到 70° 稳态：不依赖 rAF 计时，保证分镜可重复
    window.__CAR3D_SCENES__?.[0]?.userData?.__car3d__?.setDoor?.(true)
  }
  await wait(400)
  const metrics = collectMetrics()
  document.getElementById('baseline-metrics').textContent = JSON.stringify(metrics)
  document.title = 'BASELINE_READY'
}

run()
