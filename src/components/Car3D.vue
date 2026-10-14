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
      <div class="ctrl-btn" @click="toggleFullscreen" :title="t('designer.viewerFullscreen')" :aria-label="t('designer.viewerFullscreen')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
        </svg>
      </div>
    </div>
    <div class="status-bar">
      <span class="view-label">{{ currentViewLabel }}</span>
      <span class="status-item">DAYLIGHT</span>
      <span class="status-item">PERSPECTIVE</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as THREE from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { deriveCarProfile, filletCorner } from '../utils/carProfile.js'
import { bandGlassEndpoints, deriveCabinGlass, dloZAt, pillarPlacement, buildDloFrame, buildDloStrip, greenhouseInsetAt } from '../utils/carGlass.js'

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
    wheelArchRadius, archY, pickup, rails: railSpec, wing: wingSpec
  } = P

  const bodyColor = new THREE.Color(props.carColor)

  const bodyMat = new THREE.MeshStandardMaterial({
    color: bodyColor,
    metalness: 0.6,
    roughness: 0.25,
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

  // ---- 侧围轮廓（与 2D Car2D.vue 同源锚点 + G1 圆角，杜绝折痕/曲率突变） ----
  // 尾部 / 底部过渡控制点与 2D 轮廓逐点镜像（20/16/56/26/36mm）
  const tailCtrlX = rearX + 0.02
  const tailCtrlY = trunkLineY - 0.016
  const tailEndY = trunkLineY - 0.056
  if (pickup) {
    // 皮卡拓扑：车顶止于驾驶室后壁 → 后壁斜落至货箱栏板 → 栏板贯通至尾门
    const cabBotX = pickup.cabWindowBottomX
    // A 柱顶 + 驾驶室后壁顶 + 后壁底三处 G1 圆角
    const f1 = filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, 0.09)
    const f2 = filletCorner(windshieldTopX, roofTopY, pickup.cabRearX, roofTopY, cabBotX, pickup.bedWallY, 0.05)
    const f3 = filletCorner(pickup.cabRearX, roofTopY, cabBotX, pickup.bedWallY, rearX - 0.024, pickup.bedWallY, 0.03)
    bodyShape.moveTo(frontX, bodyBottomY)
    bodyShape.quadraticCurveTo(frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
    bodyShape.lineTo(cowlStartX, hoodLineY)
    bodyShape.lineTo(hoodEndX, beltLineY)
    bodyShape.lineTo(f1.a[0], f1.a[1])
    bodyShape.quadraticCurveTo(f1.ctrl[0], f1.ctrl[1], f1.b[0], f1.b[1])
    bodyShape.lineTo(f2.a[0], f2.a[1])
    bodyShape.quadraticCurveTo(f2.ctrl[0], f2.ctrl[1], f2.b[0], f2.b[1])
    bodyShape.lineTo(f3.a[0], f3.a[1])
    bodyShape.quadraticCurveTo(f3.ctrl[0], f3.ctrl[1], f3.b[0], f3.b[1])
    bodyShape.lineTo(rearX - 0.024, pickup.bedWallY)
    bodyShape.quadraticCurveTo(rearX, pickup.bedWallY - 0.008, rearX, pickup.bedWallY - 0.048)
    bodyShape.lineTo(rearX, bodyBottomY + 0.026)
    bodyShape.quadraticCurveTo(rearX, bodyBottomY, rearX - 0.036, bodyBottomY)
  } else {
    // 三厢/两厢拓扑：车顶 → C 柱 → 尾部曲线（2D 同源：无平甲板硬折点）
    const f1 = filletCorner(hoodEndX, beltLineY, windshieldTopX, roofTopY, rearWindowTopX, roofTopY, 0.09)
    const f2 = filletCorner(windshieldTopX, roofTopY, rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, 0.09)
    const f3 = filletCorner(rearWindowTopX, roofTopY, rearWindowBottomX, beltLineY, tailCtrlX, tailCtrlY, 0.06)
    bodyShape.moveTo(frontX, bodyBottomY)
    bodyShape.quadraticCurveTo(frontX + 0.09, hoodLineY - 0.04, frontX + 0.02, hoodLineY)
    bodyShape.lineTo(cowlStartX, hoodLineY)
    bodyShape.lineTo(hoodEndX, beltLineY)
    bodyShape.lineTo(f1.a[0], f1.a[1])
    bodyShape.quadraticCurveTo(f1.ctrl[0], f1.ctrl[1], f1.b[0], f1.b[1])
    bodyShape.lineTo(f2.a[0], f2.a[1])
    bodyShape.quadraticCurveTo(f2.ctrl[0], f2.ctrl[1], f2.b[0], f2.b[1])
    bodyShape.lineTo(f3.a[0], f3.a[1])
    bodyShape.quadraticCurveTo(f3.ctrl[0], f3.ctrl[1], f3.b[0], f3.b[1])
    bodyShape.quadraticCurveTo(tailCtrlX, tailCtrlY, rearX, tailEndY)
    bodyShape.lineTo(rearX, bodyBottomY + 0.026)
    bodyShape.quadraticCurveTo(rearX, bodyBottomY, rearX - 0.036, bodyBottomY)
  }
  bodyShape.closePath()

  const frontArch = new THREE.Path()
  frontArch.moveTo(frontWheelX - wheelArchRadius, archY)
  frontArch.absarc(frontWheelX, archY, wheelArchRadius, Math.PI, 0)
  frontArch.lineTo(frontWheelX + wheelArchRadius, archY)
  frontArch.closePath()
  bodyShape.holes.push(frontArch)

  const rearArch = new THREE.Path()
  rearArch.moveTo(rearWheelX - wheelArchRadius, archY)
  rearArch.absarc(rearWheelX, archY, wheelArchRadius, Math.PI, 0)
  rearArch.lineTo(rearWheelX + wheelArchRadius, archY)
  rearArch.closePath()
  bodyShape.holes.push(rearArch)

  const bodyDepth = W
  const bodyThickness = 0.03
  const bodyExtentZ = (bodyDepth + bodyThickness * 2) / 2

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

  // 座舱玻璃划分（与 2D Car2D windowPath 同源锚点）；倾角/桶面参数先于车身变形计算，
  // 供车身 greenhouse 收窄与玻璃面板共用同一轮廓公式
  const cabin = deriveCabinGlass(P, {
    carType: props.carType,
    sideGlassAngle: props.carParams?.side_glass_angle,
    glassBarrelAngle: props.carParams?.glass_barrel_angle,
    glassBarrelRadius: props.carParams?.glass_barrel_radius
  })
  const dloFrame = buildDloFrame(cabin, bodyExtentZ + 0.002)

  // 车身 greenhouse 收窄：DLO 底边（腰带线）以上的侧壁/车顶按与 DLO 玻璃面同公式
  // 内收——A/B/C 柱剪影与车顶随玻璃角度/桶面联动，玻璃面始终位于车身外侧同间隙
  // （greenhouseInsetAt 纯函数，可单测；k 为按高度的比例因子，避免内部顶点越过中线）
  const taperK = (y) => Math.max(1 - greenhouseInsetAt(y, dloFrame) / bodyExtentZ, 0.35)
  const applyGreenhouseTaper = (geom) => {
    const pos = geom.attributes.position
    for (let i = 0; i < pos.count; i++) {
      pos.setZ(i, pos.getZ(i) * taperK(pos.getY(i)))
    }
    pos.needsUpdate = true
    geom.computeVertexNormals()
  }
  applyGreenhouseTaper(bodyGeom)

  const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat)
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
  const glassMat = new THREE.MeshPhysicalMaterial({
    color: 0x87ceeb,
    transparent: true,
    opacity: 0.5,
    metalness: 0,
    roughness: 0.06,
    envMapIntensity: 1.2,
    side: THREE.DoubleSide,
    wireframe: wireframeMode.value
  })

  // 斜面玻璃带：端点/法线/顶缘下退的计算在 utils/carGlass.js 纯函数中（可单测）；
  // Z 向随高度按 taperK 收窄（与车身 greenhouse 同公式），顶缘不越过收窄后的车身
  const addBandGlass = (x1, y1, x2, y2, width, topInset = 0) => {
    const { a, b } = bandGlassEndpoints(x1, y1, x2, y2, topInset, bodyThickness + 0.001)
    const hw = width / 2
    const raw = [
      a[0], a[1], -hw, a[0], a[1], hw, b[0], b[1], -hw,
      a[0], a[1], hw, b[0], b[1], hw, b[0], b[1], -hw
    ]
    const verts = []
    for (let i = 0; i < raw.length; i += 3) {
      verts.push(raw[i], raw[i + 1], raw[i + 2] * taperK(raw[i + 1]))
    }
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(verts), 3))
    g.computeVertexNormals()
    const m = new THREE.Mesh(g, glassMat)
    m.userData.noCastShadow = true
    group.add(m)
  }

  // 前风挡：底缘 = COWL，顶缘 = 车顶前缘（与 2D A 柱线同源）
  const ws = cabin.windshield
  addBandGlass(ws.x1, ws.y1, ws.x2, ws.y2, ws.width, ws.topInset)
  // 后风挡：顶缘 = 车顶后缘，底缘 = 行李箱前缘（皮卡驾驶室后壁为车身，无后风挡）
  if (cabin.rearWindow) {
    const rw = cabin.rearWindow
    addBandGlass(rw.x1, rw.y1, rw.x2, rw.y2, rw.width, rw.topInset)
  }

  // 侧窗 DLO（左右两片）：多边形与 2D windowPath 逐点同源，顶部两角内收避开 G1 圆角；
  // Z 轮廓 = tumblehome 线性内收 + barrel 桶面圆弧鼓肚（dloZAt 纯函数，可单测）。
  // 面片沿高度细分成条带网格——四角面片无法表达桶面曲率
  // （框架构建/条带顶点生成在 utils/carGlass.js buildDloFrame / buildDloStrip 纯函数中，可单测）
  const DLO_ROWS = 16
  for (const zSide of [1, -1]) {
    const positions = buildDloStrip(cabin.dlo, dloFrame, DLO_ROWS, zSide)
    const dloGeom = new THREE.BufferGeometry()
    dloGeom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3))
    dloGeom.computeVertexNormals()
    const panel = new THREE.Mesh(dloGeom, glassMat)
    panel.userData.noCastShadow = true
    group.add(panel)
  }

  // B 柱：55% 分段处车身色立柱（叠于玻璃之上，与 2D B 柱线同位置）；
  // 与侧窗共面同倾角：底部锚定该高度处的玻璃面，绕底旋转 tiltDeg（pillarPlacement 纯函数）
  const pp = pillarPlacement(cabin, dloFrame.dloYBot, dloFrame.dloYSpan, dloFrame.dloZBase)
  const pillarGeom = new THREE.BoxGeometry(0.022, pp.height, 0.008)
  pillarGeom.translate(0, pp.height / 2, 0)   // 底部置于原点，便于绕底倾斜
  for (const zSide of [1, -1]) {
    const pillar = new THREE.Mesh(pillarGeom, bodyMat)
    pillar.position.set(pp.x, pp.botY, zSide * pp.baseZ)
    pillar.rotation.x = -zSide * pp.tiltRad
    group.add(pillar)
  }

  const createWheel = (x, z) => {
    const wheelGroup = new THREE.Group()
    
    const tireWidth = 0.28
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

  const wheelZ = bodyExtentZ - 0.12

  group.add(createWheel(frontWheelX, wheelZ))
  group.add(createWheel(frontWheelX, -wheelZ))
  group.add(createWheel(rearWheelX, wheelZ))
  group.add(createWheel(rearWheelX, -wheelZ))

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

  const bumperGeom = new THREE.BoxGeometry(0.06, 0.12, W - 0.15)
  const frontBumper = new THREE.Mesh(bumperGeom, chromeMat)
  frontBumper.position.set(frontX - 0.03, gc + 0.08, 0)
  group.add(frontBumper)

  const rearBumper = new THREE.Mesh(bumperGeom, chromeMat)
  rearBumper.position.set(rearX + 0.03, gc + 0.08, 0)
  group.add(rearBumper)

  const headlightMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xffffcc,
    emissiveIntensity: 0.5,
    wireframe: wireframeMode.value
  })
  const headlightGeom = new THREE.BoxGeometry(0.15, 0.08, 0.06)
  const hl1 = new THREE.Mesh(headlightGeom, headlightMat)
  hl1.position.set(frontX - 0.02, gc + H * 0.35, halfTrack - 0.15)
  group.add(hl1)
  const hl2 = new THREE.Mesh(headlightGeom, headlightMat)
  hl2.position.set(frontX - 0.02, gc + H * 0.35, -halfTrack + 0.15)
  group.add(hl2)

  const taillightMat = new THREE.MeshStandardMaterial({
    color: 0xff0000,
    emissive: 0xff0000,
    emissiveIntensity: 0.4,
    wireframe: wireframeMode.value
  })
  const taillightGeom = new THREE.BoxGeometry(0.12, 0.1, 0.05)
  const tl1 = new THREE.Mesh(taillightGeom, taillightMat)
  tl1.position.set(rearX + 0.02, gc + H * 0.4, halfTrack - 0.15)
  group.add(tl1)
  const tl2 = new THREE.Mesh(taillightGeom, taillightMat)
  tl2.position.set(rearX + 0.02, gc + H * 0.4, -halfTrack + 0.15)
  group.add(tl2)

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

const animate = () => {
  animationId = requestAnimationFrame(animate)

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
