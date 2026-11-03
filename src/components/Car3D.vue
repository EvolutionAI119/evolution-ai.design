<template>
  <div ref="containerRef" class="car-3d-container">
    <div class="view-controls">
      <button
        v-for="view in viewAngles"
        :key="view.key"
        type="button"
        class="view-btn"
        :class="{ active: currentView === view.key }"
        @click="setViewAngle(view.key)"
        :title="view.label"
        :aria-label="view.label"
      >
        {{ view.icon }}
      </button>
    </div>
    <div class="control-buttons">
      <div class="ctrl-btn" @click="resetView" :title="t('designer.viewerReset')" :aria-label="t('designer.viewerReset')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleWireframe" :class="{ active: wireframeMode }" :title="t('designer.viewerWireframe')" :aria-label="t('designer.viewerWireframe')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18M9 3v18M3 15h18M15 3v18"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleAutoRotate" :class="{ active: autoRotate }" :title="t('designer.viewerAutoRotate')" :aria-label="t('designer.viewerAutoRotate')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleFullscreen" :class="{ active: isFullscreen }" :title="t('designer.viewerFullscreen')" :aria-label="t('designer.viewerFullscreen')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
        </svg>
      </div>
      <div
        class="ctrl-btn door-btn"
        :class="{ active: doorOpen }"
        :title="t('designer.doorToggle')"
        :aria-label="t('designer.doorToggle')"
        @click="toggleDoor"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="4" width="13" height="16" rx="1"/>
          <path d="M16 8l4-2v12l-4-2"/>
          <circle cx="13" cy="12" r="0.8" fill="currentColor"/>
        </svg>
      </div>
      <div
        v-if="flightAvailable"
        class="ctrl-btn vtol-btn"
        :class="{ active: flightEngaged }"
        :title="flightEngaged ? t('designer.vtolDisengage') : t('designer.vtolEngage')"
        :aria-label="flightEngaged ? t('designer.vtolDisengage') : t('designer.vtolEngage')"
        @click="toggleFlight"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20V7"/>
          <path d="M8 11l4-4 4 4"/>
          <path d="M4 20h16"/>
        </svg>
      </div>
      <template v-if="flightEngaged">
        <div
          class="ctrl-btn turn-btn"
          :class="{ busy: yawTurning }"
          :title="t('designer.turnLeft90')"
          :aria-label="t('designer.turnLeft90')"
          @click="startTurn(-90)"
        >↺</div>
        <div
          class="ctrl-btn turn-btn"
          :class="{ busy: yawTurning }"
          :title="t('designer.turnRight90')"
          :aria-label="t('designer.turnRight90')"
          @click="startTurn(90)"
        >↻</div>
        <div
          class="ctrl-btn turn-btn turn-full"
          :class="{ busy: yawTurning }"
          :title="t('designer.fullTurn360')"
          :aria-label="t('designer.fullTurn360')"
          @click="startTurn(360)"
        >360°</div>
      </template>
    </div>
    <div class="status-bar">
      <span class="view-label">{{ currentViewLabel }}</span>
      <span class="status-item">DAYLIGHT</span>
      <span class="status-item">PERSPECTIVE</span>
      <span v-if="flightEngaged" class="status-item vtol-status">VTOL HOVER</span>
      <span
        v-if="flightEngaged && flightEnergy"
        class="status-item vtol-status energy-status"
      >{{ flightEnergy.kw }} kW · ×{{ flightEnergy.mult.toFixed(1) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as THREE from 'three'
import { createScene } from '../three/scene/createScene.js'
import { attachInteractions } from '../three/scene/interactions.js'
import { createFlightFx } from '../three/scene/flightFx.js'
import { deriveCarProfile, deriveWheelFitment, bodySideOutline, deriveDoorLayout, deriveLiftDevices, filletCorner, deriveNurbsFrame } from '../utils/carProfile.js'
import { deriveCabinGlass, dloZAt, pillarPlacement, buildDloFrame, deriveDloPaneRanges, deriveDloApertures, buildDoorAperturePolygon, shellHalfZAt, insideBodyMaterial, ROOF_FILLETS, BODY_BEVEL_SIZE, DLO_APERTURE_INSET } from '../utils/carGlass.js'
import { resolveFlightParams, quinticSmoothstep, hoverBobOffset,
  turnDurationSec, attitudeSample, flightControlEnvelope } from '../utils/flightPhysics.js'
import { createSteeringWheel, resolveSeatPreset } from '../utils/carInterior.js'
import { deriveInteriorLayout } from '../utils/carInteriorLayout.js'
import { smoothNormalsKeepHardEdges, splitTrianglesAtY } from '../three/geometry/smoothing.js'
import { disposeObject } from '../three/dispose.js'
import { createDoorRig } from '../three/parts/doors.js'
import { addBandGlass, addDloPane } from '../three/parts/glass.js'
import { addInteriorSeats } from '../three/interior/seats.js'
import { createLightsBumpers } from '../three/parts/lightsBumpers.js'
import { createMirrors } from '../three/parts/mirrors.js'
import { createWheels, addArchLiners, createLiftDucts } from '../three/parts/wheels.js'
import { createMaterialSet } from '../three/materials.js'

const { t } = useI18n()

const props = defineProps({
  carParams: {
    type: Object,
    required: true
  },
  carType: {
    type: String,
    default: 'sedan'
  },
  carColor: {
    type: String,
    default: '#4ade80'
  },
  viewAngle: {
    type: String,
    default: 'perspective'
  },
  wireframe: {
    type: Boolean,
    default: false
  },
  // 车门是否处于打开位（外部可绑开门按钮状态）：
  // 门洞常挖、门板为唯一门几何；本 prop 仅作外部状态同步入口，几何不受影响。
  doorOpened: {
    type: Boolean,
    default: false
  },
  // 后端真实 NURBS 采样网格（Designer 生成后传入）：
  // { parts: [{name,type,points:[[[x,y,z]]](canonical,mm),color,opacity}],
  //   wheels: [{radius,width,position:{x,y,z}(author,mm)}] }
  // 缺省时走 2D 轮廓 ExtrudeGeometry 近似路径（Demo 页/游客态）
  nurbsMesh: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:viewAngle', 'update:wireframe'])

const containerRef = ref(null)
const wireframeMode = ref(props.wireframe)
const autoRotate = ref(true)
const currentView = ref(props.viewAngle)
const isFullscreen = ref(false)

const viewAngles = [
  { key: 'front', label: 'Front', icon: 'F' },
  { key: 'rear', label: 'Rear', icon: 'R' },
  { key: 'left', label: 'Left', icon: 'L' },
  { key: 'right', label: 'Right', icon: 'R' },
  { key: 'top', label: 'Top', icon: 'T' },
  { key: 'bottom', label: 'Bottom', icon: 'B' },
  { key: 'isometric', label: 'Isometric', icon: 'I' },
  { key: 'perspective', label: 'Perspective', icon: 'P' }
]

const currentViewLabel = computed(() => {
  const v = viewAngles.find(v => v.key === currentView.value)
  return v ? v.label.toUpperCase() : 'PERSPECTIVE'
})

let scene, camera, renderer, carGroup
// initScene 实际绑定事件的容器元素。onUnmounted 触发时 Vue 已清空模板 ref
// （containerRef.value === null），卸载解绑必须用这个缓存引用，否则监听泄漏。
let boundContainer = null

// ---- 平稳垂直起降（VTOL）分支状态 ----
// flightProgress ∈ [0,1]：0=地面，1=稳态悬浮；推进速率 = dt/liftDuration，
// 高度 = hoverAltitude × quinticSmoothstep(progress)（C² 连续，端点加速度为零）；
// 全程纯垂直运动 + 相机零滚转 + 过阻尼呼吸（ζ≥1）→ 无眩晕
const flightEngaged = ref(false)
const flightAvailable = computed(() => props.carParams?.enable_vtol !== false)
let flightProgress = 0
let flightLastMs = 0
// VTOL 特效（升力环 + 地面能量场）持有权在 scene/flightFx.js：组件只保留实例与布局，
// 不再保存 rings / groundGlow 镜像，animate 一律通过 flightFx.update 读写。
let flightFx = null
// createCar 里与 createLiftDucts 共用同一份 deriveLiftDevices 结果，flightFx.ensure 原样复用
let currentLiftLayout = null

// ---- 车门打开动画状态 ----
// doorOpen 开关；doorProgress ∈ [0,1] 缓动趋近目标；doorHinges 由 createCar 重建
const doorOpen = ref(false)
let doorHinges = []
let doorSeams = []
let doorProgress = 0
const toggleDoor = () => { doorOpen.value = !doorOpen.value }

// 门洞/玻璃洞口**常挖**（与门开合状态无关）：门板 + 门片玻璃是全车唯一的门几何——
// 关门时门板/玻璃盖住洞口封闭，开门时随铰链外摆、原位留下全空通透孔洞。
// 动画本身由 doorProgress 平滑驱动，开合不再触发车身重建。

// ---- 反重力飞控：360° 原地转向 + 姿态微摆 ----
// 偏航为累计角（无 wrap）：连续指令多圈累加，全自由度无限制；
// 转向剖面 Δ·quintic(t/T) —— C² 端点归零（角速度/角加速度平滑起落，无卡顿无失稳）
const yawTurning = ref(false)
let flightYawCurrent = 0      // 当前累计偏航角（deg，落地后保留 → 原地掉头朝向生效）
let flightYawFrom = 0
let flightYawTarget = 0
let flightYawProgress = 1     // 1 = 就绪（可接受新转向指令）
let flightYawDuration = 1

/** 能耗 HUD（悬停功率 + 续航倍数，公式与后端 flight_envelope 同源） */
const flightEnergy = computed(() => {
  if (!flightAvailable.value || !props.carParams) return null
  const fp = resolveFlightParams(props.carType, props.carParams)
  const dims = {
    overall_length: props.carParams.overall_length,
    overall_width: props.carParams.overall_width,
    overall_height: props.carParams.overall_height
  }
  const env = flightControlEnvelope(dims, fp)
  return { kw: env.hoverPowerKw, mult: env.enduranceMultiple, ok: env.enduranceOk }
})

/** 原地转向指令：Δ∈(-∞,∞) 累计；时长按峰值角速度 45°/s 舒适限动态计算 */
const startTurn = (delta) => {
  if (yawTurning.value || !flightEngaged.value) return
  flightYawFrom = flightYawTarget
  flightYawTarget += delta
  flightYawDuration = turnDurationSec(delta)
  flightYawProgress = 0
  yawTurning.value = true
}
let animationId = null
let isDragging = false          // 由 interactions.js 通过 view.setDragging 镜像，animate 的自动旋转据此暂停
let detachInteractions = null   // attachInteractions 返回的解绑函数
let targetRotation = { x: 0.4, y: 0.8 }
let currentRotation = { x: 0.4, y: 0.8 }
let targetDistance = 8
let currentDistance = 8
let targetPan = { x: 0, y: 0 }
let currentPan = { x: 0, y: 0 }
let isOrthoCamera = false
let orthoCamera

// 视角预设：车长沿 X 轴（X+ 朝车头）。正交视角 dist 经 0.6 系数映射为半视口高度 d
// front=相机在 +X（正对车头）/ rear=-X / left=-Z（驾驶员侧）/ right=+Z
const viewPresets = {
  front: { x: 0, y: Math.PI / 2, dist: 5, ortho: true },
  rear: { x: 0, y: -Math.PI / 2, dist: 5, ortho: true },
  left: { x: 0, y: Math.PI, dist: 5, ortho: true },
  right: { x: 0, y: 0, dist: 5, ortho: true },
  top: { x: Math.PI / 2, y: 0, dist: 5, ortho: true },
  bottom: { x: -Math.PI / 2, y: 0, dist: 5, ortho: true },
  isometric: { x: Math.PI / 4, y: Math.PI / 4, dist: 10, ortho: false },
  perspective: { x: 0.4, y: 0.8, dist: 8, ortho: false }
}

/**
 * 从后端 NURBS 采样网格构建高保真汽车（真实曲面，替代 ExtrudeGeometry 近似）
 *
 * 坐标映射：后端 canonical（X=车长, Y=车宽, Z=车高, mm）
 *           → three（x=车长, y=高, z=宽, m）
 */
const createNurbsCar = (mesh) => {
  const group = new THREE.Group()
  const M = 0.001

  for (const part of mesh.parts || []) {
    const pts = part.points
    if (!pts || pts.length < 2 || !pts[0] || pts[0].length < 2) continue
    const nu = pts.length
    const nv = pts[0].length
    const positions = new Float32Array(nu * nv * 3)
    let k = 0
    for (let i = 0; i < nu; i++) {
      for (let j = 0; j < nv; j++) {
        const p = pts[i][j]
        positions[k++] = p[0] * M   // X 车长
        positions[k++] = p[2] * M   // Z 车高 → three.y
        positions[k++] = p[1] * M   // Y 车宽 → three.z
      }
    }
    const indices = []
    for (let i = 0; i < nu - 1; i++) {
      for (let j = 0; j < nv - 1; j++) {
        const a = i * nv + j
        const b = i * nv + j + 1
        const c = (i + 1) * nv + j
        const d = (i + 1) * nv + j + 1
        indices.push(a, b, c, b, d, c)
      }
    }
    const geom = new THREE.BufferGeometry()
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geom.setIndex(indices)
    geom.computeVertexNormals()   // 共享顶点 → 平滑法线

    const isGlass = part.type === 'windshield' || part.type === 'rear_window'
      || part.type === 'side_glass'
    // 车漆件：BODY COLOR 面板选色优先（灯具/格栅/保险杠保留后端本色）
    const PAINT_TYPES = new Set(['body_shell', 'hood', 'roof', 'trunk', 'door', 'fender'])
    const isPaint = PAINT_TYPES.has(part.type)
    const paintColor = (isPaint && props.carColor) || part.color || props.carColor
    const material = isGlass
      ? new THREE.MeshPhysicalMaterial({
          color: part.color || '#a8c4cc',
          transparent: true,
          opacity: part.opacity ?? 0.25,
          metalness: 0,
          roughness: 0.08,
          envMapIntensity: 0.6,
          side: THREE.DoubleSide,
          depthWrite: false,
          wireframe: wireframeMode.value
        })
      : new THREE.MeshPhysicalMaterial({
          color: paintColor,
          metalness: 0.72,
          roughness: 0.28,
          clearcoat: 1.0,
          clearcoatRoughness: 0.06,
          envMapIntensity: 1.5,
          side: THREE.DoubleSide,
          wireframe: wireframeMode.value
        })
    const meshObj = new THREE.Mesh(geom, material)
    meshObj.castShadow = true
    meshObj.receiveShadow = true
    group.add(meshObj)
  }

  for (const w of mesh.wheels || []) {
    group.add(createNurbsWheel(w))
  }
  return group
}

/** 后端 wheel 部件 → three 轮子组（位置字典为 author 约定：y=高, z=宽） */
const createNurbsWheel = (w) => {
  const M = 0.001
  const g = new THREE.Group()
  const r = w.radius * M
  const width = (w.width || 200) * M

  const tireGeom = new THREE.CylinderGeometry(r, r, width, 40)
  tireGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    tireGeom,
    new THREE.MeshStandardMaterial({ color: 0x26262b, metalness: 0.1, roughness: 0.85 })))

  // 轮毂/轮芯端面必须比胎面更宽才能外露（否则被轮胎实体完全包住）
  const rimGeom = new THREE.CylinderGeometry(r * 0.62, r * 0.62, width * 1.08, 24)
  rimGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    rimGeom,
    new THREE.MeshStandardMaterial({ color: 0xb8bdc4, metalness: 0.95, roughness: 0.2 })))

  const hubGeom = new THREE.CylinderGeometry(r * 0.18, r * 0.18, width * 1.16, 12)
  hubGeom.rotateX(Math.PI / 2)
  g.add(new THREE.Mesh(
    hubGeom,
    new THREE.MeshStandardMaterial({ color: 0xd8dadd, metalness: 1.0, roughness: 0.15 })))

  const pos = w.position || {}
  g.position.set((pos.x || 0) * M, (pos.y || 0) * M, (pos.z || 0) * M)
  g.traverse((o) => { if (o.isMesh) o.castShadow = true })
  return g
}

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
function splitBodyAperturesInterior(geom, rects, zCap, bands = [], taperK = null, isBodyMaterial = null) {
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
 * 将后端 NURBS 网格对齐到 carProfile 的居中坐标系。
 * 数学部分（平移/偏航/等比缩放）在 carProfile.deriveNurbsFrame 中，此处只负责落到 Three 变换上。
 */
const alignNurbsToProfile = (body, mesh, P) => {
  body.updateMatrixWorld(true)
  const box = new THREE.Box3().setFromObject(body)
  if (box.isEmpty()) return { valid: false, scale: 1, flip: false }

  const wheelXs = (mesh.wheels || []).map((w) => (w.position?.x || 0) * 0.001)
  const frame = deriveNurbsFrame(
    { min: { x: box.min.x, y: box.min.y, z: box.min.z },
      max: { x: box.max.x, y: box.max.y, z: box.max.z } },
    wheelXs,
    P
  )
  if (!frame) return { valid: false, scale: 1, flip: false }

  body.rotation.y = frame.rotationY
  body.scale.setScalar(frame.scale)
  body.position.set(frame.position.x, frame.position.y, frame.position.z)
  body.updateMatrixWorld(true)
  return { valid: true, scale: frame.scale, flip: frame.flip }
}

/**
 * 内饰座椅 + 舱内附件装配：几何与挂载全部在 three/interior/seats.js（P2 拆分）。
 * 调用时序是契约——必须在 createDoorRig 之后，否则门板内饰拿不到铰链、开门时不跟动。
 */
const createCar = () => {
  // 每次重建先清空门铰链/门缝引用：NURBS 路径不建门，若残留上一台车的铰链会让
  // 门板内饰误挂到已销毁的 Group。动画每帧读取的也是这里的引用，必须同源。
  doorHinges = []
  doorSeams = []
  // 座椅材质预设由调用方解析（内饰模块不读 props）
  const seatPreset = resolveSeatPreset(props.carType, props.carParams)
  // 有后端真实网格时走高保真路径：车身先对齐到 carProfile 坐标系，再与内饰件同父级共存
  if (props.nurbsMesh) {
    const P = deriveCarProfile(props.carParams, props.carType)
    const root = new THREE.Group()
    const body = createNurbsCar(props.nurbsMesh)
    alignNurbsToProfile(body, props.nurbsMesh, P)
    root.add(body)
    addInteriorSeats({ parent: root, P, preset: seatPreset, doorHinges })
    return root
  }
  const group = new THREE.Group()

  // 侧围轮廓（米）：mm 推导与物理约束集中在纯函数，保证全车型拓扑合法
  const P = deriveCarProfile(props.carParams, props.carType)
  const {
    W, H, gc, wheelR, halfTrack,
    frontWheelX, rearWheelX, frontX, rearX,
    bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY,
    hoodEndX, cowlStartX, trunkStartX,
    windshieldTopX, rearWindowTopX, rearWindowBottomX,
    wheelArchRadius, archY, wheelArch,
    pickup, rails: railSpec, wing: wingSpec
  } = P

  // 材质集合：构建内工厂，每次 createCar 新建（车色/线框变化都走 updateCar 重建）
  const {
    bodyMat, interiorMat, bodyMats, glassMat,
    wheelMat, rimMat, rimDiscMat, chromeMat,
    ductMat, lipMat, linerMat
  } = createMaterialSet({ carColor: props.carColor, wireframe: wireframeMode.value })

  const bodyShape = new THREE.Shape()

  // 座舱玻璃划分（与 2D Car2D windowPath 同源锚点）；倾角/桶面参数先于车身变形计算，
  // 供车身 greenhouse 收窄与玻璃面板共用同一轮廓公式
  const cabin = deriveCabinGlass(P, {
    carType: props.carType,
    sideGlassAngle: props.carParams?.side_glass_angle,
    glassBarrelAngle: props.carParams?.glass_barrel_angle,
    glassBarrelRadius: props.carParams?.glass_barrel_radius
  })

  // 车门分缝线 / B柱宽度 / 门把手布置（2D/3D 同源，参数可调）；侧窗分片与门板共用同一条分缝
  const dl = deriveDoorLayout(P, cabin, {
    bPillarWidthRatio: props.carParams?.b_pillar_width_ratio,
    handleDropRatio: props.carParams?.handle_drop_ratio,
    handleXRatio: props.carParams?.handle_x_ratio,
    carType: props.carType
  })

  // 侧窗分片（A 柱前固定片/前门片/后门片/C 柱后固定片）：玻璃切片与玻璃洞口
  // 共用同一份分片口径（carGlass 纯函数，可单测）；须在车身挖洞前定义
  const paneRanges = deriveDloPaneRanges(dl, props.carParams?.door_seam_width ?? 8)

  // ---- 侧围外轮廓（2D/3D 唯一真源 bodySideOutline：顶边 G1 圆角 + 底边轮拱 notch + 接近/离去角切角）----
  // 轮拱做进外轮廓（非 holes 共线孔）→ bevel 沿轮廓走，拱底无残留车身色薄片，真正挖通
  let outlineCmds = bodySideOutline(P, props.carType, ROOF_FILLETS, P.ramps)
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
  const doorRearEdge = (dl.rearSeamX === null ? dl.midSeamX : dl.rearSeamX) - 0.004
  const doorFrontEdge = dl.frontSeamX + 0.004
  const doorHoleBottom = bodyBottomY + 0.028
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
  const bodyDepth = W - BODY_BEVEL_SIZE * 2
  const bodyThickness = BODY_BEVEL_SIZE
  const bodyExtentZ = (bodyDepth + bodyThickness * 2) / 2
  // 车轮/车门/门缝/后视镜的安装基准：车身实际半宽 bodyExtentZ（= W/2），
  // 不是 W/2 + bevel——否则这些部件会整体浮出车身外表面。
  const fit = deriveWheelFitment(P, bodyExtentZ)

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
  const applyGreenhouseTaper = (geom) => {
    // 先把横跨腰带线的长三角形切开，否则收窄后折板会渲染成大面积渐变破面
    splitTrianglesAtY(geom, dloFrame.dloYBot)
    const pos = geom.attributes.position
    for (let i = 0; i < pos.count; i++) {
      pos.setZ(i, pos.getZ(i) * taperK(pos.getY(i)))
    }
    pos.needsUpdate = true
    // 收窄后侧围端盖已成双曲面：必须按位置焊接求平滑法线，否则逐面法线烧出三角破面；
    // 腰带线（DLO 底边）钉为硬边——收窄拐点若被焊接平均扫过，腰线高光会晕染成一条
    // 宽泛爆白的「白带」；硬边让高光收成一条锐利折线，上下板面各自均匀过渡。
    smoothNormalsKeepHardEdges(geom, 1e-4, 32, [dloFrame.dloYBot])
  }
  applyGreenhouseTaper(bodyGeom)

  // 洞壁内饰化：门洞 + 全部侧窗分片洞口的洞壁（横贯车宽）改判深色内饰材质，
  // |z| ≥ 外蒙皮端面的倒角环带保留车身色作门框/窗框唇边；风挡/后风挡斜面玻璃带
  // 中央区改判暗舱底（A/C 柱区留车身色）——透明玻璃后读到的是舱影而非车漆壁。
  // 车顶边框：风挡/后风挡玻璃顶边停在柱顶圆角切点下方 FRONT_GLASS_TOP_BORDER 处——
  // 玻璃不包裹圆角、不搭上车顶；车顶圆角（车身色）本身即「车身色顶部边界」。
  // 暗舱底（内饰深色）只改判到玻璃顶边：玻璃覆盖区读作舱影，玻璃以上全是车身色，
  // 不再出现「玻璃上方一条宽深色厚板」的观感。
  const FRONT_GLASS_TOP_BORDER = 0.004
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

  const bodyMesh = new THREE.Mesh(bodyGeom, bodyMats)
  bodyMesh.castShadow = true
  bodyMesh.receiveShadow = true
  group.add(bodyMesh)

  // 皮卡货箱：深色内舱面嵌于栏板之间（略高于栏板上沿，俯视呈开放货舱）
  if (pickup) {
    const bedMat = new THREE.MeshStandardMaterial({
      color: 0x14141a, metalness: 0.2, roughness: 0.9,
      wireframe: wireframeMode.value
    })
    const bedLen = pickup.bedFrontX - pickup.bedRearX
    const bedGeom = new THREE.BoxGeometry(bedLen, 0.015, pickup.bedInteriorHalfZ * 2)
    const bed = new THREE.Mesh(bedGeom, bedMat)
    bed.position.set((pickup.bedFrontX + pickup.bedRearX) / 2, pickup.bedWallY + 0.006, 0)
    bed.receiveShadow = true
    group.add(bed)
  }

  // ---- 座舱玻璃划分（与 2D Car2D windowPath 同源锚点） ----
  // 真透明玻璃：浅灰绿 tint、低不透明度和极低粗糙度（真车侧窗透光观感），
  // 侧窗/风挡/后风挡覆盖区车身已开真实孔洞（侧窗）或改判暗舱底（斜面），
  // 玻璃后读到的是座舱而非车身色壁；depthWrite=false 避免舱内玻璃面排序伪影。
  // A/B/C 柱与车顶保持车身色（洞口间竖条 + 玻璃半宽以外斜面区），
  // 车身色顶部边界与玻璃因此清晰区分。

  // 斜面玻璃带：脊柱线由 carGlass.bandGlassSpine 生成（可单测）——含车顶 G1 圆角包裹
  // 采样与顶面搭接，玻璃随车身同一圆角弯曲（几何在 parts/glass.js，P2 拆分）。
  // 前风挡：底缘 = COWL（bottomInset 下退避开 bevel 外扩角），顶缘停在 A 柱顶圆角
  // 下方 FRONT_GLASS_TOP_BORDER 处——不包裹圆角、不搭上车顶：玻璃顶边始终低于车顶，
  // 车身色车顶前缘完整可见（旧实现搭接车顶 20mm，在顶面烧出一道高光横带 = 穿模）。
  const ws = cabin.windshield
  addBandGlass({
    group, material: glassMat, taperK,
    x1: ws.x1, y1: ws.y1, x2: ws.x2, y2: ws.y2, width: ws.width,
    topInset: ws.topInset + FRONT_GLASS_TOP_BORDER, bottomInset: ws.bottomInset
  })
  // 后风挡：顶缘同样停在车顶后缘圆角下方（皮卡无后风挡）；
  // 底缘下退 cPillarBottom 至 C 柱底圆角切点（玻璃不戳入尾部圆角）
  if (cabin.rearWindow) {
    const rw = cabin.rearWindow
    addBandGlass({
      group, material: glassMat, taperK,
      x1: rw.x1, y1: rw.y1, x2: rw.x2, y2: rw.y2, width: rw.width,
      topInset: rw.topInset + FRONT_GLASS_TOP_BORDER, bottomInset: ROOF_FILLETS.cPillarBottom
    })
  }

  // 侧窗 DLO（左右各分片）：多边形与 2D windowPath 逐点同源，顶部两角内收避开 G1 圆角；
  // Z 轮廓 = tumblehome 线性内收 + barrel 桶面圆弧鼓肚（dloZAt 纯函数，可单测）。
  // 面片沿高度细分成条带网格——四角面片无法表达桶面曲率
  // 侧窗按车门分缝切成 4 片/侧：A 柱前固定片 + 前门片 + 后门片 + C 柱后固定片。
  // 门片不直接挂载，先收集进 doorGlass，再由 createDoorRig 挂到对应车门铰链 Group
  // （与门板同轴同角度）——收集顺序是 doors 的输入契约，必须留在本例程里完成。
  // 分缝两侧各留半个缝宽间隙 → 玻璃上同样能看到门缝（与 2D 分缝线同坐标）。
  const doorGlass = []
  for (const zSide of [1, -1]) {
    // 分片边界与门缝坐标全部来自 carGlass.deriveDloPaneRanges（纯函数，可单测）：
    // A 柱前固定片 / 前门片 / 后门片（双门与皮卡无此片）/ C 柱后固定片
    for (const pane of paneRanges) {
      addDloPane({
        group, material: glassMat, doorGlass, cabin, dloFrame,
        xFront: pane.xFront, xRear: pane.xRear, zSide, hingeKey: pane.hingeKey
      })
    }
  }

  // B 柱：分缝线 B柱位置车身色立柱（叠于玻璃之上，与 2D B 柱线同位置）；
  // 宽度按 b_pillar_width_ratio 参数化（默认≈75mm，实车 60~120mm），与侧窗共面同倾角（pillarPlacement 纯函数）
  // B 柱 X 由门模块分缝唯一决定（与 2D 蓝线同坐标），不再用座舱 55% 启发式
  const pillarCabin = { ...cabin, pillar: { ...cabin.pillar, x: dl.midSeamX } }
  const pp = pillarPlacement(pillarCabin, dloFrame.dloYBot, dloFrame.dloYSpan, dloFrame.dloZBase)
  const pillarGeom = new THREE.BoxGeometry(dl.bWidth, pp.height, 0.008)
  pillarGeom.translate(0, pp.height / 2, 0)   // 底部置于原点，便于绕底倾斜
  for (const zSide of [1, -1]) {
    const pillar = new THREE.Mesh(pillarGeom, bodyMat)
    pillar.position.set(pp.x, pp.botY, zSide * pp.baseZ)
    pillar.rotation.x = -zSide * pp.tiltRad
    group.add(pillar)
  }


  // ---- 底盘上升装置（6~8 台，deriveLiftDevices 同源）----
  // 只落前后轮腔之间的封闭地板区间，绝不侵入轮腔切口；风道口下沉 12mm（不构成额外最低点）
  // 布局在此算一次：悬停风扇环（ensureFlightFx）沿用同一份 deriveLiftDevices，避免环与风道错位
  const liftLayout = deriveLiftDevices(P, resolveFlightParams(props.carType, props.carParams).liftFans)
  currentLiftLayout = liftLayout
  createLiftDucts({ parent: group, liftLayout, ductMat, lipMat })

  // ---- 四轮：胎 + 轮辋盘 + 轮唇 + 轮毂盖 + 5 辐条（几何在 parts/wheels.js）----
  // 材质由本例程创建后传入（chromeMat 与门把手共用，模块内不得重建）
  const wheelZ = fit.wheelZ
  createWheels({
    parent: group,
    frontX: frontWheelX,
    rearX: rearWheelX,
    wheelZ,
    wheelR,
    tireW: fit.tireW,
    wheelMat,
    rimDiscMat,
    rimMat,
    chromeMat
  })

  // ---- 轮腔内衬：与拱口同形的内嵌椭圆拱壳（半椭圆上缘 + 竖直唇落至底板）----
  // 圆形筒对椭圆拱口必然四周互穿（前后壁/顶部戳出 = 拓扑破面），改用 archLinerProfile
  // 纯函数生成的拱形开壳，整体内缩 12mm 严格位于空腔内，横跨全宽挡住对侧亮色 bevel
  addArchLiners({ parent: group, P, bodyExtentZ, material: linerMat })

  // ---- 方向盘总成：共享 createSteeringWheel（含 SAE 22° 轮面倾角，与独立预览页同一真源）----
  group.add(createSteeringWheel(P))

  // ---- 保险杠 + 前大灯 + 尾灯：贴前/后立面外表面（几何在 parts/lightsBumpers.js）----
  // 坐标常量（±5mm 保险杠外沿、灯组贴面 6mm 露出、尾灯复用头灯 hlZ）逐字保留，
  // 添加顺序与拆分前一致：车身之后、createDoorRig 之前。
  createLightsBumpers({
    parent: group,
    W,
    frontX,
    rearX,
    bodyBottomY,
    hoodLineY,
    trunkLineY,
    wall: fit.wall,
    outlineShape: outlinePts.shape,
    bodyMat,
    wireframe: wireframeMode.value
  })

  // ---- 车门分缝线 + 门板（可绕前铰链打开）+ 门把手（随门板运动）----
  // 几何组装整体在 parts/doors.js（P2 拆分）：此处只传真源坐标与共用材质实例，
  // 返回的铰链/缝条引用交给 animate() 逐帧驱动开合，运动学与拆分前一致。
  const doorRig = createDoorRig({
    parent: group,
    wall: fit.wall,
    doorLayout: dl,
    bodyBottomY,
    shoulderY,
    bodyMat,
    chromeMat,
    doorSeamWidth: props.carParams?.door_seam_width ?? 8,
    doorGlass,
    wireframe: wireframeMode.value
  })
  doorHinges = doorRig.hinges
  doorSeams = doorRig.seams

  // ---- 外后视镜：镜壳（球面雕刻水滴形）+ 连接颈 + 密封圈 + 凸面镜片 ----
  // 几何与左右镜像全在 parts/mirrors.js（P2 拆分）：安装点半宽仍走 shellHalfZAt 真源，
  // 三处亚毫米防 z-fighting 偏移与 housingZ 系数逐字保留；两片镜共用一张贴花纹理。
  createMirrors({
    parent: group,
    hoodLineY,
    hoodEndX,
    bodyMat,
    dloFrame,
    bodyExtentZ,
    wireframe: wireframeMode.value
  })

  if (wingSpec) {
    // GT 尾翼：翼片沿车长（X）取弦长、横跨车宽（Z），支柱落在后甲板实体上
    const wingGeom = new THREE.BoxGeometry(wingSpec.chord, wingSpec.thickness, wingSpec.span)
    const wing = new THREE.Mesh(wingGeom, bodyMat)
    wing.position.set(wingSpec.x, wingSpec.y, 0)
    group.add(wing)

    // 两根垂直支柱，从后甲板向上承托翼片
    const wingSupportGeom = new THREE.BoxGeometry(0.035, wingSpec.supportH, 0.05)
    const ws1 = new THREE.Mesh(wingSupportGeom, chromeMat)
    ws1.position.set(wingSpec.x, wingSpec.deckY + wingSpec.supportH / 2, wingSpec.strutZ)
    group.add(ws1)
    const ws2 = new THREE.Mesh(wingSupportGeom, chromeMat)
    ws2.position.set(wingSpec.x, wingSpec.deckY + wingSpec.supportH / 2, -wingSpec.strutZ)
    group.add(ws2)
  }

  if (railSpec) {
    // 行李架：长边沿车长（X）、与车身同色，半嵌车顶，阴影落在车顶而非侧面
    const railGeom = new THREE.BoxGeometry(railSpec.length, 0.035, 0.045)
    const rail1 = new THREE.Mesh(railGeom, bodyMat)
    rail1.position.set(railSpec.xCenter, railSpec.y, railSpec.z)
    group.add(rail1)
    const rail2 = new THREE.Mesh(railGeom, bodyMat)
    rail2.position.set(railSpec.xCenter, railSpec.y, -railSpec.z)
    group.add(rail2)
  }

  // ---- 内饰座椅：按 carProfile 的座椅布局（seatRows / seatRowCounts / H 点 / 排距）逐排生成 ----
  // 纯参数化几何、无贴图；由 createCar 统一构建 → 车型切换时随 updateCar() 整体重建。
  // 玻璃为 depthWrite:false 透明件，座舱内座椅可从风挡/侧窗看到。
  addInteriorSeats({ parent: group, P, preset: seatPreset, doorHinges })

  return group
}

const initScene = () => {
  const container = containerRef.value
  if (!container) return
  
  // 机位状态访问器：动画/视图状态仍由组件持有（P3 animate 批再迁），
  // 这里只把读写入口交给 createScene；钩子签名、字段与挂载时机保持不变。
  const viewControls = {
    applyPreset: (key) => setViewAngle(key),
    snap: () => {
      currentRotation.x = targetRotation.x
      currentRotation.y = targetRotation.y
      currentDistance = targetDistance
      currentPan.x = targetPan.x
      currentPan.y = targetPan.y
    },
    setTargets: (pose) => {
      if (typeof pose.rotX === 'number') targetRotation.x = pose.rotX
      if (typeof pose.rotY === 'number') targetRotation.y = pose.rotY
      if (typeof pose.distance === 'number') targetDistance = pose.distance
      if (typeof pose.panX === 'number') targetPan.x = pose.panX
      if (typeof pose.panY === 'number') targetPan.y = pose.panY
    },
    setOrtho: (ortho) => { isOrthoCamera = ortho }
  }

  // 场景基座（渲染器/相机/灯光/环境/地面/网格 + __car3d__ 注册）全部在 scene/createScene.js
  const sceneApi = createScene({
    container,
    wireframe: wireframeMode.value,
    nurbs: !!props.nurbsMesh,
    viewControls
  })
  scene = sceneApi.scene
  camera = sceneApi.camera
  renderer = sceneApi.renderer
  orthoCamera = sceneApi.orthoCamera
  // 特效实例与场景同作用域；ensure 仍由 animate 首帧调用（保持 noCastShadow 时序）
  flightFx = createFlightFx({ scene })

  carGroup = createCar()
  carGroup.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = !child.userData.noCastShadow   // 玻璃不投实心影
      child.receiveShadow = true
    }
  })
  scene.add(carGroup)

  // 视觉基线/调试钩子：setDoor / viewState 依赖门铰链与动画状态，仍在 createCar 之后补挂；
  // setViewInstant / setCameraPose 由 createScene 注册（字段与行为不变）
  scene.userData.__car3d__.setDoor = (open) => {
    doorOpen.value = open
    doorProgress = open ? 1 : 0
    const openRad = ((props.carParams?.door_open_angle ?? 70) * Math.PI) / 180
    for (const d of doorHinges) d.hinge.rotation.y = d.sign * openRad
    for (const s of doorSeams) s.visible = !open
  }
  scene.userData.__car3d__.viewState = () => ({
    rotX: currentRotation.x,
    rotY: currentRotation.y,
    targetX: targetRotation.x,
    targetY: targetRotation.y,
    distance: currentDistance,
    targetDistance,
    ortho: isOrthoCamera
  })

  boundContainer = container
  // 交互（拖拽/缩放/resize）在 scene/interactions.js：只写 target*，缓动留给 animate 批。
  // 传入的宿主是缓存的 boundContainer（卸载时 containerRef 已为空），detach 也解绑它。
  detachInteractions = attachInteractions({
    container: boundContainer,
    camera,
    orthoCamera,
    renderer,
    view: {
      getRotation: () => ({ x: targetRotation.x, y: targetRotation.y }),
      setRotation: (x, y) => { targetRotation.x = x; targetRotation.y = y },
      getPan: () => ({ x: targetPan.x, y: targetPan.y }),
      setPan: (x, y) => { targetPan.x = x; targetPan.y = y },
      getDistance: () => targetDistance,
      setDistance: (v) => { targetDistance = v },
      setDragging: (v) => { isDragging = v }
    }
  })

  animate()
}

