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
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { deriveCarProfile, deriveWheelFitment, archLinerProfile, bodySideOutline, deriveDoorLayout, deriveLiftDevices, filletCorner, roofFilletSet } from '../utils/carProfile.js'
import { deriveCabinGlass, dloZAt, pillarPlacement, buildDloFrame, buildDloStripRange, deriveDloPaneRanges, shellHalfZAt, bandGlassSpine, ROOF_FILLETS, BODY_BEVEL_SIZE, GLASS_SURFACE_GAP } from '../utils/carGlass.js'
import { resolveFlightParams, quinticSmoothstep, hoverBobOffset,
  turnDurationSec, attitudeSample, flightControlEnvelope } from '../utils/flightPhysics.js'

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
  // true = 车身按 deriveDoorLayout 挖门洞，门板成为唯一覆盖几何（无重复侧壁）；
  // false = 车身完整，门板贴合侧壁（关闭态无需挖洞）。
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

// ---- 平稳垂直起降（VTOL）分支状态 ----
// flightProgress ∈ [0,1]：0=地面，1=稳态悬浮；推进速率 = dt/liftDuration，
// 高度 = hoverAltitude × quinticSmoothstep(progress)（C² 连续，端点加速度为零）；
// 全程纯垂直运动 + 相机零滚转 + 过阻尼呼吸（ζ≥1）→ 无眩晕
const flightEngaged = ref(false)
const flightAvailable = computed(() => props.carParams?.enable_vtol !== false)
let flightProgress = 0
let flightLastMs = 0
let flightRings = []          // 升力风扇环（carGroup 子对象，随车升降）
let flightGroundGlow = null   // 地面能量场（scene 子对象，随高度衰减）

// ---- 车门打开动画状态 ----
// doorOpen 开关；doorProgress ∈ [0,1] 缓动趋近目标；doorHinges 由 createCar 重建
const doorOpen = ref(false)
let doorHinges = []
let doorProgress = 0
const toggleDoor = () => { doorOpen.value = !doorOpen.value }

// 开门状态下：车身按 deriveDoorLayout 挖门洞（门板成为覆盖洞口的唯一几何，
// 不再与实体侧壁重复）；关门状态：车身完整，门板贴于侧壁外（常规关闭门缝观感）。
// 挖洞/恢复在 updateCar 重建车身时生效，动画本身仍由 doorProgress 平滑驱动。
watch(doorOpen, () => updateCar())

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
let isDragging = false
let previousMousePosition = { x: 0, y: 0 }
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
          color: part.color || '#87CEEB',
          transparent: true,
          opacity: part.opacity ?? 0.5,
          metalness: 0,
          roughness: 0.05,
          envMapIntensity: 1.2,
          side: THREE.DoubleSide,
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
 * 按位置焊接后平滑法线（保留硬边）
 *
 * ExtrudeGeometry 为非索引几何：每个三角形持有一份独立法线。greenhouse 收窄是随 y 变化的
 * 线性 Z 缩放，会把原本平坦的侧围端盖变成双曲面；此时 computeVertexNormals() 只能给出
 * 逐面法线——侧围 / 车顶 / 倒角上因此出现一片片明暗不同的三角面（用户读作「亮色破面」），
 * 车顶薄倒角更会被切成一串高亮细条（读作「尖刺」）。
 * 这里按位置把法线焊接平均，只合并夹角小于阈值的面，腰线、轮拱等硬边仍是硬边。
 */
function smoothNormalsKeepHardEdges(geom, tol = 1e-4, angleDeg = 32) {
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

  // 逐三角形面法线（同一三角形的三个顶点共用）
  const face = new Float32Array(n * 3)
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
  }

  // 焊接平均：仅合并与自身面夹角小于阈值的相邻面
  const out = new Float32Array(n * 3)
  for (let i = 0; i < n; i++) {
    const own = i * 3
    const f0x = face[own], f0y = face[own + 1], f0z = face[own + 2]
    let sx = 0, sy = 0, sz = 0
    for (const j of buckets.get(keyOf(i))) {
      const q = j * 3
      if (face[q] * f0x + face[q + 1] * f0y + face[q + 2] * f0z < cosT) continue
      sx += face[q]; sy += face[q + 1]; sz += face[q + 2]
    }
    const len = Math.hypot(sx, sy, sz) || 1
    out[own] = sx / len; out[own + 1] = sy / len; out[own + 2] = sz / len
  }
  geom.setAttribute('normal', new THREE.BufferAttribute(out, 3))
}