// ---- VTOL 特效：升力风扇环（随车）+ 地面能量场（贴地衰减）----
// 实现已迁至 scene/flightFx.js（P3）：持有权、建环常量、逐帧外观公式全部在模块内；
// 这里只保留调用点，保证 updateCar / onUnmounted 的释放时序不变。
const disposeFlightFx = () => {
  flightFx?.dispose()
}

const ensureFlightFx = () => {
  flightFx?.ensure({
    carGroup,
    carParams: props.carParams,
    liftLayout: currentLiftLayout
  })
}

const toggleFlight = () => {
  if (!flightAvailable.value) return
  flightEngaged.value = !flightEngaged.value
}

const animate = () => {
  animationId = requestAnimationFrame(animate)

  // ---- VTOL 飞行动画（无眩晕：C² 平滑起升 + 过阻尼悬浮呼吸 + 零滚转）----
  const vnow = performance.now()
  const vdt = flightLastMs ? Math.min((vnow - flightLastMs) / 1000, 0.05) : 0
  flightLastMs = vnow
  if (carGroup && flightAvailable.value) {
    ensureFlightFx()
    const fp = resolveFlightParams(props.carType, props.carParams)
    const target = flightEngaged.value ? 1 : 0
    if (flightProgress !== target) {
      const step = vdt / Math.max(fp.liftDuration, 0.1)
      flightProgress = target > flightProgress
        ? Math.min(flightProgress + step, 1)
        : Math.max(flightProgress - step, 0)
    }
    const lift = quinticSmoothstep(flightProgress)
    // 悬浮呼吸：振幅随 lift² 衰减（地面为零），频率 < 0.2Hz 远离晕动敏感频段
    const bob = hoverBobOffset(vnow / 1000, fp) * lift * lift
    carGroup.position.y = (fp.hoverAltitude * lift + bob) / 1000
    // ---- 反重力飞控：360° 原地转向（累计角无 wrap，C² 剖面无卡顿）----
    if (flightYawProgress < 1) {
      flightYawProgress = Math.min(1, flightYawProgress + vdt / Math.max(flightYawDuration, 0.1))
      const eased = quinticSmoothstep(flightYawProgress)
      flightYawCurrent = flightYawFrom + (flightYawTarget - flightYawFrom) * eased
      if (flightYawProgress >= 1) {
        flightYawCurrent = flightYawTarget
        yawTurning.value = false
      }
    }
    carGroup.rotation.y = flightYawCurrent * Math.PI / 180
    // 姿态微摆（roll/pitch 双低频谱，峰值 ≤0.85°/ζ < ±2° 包络；振幅随 lift² 衰减）：
    // 原地转向零向心加速度 → 零侧倾耦合，roll 与 yaw 解耦（全自由度姿态稳定）
    const attRoll = attitudeSample(vnow / 1000, fp.darkMatterRatio) * lift * lift
    const attPitch = attitudeSample(vnow / 1000 + 17.3, fp.darkMatterRatio) * lift * lift
    carGroup.rotation.z = attRoll * Math.PI / 180
    carGroup.rotation.x = attPitch * Math.PI / 180
    // 特效：风扇环脉冲（蓝），地面能量场随高度衰减（绿）
    flightFx?.update({ now: vnow, lift, progress: flightProgress })
  }

  // ---- 车门开合动画：doorProgress 缓动趋近目标，铰链绕竖直轴 rotation.y 开合（把手随门板）----
  if (doorHinges.length) {
    const dTarget = doorOpen.value ? 1 : 0
    if (doorProgress !== dTarget) {
      const step = vdt / 0.8
      doorProgress = dTarget > doorProgress ? Math.min(doorProgress + step, 1) : Math.max(doorProgress - step, 0)
    }
    const openRad = ((props.carParams?.door_open_angle ?? 70) * Math.PI) / 180
    const e = quinticSmoothstep(doorProgress) * openRad
    for (const d of doorHinges) d.hinge.rotation.y = d.sign * e   // 正负号使门板向外摆（+Z 侧向 +Z、−Z 侧向 −Z）
    // 门缝条属于「关门时的分缝观感」：门一开就与门板脱开、悬在洞口中央，
    // 必须在 doorProgress 抬起后立即隐藏，只在完全关闭时显示。
    const seamVisible = doorProgress < 0.02
    for (const s of doorSeams) s.visible = seamVisible
  }

  if (autoRotate.value && !isDragging && currentView.value === 'perspective') {
    targetRotation.y += 0.004
  }

  currentRotation.x += (targetRotation.x - currentRotation.x) * 0.08
  currentRotation.y += (targetRotation.y - currentRotation.y) * 0.08
  currentDistance += (targetDistance - currentDistance) * 0.08
  currentPan.x += (targetPan.x - targetPan.x) * 0.08
  currentPan.y += (targetPan.y - currentPan.y) * 0.08

  const activeCamera = isOrthoCamera ? orthoCamera : camera

  activeCamera.position.x = currentPan.x + Math.sin(currentRotation.y) * Math.cos(currentRotation.x) * currentDistance
  activeCamera.position.y = currentPan.y + Math.sin(currentRotation.x) * currentDistance + 1
  activeCamera.position.z = Math.cos(currentRotation.y) * Math.cos(currentRotation.x) * currentDistance
  activeCamera.lookAt(currentPan.x, 1, currentPan.y)

  renderer.render(scene, activeCamera)
}