/**
 * 门洞内壁材质分组（开门状态专用）
 *
 * 车身由侧围轮廓整宽挤出：门洞沿 Z 贯穿，洞口的四壁（底槛面 / 前后门框面）
 * 因此横贯整车宽度。开门后被看成大片车身色板——即「多余车身」。
 * 把三角形重心落在门洞矩形内、且不在外蒙皮端面（|z| 接近半车宽的倒角环带保留
 * 车身色作门框唇边）的三角形归入材质组 1，用深色内饰材质渲染，
 * 门洞内读作座舱内壁，车身色不再出现在门洞里。
 *
 * @param {THREE.BufferGeometry} geom 车身挤出几何（非索引，就地重排）
 * @param {{x0:number,x1:number,y0:number,y1:number}} rect 门洞矩形（米）
 * @param {number} zCap 外蒙皮端面保留带宽（|z| ≥ zCap 的三角形保持车身色）
 * @returns {number} 归入内饰组的三角形数
 */
function splitDoorApertureInterior(geom, rect, zCap) {
  const pos = geom.attributes.position
  const arr = pos.array
  const nTri = pos.count / 3
  const exterior = []
  const interior = []
  for (let i = 0; i < nTri; i++) {
    const o = i * 9
    const cx = (arr[o] + arr[o + 3] + arr[o + 6]) / 3
    const cy = (arr[o + 1] + arr[o + 4] + arr[o + 7]) / 3
    const cz = (arr[o + 2] + arr[o + 5] + arr[o + 8]) / 3
    const inAperture = cx > rect.x0 && cx < rect.x1 && cy > rect.y0 && cy < rect.y1 && Math.abs(cz) < zCap
    ;(inAperture ? interior : exterior).push(o)
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

const createCar = () => {
  // 有后端真实网格时走高保真路径
  if (props.nurbsMesh) return createNurbsCar(props.nurbsMesh)
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

  const bodyColor = new THREE.Color(props.carColor)

  const bodyMat = new THREE.MeshStandardMaterial({
    color: bodyColor,
    metalness: 0.6,
    roughness: 0.25,
    wireframe: wireframeMode.value
  })

  // 门洞内壁材质（开门状态）：深色内饰面，替代洞壁上的车身色 → 门洞里读作座舱，
  // 不再是一块横贯车宽的车身色板。DoubleSide 兜住洞壁朝向差异。
  const interiorMat = new THREE.MeshStandardMaterial({
    color: 0x1b1d22,
    metalness: 0.2,
    roughness: 0.9,
    side: THREE.DoubleSide,
    wireframe: wireframeMode.value
  })

  const wheelMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a1f,
    metalness: 0.3,
    roughness: 0.8,
    wireframe: wireframeMode.value
  })

  const rimMat = new THREE.MeshStandardMaterial({
    color: 0xaaaaaa,
    metalness: 0.9,
    roughness: 0.2,
    wireframe: wireframeMode.value
  })

  const chromeMat = new THREE.MeshStandardMaterial({
    color: 0xcccccc,
    metalness: 1.0,
    roughness: 0.1,
    wireframe: wireframeMode.value
  })

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

  // 开门状态：在门区内开真实矩形洞（holes），门板成为覆盖洞口的唯一几何——
  // 开门时侧壁不再与门板重复，物理空间唯一、无 z-fighting。
  // 关闭状态不挖洞：门板薄板贴于完整侧壁外，即常规车关闭门缝的视觉。
  // 注意：用 holes 而非压平轮廓，避免挤出 bevel 在压平区产生折叠/顶点爆炸。
  let doorAperture = null
  if (props.doorOpened || doorOpen.value) {
    const doorRearEdge = (dl.rearSeamX === null ? dl.midSeamX : dl.rearSeamX) - 0.004
    const doorFrontEdge = dl.frontSeamX + 0.004
    const doorHoleBottom = bodyBottomY + 0.028
    const doorHoleTop = beltLineY - 0.004
    const hole = new THREE.Path()
    hole.moveTo(doorRearEdge, doorHoleBottom)
    hole.lineTo(doorFrontEdge, doorHoleBottom)
    hole.lineTo(doorFrontEdge, doorHoleTop)
    hole.lineTo(doorRearEdge, doorHoleTop)
    hole.closePath()
    bodyShape.holes.push(hole)
    // 门洞矩形（供挤出后把洞口内壁改判为内饰材质，见 splitDoorApertureInterior）
    doorAperture = {
      x0: doorRearEdge - 0.008, x1: doorFrontEdge + 0.008,
      y0: doorHoleBottom - 0.008, y1: doorHoleTop + 0.004
    }
  }

  const bodyDepth = W
  const bodyThickness = BODY_BEVEL_SIZE
  const bodyExtentZ = (bodyDepth + bodyThickness * 2) / 2
  // 车轮装配配合（纯函数同源判据）：胎外侧面收进侧壁内，杜绝轮-身干涉观感
  const fit = deriveWheelFitment(P, bodyThickness)

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
    const pos = geom.attributes.position
    for (let i = 0; i < pos.count; i++) {
      pos.setZ(i, pos.getZ(i) * taperK(pos.getY(i)))
    }
    pos.needsUpdate = true
    // 收窄后侧围端盖已成双曲面：必须按位置焊接求平滑法线，否则逐面法线烧出三角破面
    smoothNormalsKeepHardEdges(geom)
  }
  applyGreenhouseTaper(bodyGeom)

  // 开门状态：门洞四壁横贯整车宽度（holes 沿 Z 通透），整片车身色在门洞里外露。
  // 把洞壁三角形改判为内饰材质组，|z| ≥ 外蒙皮端面处的倒角环带仍保留车身色作门框唇边。
  let bodyMats = bodyMat
  if (doorAperture) {
    splitDoorApertureInterior(bodyGeom, doorAperture, bodyDepth / 2 - bodyThickness)
    bodyMats = [bodyMat, interiorMat]
  }

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

  // ---- 座舱玻璃划分（与 2D Car2D windowPath 同源锚点：玻璃与车身两种状态） ----
  // 前后风挡贴合拉伸体侧壁（壁面被 bevel 外扩 bodyThickness），侧窗贴合端盖外缘；
  // 玻璃统一用独立透明材质与车身漆面区分；B 柱在 55% 分段处保留车身色立柱（与 2D pillarX 同源）
  // 汽车玻璃写实材质：深色灰绿 tint（真车侧窗透光率 70% 级视觉），零环境反射——
  // 杜绝浅蓝镜面化与风挡斜面 RoomEnvironment 菲涅尔发白（envMapIntensity=0）；
  // 深色低透同时遮蔽对侧门缝黑条（移除透见的不合理门缝）。
  const glassMat = new THREE.MeshPhysicalMaterial({
    color: 0x212c30,
    transparent: true,
    opacity: 0.70,
    metalness: 0,
    roughness: 0.50,
    envMapIntensity: 0.0,
    side: THREE.DoubleSide,
    wireframe: wireframeMode.value
  })

  // 斜面玻璃带：脊柱线由 carGlass.bandGlassSpine 生成（可单测）——含车顶 G1 圆角包裹
  // 采样与顶面搭接，玻璃随车身同一圆角弯曲。
  // 偏移量 = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP：ExtrudeGeometry 的 bevel 会把整个侧壁
  // 沿 X-Y 外扩 bevelSize(=BODY_BEVEL_SIZE)，车身真实壁面因此在原始轮廓外该尺寸；
  // 玻璃必须骑在这层外扩壁面上，再留贴面间隙避免共面 z-fighting。
  // minOffsetRatio=1：全程保持同一偏移——旧实现让法线转向车顶时偏移渐减到 0，
  // 玻璃在 A 柱顶/C 柱顶瞬间沉入车身 30mm，肉眼即 COWL/车顶前缘的台阶折痕。
  const GLASS_GAP = BODY_BEVEL_SIZE + GLASS_SURFACE_GAP
  const addBandGlass = (x1, y1, x2, y2, width, topInset = 0, bottomInset = 0, fillet = null) => {
    const spine = bandGlassSpine(x1, y1, x2, y2, {
      topInset, bottomInset, offset: GLASS_GAP, minOffsetRatio: 1, fillet
    })
    const hw = width / 2
    const verts = []
    for (let i = 0; i < spine.length - 1; i++) {
      const [ax, ay] = spine[i]
      const [bx, by] = spine[i + 1]
      const az = hw * taperK(ay)
      const bz = hw * taperK(by)
      verts.push(ax, ay, -az, ax, ay, az, bx, by, -bz)
      verts.push(ax, ay, az, bx, by, bz, bx, by, -bz)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3))
    g.computeVertexNormals()
    const m = new THREE.Mesh(g, glassMat)
    m.userData.noCastShadow = true
    group.add(m)
  }

  // 车顶 G1 圆角集（与车身轮廓同一真源 roofFilletSet）：风挡顶/车顶后缘玻璃包裹用
  const roofFillets = roofFilletSet(P, props.carType, ROOF_FILLETS)

  // 前风挡：底缘 = COWL（bottomInset 下退避开 bevel 外扩角），顶缘包裹 A柱顶圆角并搭上车顶
  const ws = cabin.windshield
  addBandGlass(ws.x1, ws.y1, ws.x2, ws.y2, ws.width, ws.topInset, ws.bottomInset, roofFillets.front)
  // 后风挡：顶缘包裹车顶后缘圆角（rear 圆角 a/b 与行进方向相反 → 交换传入）；
  // 底缘下退 cPillarBottom 至 C 柱底圆角切点（玻璃不戳入尾部圆角，皮卡无后风挡）
  if (cabin.rearWindow) {
    const rw = cabin.rearWindow
    const rf = roofFillets.rear
    const rearFillet = rf ? { a: rf.b, ctrl: rf.ctrl, b: rf.a } : null
    addBandGlass(rw.x1, rw.y1, rw.x2, rw.y2, rw.width, rw.topInset, ROOF_FILLETS.cPillarBottom, rearFillet)
  }

  // 侧窗 DLO（左右各分片）：多边形与 2D windowPath 逐点同源，顶部两角内收避开 G1 圆角；
  // Z 轮廓 = tumblehome 线性内收 + barrel 桶面圆弧鼓肚（dloZAt 纯函数，可单测）。
  // 面片沿高度细分成条带网格——四角面片无法表达桶面曲率
  // 侧窗按车门分缝切成 4 片/侧：A 柱前固定片 + 前门片 + 后门片 + C 柱后固定片。
  // 门片挂到对应车门铰链 Group（与门板同轴同角度），开门时玻璃随门一同外摆；
  // 分缝两侧各留半个缝宽间隙 → 玻璃上同样能看到门缝（与 2D 分缝线同坐标）。
  const DLO_ROWS = 16
  const paneRanges = deriveDloPaneRanges(dl, props.carParams?.door_seam_width ?? 8)
  const doorGlass = []
  const addDloPane = (xFront, xRear, zSide, hingeKey) => {
    const positions = buildDloStripRange(cabin.dlo, dloFrame, DLO_ROWS, zSide, xFront, xRear)
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
    g.computeVertexNormals()
    const panel = new THREE.Mesh(g, glassMat)
    panel.userData.noCastShadow = true
    if (hingeKey) doorGlass.push({ key: hingeKey, zSide, mesh: panel })
    else group.add(panel)
  }
  for (const zSide of [1, -1]) {
    // 分片边界与门缝坐标全部来自 carGlass.deriveDloPaneRanges（纯函数，可单测）：
    // A 柱前固定片 / 前门片 / 后门片（双门与皮卡无此片）/ C 柱后固定片
    for (const pane of paneRanges) {
      addDloPane(pane.xFront, pane.xRear, zSide, pane.hingeKey)
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
  const liftLayout = deriveLiftDevices(P, resolveFlightParams(props.carType, props.carParams).liftFans)
  const ductMat = new THREE.MeshStandardMaterial({
    color: 0x14161c, metalness: 0.6, roughness: 0.4, wireframe: wireframeMode.value
  })
  const lipMat = new THREE.MeshStandardMaterial({
    color: 0xb8bcc4, metalness: 1.0, roughness: 0.15, wireframe: wireframeMode.value
  })
  for (const d of liftLayout.devices) {
    const duct = new THREE.Mesh(new THREE.CylinderGeometry(d.r, d.r * 1.04, 0.02, 28), ductMat)
    duct.position.set(d.x, liftLayout.y, d.z)
    duct.userData.noCastShadow = true
    group.add(duct)
    const lip = new THREE.Mesh(new THREE.TorusGeometry(d.r * 0.99, 0.009, 8, 28), lipMat)
    lip.rotation.x = Math.PI / 2
    lip.position.set(d.x, liftLayout.y - 0.01, d.z)
    lip.userData.noCastShadow = true
    group.add(lip)
  }

  const createWheel = (x, z) => {
    const wheelGroup = new THREE.Group()
    
    const tireWidth = fit.tireW
    const tireGeom = new THREE.CylinderGeometry(wheelR, wheelR, tireWidth, 24)
    tireGeom.rotateX(Math.PI / 2)
    const tire = new THREE.Mesh(tireGeom, wheelMat)
    wheelGroup.add(tire)

    const rimGeom = new THREE.CylinderGeometry(wheelR * 0.6, wheelR * 0.6, tireWidth * 0.9, 12)
    rimGeom.rotateX(Math.PI / 2)
    const rim = new THREE.Mesh(rimGeom, rimMat)
    wheelGroup.add(rim)

    const hubGeom = new THREE.CylinderGeometry(wheelR * 0.2, wheelR * 0.2, tireWidth * 0.95, 8)
    hubGeom.rotateX(Math.PI / 2)
    const hub = new THREE.Mesh(hubGeom, chromeMat)
    wheelGroup.add(hub)

    for (let i = 0; i < 5; i++) {
      const spokeGeom = new THREE.BoxGeometry(wheelR * 0.5, 0.04, 0.06)
      const spoke = new THREE.Mesh(spokeGeom, rimMat)
      spoke.rotation.x = (i * Math.PI * 2) / 5
      wheelGroup.add(spoke)
    }

    wheelGroup.position.set(x, wheelR, z)
    return wheelGroup
  }

  const wheelZ = fit.wheelZ

  group.add(createWheel(frontWheelX, wheelZ))
  group.add(createWheel(frontWheelX, -wheelZ))
  group.add(createWheel(rearWheelX, wheelZ))
  group.add(createWheel(rearWheelX, -wheelZ))

  // ---- 轮腔内衬：与拱口同形的内嵌椭圆拱壳（半椭圆上缘 + 竖直唇落至底板）----
  // 圆形筒对椭圆拱口必然四周互穿（前后壁/顶部戳出 = 拓扑破面），改用 archLinerProfile
  // 纯函数生成的拱形开壳，整体内缩 12mm 严格位于空腔内，横跨全宽挡住对侧亮色 bevel
  const linerMat = new THREE.MeshStandardMaterial({
    color: 0x101014, metalness: 0.2, roughness: 0.95, side: THREE.DoubleSide,
    wireframe: wireframeMode.value
  })
  const addArchLiner = (side) => {
    const prof = archLinerProfile(P, side, 0.012)
    const L = bodyExtentZ
    const positions = []
    for (const [x, y] of prof) positions.push(x, y, -L, x, y, L)
    const indices = []
    for (let i = 0; i < prof.length - 1; i++) {
      const a = i * 2, b = i * 2 + 1, c = (i + 1) * 2, d = (i + 1) * 2 + 1
      indices.push(a, b, c, b, d, c)
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
    g.setIndex(indices)
    g.computeVertexNormals()
    const liner = new THREE.Mesh(g, linerMat)
    liner.receiveShadow = true
    group.add(liner)
  }
  addArchLiner('front')
  addArchLiner('rear')

  const steeringWheelGroup = new THREE.Group()
  const swRadius = 0.15
  const swGeom = new THREE.TorusGeometry(swRadius, 0.012, 16, 32)
  const swMesh = new THREE.Mesh(swGeom, chromeMat)
  swMesh.rotation.x = Math.PI / 2
  steeringWheelGroup.add(swMesh)

  const swSpoke1 = new THREE.Mesh(new THREE.BoxGeometry(0.008, swRadius * 1.8, 0.008), chromeMat)
  steeringWheelGroup.add(swSpoke1)
  const swSpoke2 = new THREE.Mesh(new THREE.BoxGeometry(0.008, swRadius * 1.8, 0.008), chromeMat)
  swSpoke2.rotation.z = Math.PI / 3
  steeringWheelGroup.add(swSpoke2)
  const swSpoke3 = new THREE.Mesh(new THREE.BoxGeometry(0.008, swRadius * 1.8, 0.008), chromeMat)
  swSpoke3.rotation.z = -Math.PI / 3
  steeringWheelGroup.add(swSpoke3)

  const steeringColumnGeom = new THREE.CylinderGeometry(0.015, 0.015, 0.15, 8)
  const steeringColumn = new THREE.Mesh(steeringColumnGeom, chromeMat)
  steeringColumn.position.set(0, -swRadius - 0.075, 0)
  steeringWheelGroup.add(steeringColumn)

  const steeringWheelX = (windshieldTopX + hoodEndX) / 2
  const steeringWheelY = beltLineY - 0.1
  const steeringWheelZ = -halfTrack + 0.08
  steeringWheelGroup.position.set(steeringWheelX, steeringWheelY, steeringWheelZ)
  group.add(steeringWheelGroup)

  // ---- 保险杠：贴前/后立面外表面（旧值埋在车身实体内不可见，已修正）----
  const bumperGeom = new THREE.BoxGeometry(0.05, 0.15, W - 0.10)
  const frontBumper = new THREE.Mesh(bumperGeom, bodyMat)
  frontBumper.position.set(frontX + 0.005, bodyBottomY + 0.075, 0)
  group.add(frontBumper)

  const rearBumper = new THREE.Mesh(bumperGeom, bodyMat)
  rearBumper.position.set(rearX - 0.005, bodyBottomY + 0.075, 0)
  group.add(rearBumper)

  // ---- 接近角/离去角构造线：接地点→车身立面底角（坡面 cornerY 由可调角度驱动）的琥珀色布置线 ----
  const angleLineMat = new THREE.LineBasicMaterial({ color: 0xfbbf24 })
  for (const zSide of [1, -1]) {
    const zz = zSide * (fit.wall + 0.006)
    group.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(frontWheelX, 0, zz), new THREE.Vector3(frontX, P.ramps.front.cornerY, zz)]),
      angleLineMat))
    group.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(rearWheelX, 0, zz), new THREE.Vector3(rearX, P.ramps.rear.cornerY, zz)]),
      angleLineMat))
  }

  // ---- 前大灯：嵌于前立面（旧值 z=halfTrack-0.15 深埋车体内部，不可见）----
  const headlightMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xffffcc,
    emissiveIntensity: 0.5,
    wireframe: wireframeMode.value
  })
  const headlightGeom = new THREE.BoxGeometry(0.05, 0.10, 0.22)
  const hlY = Math.max(hoodLineY - 0.16, bodyBottomY + 0.16)
  const hlZ = fit.wall - 0.18
  const hl1 = new THREE.Mesh(headlightGeom, headlightMat)
  hl1.position.set(frontX, hlY, hlZ)
  group.add(hl1)
  const hl2 = new THREE.Mesh(headlightGeom, headlightMat)
  hl2.position.set(frontX, hlY, -hlZ)
  group.add(hl2)

  // ---- 尾灯：嵌于后立面（与大灯同口径修正）----
  const taillightMat = new THREE.MeshStandardMaterial({
    color: 0xff0000,
    emissive: 0xff0000,
    emissiveIntensity: 0.4,
    wireframe: wireframeMode.value
  })
  const taillightGeom = new THREE.BoxGeometry(0.04, 0.10, 0.20)
  const tlY = Math.max(trunkLineY - 0.18, bodyBottomY + 0.16)
  const tl1 = new THREE.Mesh(taillightGeom, taillightMat)
  tl1.position.set(rearX, tlY, hlZ)
  group.add(tl1)
  const tl2 = new THREE.Mesh(taillightGeom, taillightMat)
  tl2.position.set(rearX, tlY, -hlZ)
  group.add(tl2)

  // ---- 车门分缝线 + 门板（可绕前铰链打开）+ 门把手（随门板运动）----
  // 分缝线：前缝/B柱缝/后缝 竖向暗色薄槽（sill→腰带线）；门板：贴侧壁的薄面板挂到铰链 Group，
  // animate() 按 door_open_angle 缓动 rotation.y 开合，把手 parent 到对应门板随动。
  const seamMat = new THREE.MeshStandardMaterial({ color: 0x08080c, metalness: 0.3, roughness: 0.8, wireframe: wireframeMode.value })
  const doorMat = new THREE.MeshStandardMaterial({ color: bodyColor, metalness: 0.6, roughness: 0.28, wireframe: wireframeMode.value })
  const handleGeom = new THREE.BoxGeometry(0.14, 0.022, 0.02)
  const doorBottom = bodyBottomY + 0.02
  const doorTop = beltLineY - 0.004
  const doorH = doorTop - doorBottom
  const seamW = (props.carParams?.door_seam_width ?? 8) / 1000
  doorHinges = []
  const addSeam = (x) => {
    for (const zSide of [1, -1]) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(seamW, doorH, 0.004), seamMat)
      s.position.set(x, doorBottom + doorH / 2, zSide * (fit.wall + 0.002))
      group.add(s)
    }
  }
  addSeam(dl.frontSeamX); addSeam(dl.midSeamX)
  if (dl.rearSeamX !== null) addSeam(dl.rearSeamX)
  // 门板 + 铰链（常规前铰：前门铰链在前缝、后门铰链在 B柱缝，均向后开）
  const mkDoor = (key, hingeX, leadX, trailX, handleX, zSide) => {
    const hinge = new THREE.Group()
    hinge.position.set(hingeX, 0, zSide * fit.wall)
    const w = Math.max(Math.abs(trailX - leadX) - seamW, 0.05)   // X+ 朝车头：leading 边 X 更大，取绝对宽
    const panel = new THREE.Mesh(new THREE.BoxGeometry(w, doorH, 0.012), doorMat)
    panel.position.set((leadX + trailX) / 2 - hingeX, doorBottom + doorH / 2, zSide * 0.006)
    panel.castShadow = true
    hinge.add(panel)
    const h = new THREE.Mesh(handleGeom, chromeMat)
    h.position.set(handleX - hingeX, dl.handleY, zSide * 0.016)
    hinge.add(h)
    group.add(hinge)
    doorHinges.push({ hinge, sign: zSide, key })
  }
  for (const zSide of [1, -1]) {
    mkDoor('front', dl.frontSeamX, dl.frontSeamX, dl.midSeamX, dl.frontHandleX, zSide)
    if (dl.rearSeamX !== null) mkDoor('rear', dl.midSeamX, dl.midSeamX, dl.rearSeamX, dl.rearHandleX, zSide)
  }
  // 侧窗门片挂到对应车门铰链：几何按铰链轴平移（几何原为世界坐标），
  // 之后与门板同轴同角度旋转 → 玻璃随门一同打开、与门板上下沿严格对齐
  for (const dg of doorGlass) {
    const target = doorHinges.find((d) => d.key === dg.key && d.sign === dg.zSide)
    if (!target) continue
    dg.mesh.geometry.translate(-target.hinge.position.x, 0, -target.hinge.position.z)
    target.hinge.add(dg.mesh)
  }

  const createMirror = (zSide) => {
    const mirrorGroup = new THREE.Group()

    // 后视镜安装在 A 柱根部（发动机舱线高度），与车顶保持明确间距，
    // 避免任何视角下镜壳与车顶视觉重叠而成为"杂乱物"
    const armLength = 0.08
    const armGeom = new THREE.CylinderGeometry(0.015, 0.02, armLength, 8)
    armGeom.rotateX(Math.PI / 2)
    const arm = new THREE.Mesh(armGeom, bodyMat)
    arm.position.set(0, 0, zSide * (bodyExtentZ + armLength / 2))
    mirrorGroup.add(arm)

    // 镜壳：宽度沿车长、深度沿 Z 向外凸出，呈真实后视镜形态（非薄片状）
    const housingDepth = 0.11
    const housingGeom = new THREE.BoxGeometry(0.16, 0.09, housingDepth)
    const housingZ = bodyExtentZ + armLength + housingDepth / 2
    const housing = new THREE.Mesh(housingGeom, bodyMat)
    housing.position.set(0, 0.02, zSide * housingZ)
    mirrorGroup.add(housing)

    // 镜面：嵌入镜壳内侧，朝向驾驶员方向
    const mirrorFaceGeom = new THREE.PlaneGeometry(0.13, 0.07)
    const mirrorFace = new THREE.Mesh(mirrorFaceGeom, chromeMat)
    mirrorFace.position.set(-0.05, 0.02, zSide * (housingZ - 0.006))
    mirrorFace.rotation.y = -Math.PI / 2
    mirrorGroup.add(mirrorFace)

    // 安装点：A 柱根部、发动机舱肩部（紧贴车身侧面，不悬空、不挤车顶）
    mirrorGroup.position.set(
      hoodEndX + 0.02,
      hoodLineY + 0.03,
      0
    )
    return mirrorGroup
  }

  group.add(createMirror(1))
  group.add(createMirror(-1))

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

  return group
}

const initScene = () => {
  const container = containerRef.value
  if (!container) return
  
  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0a0f)
  // 调试/验收钩子：暴露场景供浏览器端几何校验（只读引用，不影响渲染）。
  // Designer 同页挂载多个 Car3D 实例（基础模型/实时预览），单一 __THREE_SCENE__
  // 会被后挂载实例覆盖导致采错场景；__CAR3D_SCENES__ 数组注册全部存活实例，
  // userData 标记视口特征（wireframe/nurbs）供采样端定位正确实例。
  scene.userData.__car3d__ = { wireframe: wireframeMode.value, nurbs: !!props.nurbsMesh }
  if (typeof window !== 'undefined') {
    const reg = (window.__CAR3D_SCENES__ = window.__CAR3D_SCENES__ || [])
    reg.push(scene)
    window.__THREE_SCENE__ = scene
  }

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
  camera.position.set(6, 3, 6)
  camera.lookAt(0, 1, 0)

  const aspect = width / height
  const d = 5
  orthoCamera = new THREE.OrthographicCamera(-d * aspect, d * aspect, d, -d, 0.1, 100)
  orthoCamera.position.set(6, 3, 6)
  orthoCamera.lookAt(0, 1, 0)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0
  container.appendChild(renderer.domElement)

  // PBR 环境反射：RoomEnvironment 经 PMREM 预处理，供车漆/金属反射
  // （three 内置，无外部 hdr 资源依赖）
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  pmrem.dispose()

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.35)
  scene.add(ambientLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.0)
  mainLight.position.set(8, 12, 8)
  mainLight.castShadow = true
  mainLight.shadow.mapSize.width = 2048
  mainLight.shadow.mapSize.height = 2048
  mainLight.shadow.camera.near = 0.5
  mainLight.shadow.camera.far = 50
  mainLight.shadow.camera.left = -10
  mainLight.shadow.camera.right = 10
  mainLight.shadow.camera.top = 10
  mainLight.shadow.camera.bottom = -10
  scene.add(mainLight)

  const fillLight = new THREE.DirectionalLight(0x88aaff, 0.3)
  fillLight.position.set(-6, 4, -6)
  scene.add(fillLight)

  const rimLight = new THREE.DirectionalLight(0xffddaa, 0.25)
  rimLight.position.set(0, 6, -10)
  scene.add(rimLight)

  const groundMat = new THREE.MeshStandardMaterial({
    color: 0x0f0f18,
    metalness: 0.1,
    roughness: 0.9
  })
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  const gridHelper = new THREE.GridHelper(20, 20, 0x1e1e2e, 0x15151f)
  gridHelper.position.y = 0.01
  scene.add(gridHelper)

  carGroup = createCar()
  carGroup.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = !child.userData.noCastShadow   // 玻璃不投实心影
      child.receiveShadow = true
    }
  })
  scene.add(carGroup)

  container.addEventListener('mousedown', onMouseDown)
  container.addEventListener('mousemove', onMouseMove)
  container.addEventListener('mouseup', onMouseUp)
  container.addEventListener('mouseleave', onMouseUp)
  container.addEventListener('wheel', onWheel)
  container.addEventListener('contextmenu', (e) => e.preventDefault())
  window.addEventListener('resize', onWindowResize)

  animate()
}