const setViewAngle = (view) => {
  currentView.value = view
  emit('update:viewAngle', view)
  
  const preset = viewPresets[view]
  if (preset) {
    targetRotation.x = preset.x
    targetRotation.y = preset.y
    targetDistance = preset.dist
    isOrthoCamera = preset.ortho
    
    if (preset.ortho) {
      const container = containerRef.value
      if (container) {
        const w = container.clientWidth
        const h = container.clientHeight
        const aspect = w / h
        const d = preset.dist * 0.6
        orthoCamera.left = -d * aspect
        orthoCamera.right = d * aspect
        orthoCamera.top = d
        orthoCamera.bottom = -d
        orthoCamera.updateProjectionMatrix()
      }
    }
  }
}

const resetView = () => {
  targetRotation = { x: 0.4, y: 0.8 }
  targetDistance = 8
  targetPan = { x: 0, y: 0 }
  currentView.value = 'perspective'
  isOrthoCamera = false
  emit('update:viewAngle', 'perspective')
}

const toggleWireframe = () => {
  wireframeMode.value = !wireframeMode.value
  emit('update:wireframe', wireframeMode.value)
  if (scene) scene.userData.__car3d__.wireframe = wireframeMode.value   // 多实例定位标记同步
  updateCar()
}

const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
}