const onMouseDown = (e) => {
  isDragging = true
  previousMousePosition = { x: e.clientX, y: e.clientY }
}

const onMouseMove = (e) => {
  if (!isDragging) return
  const dx = e.clientX - previousMousePosition.x
  const dy = e.clientY - previousMousePosition.y
  previousMousePosition = { x: e.clientX, y: e.clientY }

  if (e.button === 2) {
    targetPan.x -= dx * 0.01
    targetPan.y += dy * 0.01
    targetPan.x = Math.max(-3, Math.min(3, targetPan.x))
    targetPan.y = Math.max(-2, Math.min(2, targetPan.y))
  } else if (e.button === 0) {
    targetRotation.y += dx * 0.01
    targetRotation.x += dy * 0.008
    targetRotation.x = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, targetRotation.x))
  }
}

const onMouseUp = () => { isDragging = false }

const onWheel = (e) => {
  e.preventDefault()
  targetDistance += e.deltaY * 0.008
  targetDistance = Math.max(3, Math.min(20, targetDistance))
}

const onWindowResize = () => {
  const container = containerRef.value
  if (!container || !renderer) return
  const w = container.clientWidth
  const h = container.clientHeight
  
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  
  const aspect = w / h
  const d = 5
  orthoCamera.left = -d * aspect
  orthoCamera.right = d * aspect
  orthoCamera.top = d
  orthoCamera.bottom = -d
  orthoCamera.updateProjectionMatrix()
  
  renderer.setSize(w, h)
}