const toggleFullscreen = () => {
  const container = containerRef.value
  if (!container) return
  if (!document.fullscreenElement) {
    container.requestFullscreen().then(() => { isFullscreen.value = true }).catch(() => {})
  } else {
    document.exitFullscreen().then(() => { isFullscreen.value = false }).catch(() => {})
  }
}

// 材质随附贴图（alphaMap 等 CanvasTexture）必须显式 dispose，否则内存泄漏
// —— 实现已迁至 src/three/dispose.js（P1 拆分）

const updateCar = () => {
  if (!scene || !carGroup) return
  scene.userData.__car3d__.nurbs = !!props.nurbsMesh   // 生成后 nurbs 标记同步，供多实例定位
  scene.remove(carGroup)
  disposeFlightFx()
  currentLiftLayout = null   // 旧布局随旧车失效，createCar 重新赋值后再被 flightFx.ensure 复用
  disposeObject(carGroup)
  carGroup = null
  carGroup = createCar()
  carGroup.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = !child.userData.noCastShadow   // 玻璃不投实心影
      child.receiveShadow = true
    }
  })
  scene.add(carGroup)
}

watch(
  () => [props.carParams, props.carType, props.carColor, props.nurbsMesh],
  () => updateCar(),
  { deep: true }
)

watch(
  () => props.viewAngle,
  (val) => {
    if (val !== currentView.value) {
      setViewAngle(val)
    }
  }
)