// ---- VTOL 特效：升力风扇环（随车）+ 地面能量场（贴地衰减）----
const disposeFlightFx = () => {
  if (flightGroundGlow) {
    scene.remove(flightGroundGlow)
    disposeObject(flightGroundGlow)
    flightGroundGlow = null
  }
  flightRings = []   // 环为 carGroup 子对象，随 carGroup 一起被 dispose
}

const ensureFlightFx = () => {
  if (!scene || !carGroup || flightRings.length) return
  const fp = resolveFlightParams(props.carType, props.carParams)
  const P = deriveCarProfile(props.carParams, props.carType)
  const ringMat = () => new THREE.MeshBasicMaterial({
    color: 0x38bdf8, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false
  })
  // 升力环与底盘上升装置同坐标（装置本体在 createCar 中常显，环仅飞行时可见）
  const lift = deriveLiftDevices(P, fp.liftFans)
  for (const d of lift.devices) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(d.r * 0.86, 0.016, 10, 40), ringMat())
    ring.rotation.x = Math.PI / 2
    ring.position.set(d.x, lift.y - 0.03, d.z)
    ring.userData.noCastShadow = true
    ring.visible = false
    carGroup.add(ring)
    flightRings.push(ring)
  }
  // 地面能量场：半径随车长缩放，绿色翡翠（品牌主色），悬浮越高越弱
  const glowR = Math.max(2.0, (props.carParams.overall_length || 4800) / 1000 * 0.42)
  const glowGeo = new THREE.CircleGeometry(glowR, 48)
  flightGroundGlow = new THREE.Mesh(glowGeo, new THREE.MeshBasicMaterial({
    color: 0x10b981, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false
  }))
  flightGroundGlow.rotation.x = -Math.PI / 2
  flightGroundGlow.position.y = 0.02
  flightGroundGlow.visible = false
  scene.add(flightGroundGlow)
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
    const pulse = 0.5 + 0.5 * Math.sin(vnow / 1000 * Math.PI * 2 * 0.8)
    const ringOn = flightProgress > 0.001
    for (const r of flightRings) {
      r.visible = ringOn
      r.material.opacity = ringOn ? 0.55 * (0.35 + 0.65 * pulse) * (0.3 + 0.7 * lift) : 0
      const s = 1 + 0.10 * pulse
      r.scale.set(s, s, 1)
    }
    if (flightGroundGlow) {
      flightGroundGlow.visible = ringOn
      flightGroundGlow.material.opacity = ringOn
        ? 0.22 * (1 - 0.72 * lift) * (0.4 + 0.6 * pulse) : 0
      const gs = 1 + 0.35 * (1 - lift)
      flightGroundGlow.scale.set(gs, gs, 1)
    }
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
  updateCar()
}