watch(
  () => props.wireframe,
  (val) => {
    if (val !== wireframeMode.value) {
      wireframeMode.value = val
      updateCar()
    }
  }
)

onMounted(() => {
  initScene()
  if (props.viewAngle !== 'perspective') {
    setViewAngle(props.viewAngle)
  }
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  disposeFlightFx()
  flightFx = null
  // 模板 ref 此时已被 Vue 清空（containerRef.value === null）；interactions.js 内部
  // 用 initScene 时缓存的 container 解绑，所以这里只需调用 detach，不再碰 containerRef。
  if (detachInteractions) {
    detachInteractions()
    detachInteractions = null
  }
  boundContainer = null
  disposeObject(carGroup)
  if (typeof window !== 'undefined' && Array.isArray(window.__CAR3D_SCENES__)) {
    const reg = window.__CAR3D_SCENES__
    const idx = reg.indexOf(scene)
    if (idx >= 0) reg.splice(idx, 1)
    // 修正全局调试指针，避免继续指向已销毁场景
    window.__THREE_SCENE__ = reg.length ? reg[reg.length - 1] : null
  }
  if (renderer) {
    renderer.dispose()
    const gl = renderer.getContext()
    const ext = gl.getExtension('WEBGL_lose_context')
    if (ext) ext.loseContext()
    renderer.domElement.remove()
    renderer = null
  }
  if (scene) {
    scene.clear()
    scene = null
  }
})
</script>