const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
}

const toggleFullscreen = () => {
  const container = containerRef.value
  if (!container) return
  if (!document.fullscreenElement) {
    container.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const disposeObject = (obj) => {
  if (!obj) return
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach(m => m.dispose())
      } else {
        child.material.dispose()
      }
    }
  })
  if (obj.geometry) obj.geometry.dispose()
  if (obj.material) {
    if (Array.isArray(obj.material)) {
      obj.material.forEach(m => m.dispose())
    } else {
      obj.material.dispose()
    }
  }
}

const updateCar = () => {
  if (!scene || !carGroup) return
  scene.remove(carGroup)
  disposeFlightFx()
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
  const container = containerRef.value
  if (container && renderer) {
    container.removeEventListener('mousedown', onMouseDown)
    container.removeEventListener('mousemove', onMouseMove)
    container.removeEventListener('mouseup', onMouseUp)
    container.removeEventListener('mouseleave', onMouseUp)
    container.removeEventListener('wheel', onWheel)
    window.removeEventListener('resize', onWindowResize)
  }
  disposeObject(carGroup)
  if (typeof window !== 'undefined' && Array.isArray(window.__CAR3D_SCENES__)) {
    const idx = window.__CAR3D_SCENES__.indexOf(scene)
    if (idx >= 0) window.__CAR3D_SCENES__.splice(idx, 1)
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