<style scoped>
.car-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: var(--bg-primary);
}

.view-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  z-index: 10;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  padding: 6px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.view-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  border: none;
  padding: 0;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: Inter, sans-serif;
}

.view-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
}

.view-btn.active {
  background: rgba(59, 130, 246, 0.25);
  color: #60a5fa;
}

.control-buttons {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 10;
}

.ctrl-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}

.ctrl-btn svg {
  width: 16px;
  height: 16px;
}

.ctrl-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
}

.ctrl-btn.active {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.4);
}

/* VTOL 飞行分支：翡翠绿主色（品牌一致），激活时呼吸辉光 */
.ctrl-btn.vtol-btn:hover {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.35);
}

.ctrl-btn.vtol-btn.active {
  background: rgba(16, 185, 129, 0.22);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.5);
  animation: vtol-glow 1.6s ease-in-out infinite;
}

@keyframes vtol-glow {
  0%, 100% { box-shadow: 0 0 4px rgba(16, 185, 129, 0.25); }
  50% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.55); }
}

.status-item.vtol-status {
  color: #10b981;
  letter-spacing: 0.12em;
}

/* 反重力飞控：原地转向按钮（悬停态出现；字号缩小承载度数文本） */
.ctrl-btn.turn-btn {
  color: #10b981;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

.ctrl-btn.turn-btn:hover {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.35);
}

.ctrl-btn.turn-btn.busy {
  opacity: 0.45;
  pointer-events: none;
}

.ctrl-btn.turn-btn.turn-full {
  font-size: 11px;
  letter-spacing: 0.02em;
}

.status-item.energy-status {
  letter-spacing: 0.04em;
}

.status-bar {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10;
}

.view-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  font-family: Inter, sans-serif;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.status-item {
  font-size: 10px;
  color: var(--text-muted);
  font-family: Inter, sans-serif;
  letter-spacing: 0.5px;
}
</style>
