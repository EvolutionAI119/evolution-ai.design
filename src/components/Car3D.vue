<template>
  <div ref="containerRef" class="car-3d-container">
    <div class="view-controls">
      <div
        v-for="view in viewAngles"
        :key="view.key"
        class="view-btn"
        :class="{ active: currentView === view.key }"
        @click="setViewAngle(view.key)"
        :title="view.label"
      >
        {{ view.icon }}
      </div>
    </div>
    <div class="control-buttons">
      <div class="ctrl-btn" @click="resetView" title="重置">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleWireframe" :class="{ active: wireframeMode }" title="线框">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18M9 3v18M3 15h18M15 3v18"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleAutoRotate" :class="{ active: autoRotate }" title="自动旋转">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleFullscreen" title="全屏">
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
import * as THREE from 'three'

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

const viewPresets = {
  front: { x: 0, y: 0, dist: 8, ortho: true },
  rear: { x: 0, y: Math.PI, dist: 8, ortho: true },
  left: { x: 0, y: -Math.PI / 2, dist: 8, ortho: true },
  right: { x: 0, y: Math.PI / 2, dist: 8, ortho: true },
  top: { x: Math.PI / 2, y: 0, dist: 10, ortho: true },
  bottom: { x: -Math.PI / 2, y: 0, dist: 10, ortho: true },
  isometric: { x: Math.PI / 4, y: Math.PI / 4, dist: 10, ortho: false },
  perspective: { x: 0.4, y: 0.8, dist: 8, ortho: false }
}

const createCar = () => {
  const group = new THREE.Group()
  
  const L = props.carParams.overall_length / 1000
  const W = props.carParams.overall_width / 1000
  const H = props.carParams.overall_height / 1000
  const WB = props.carParams.wheel_base / 1000
  const track = props.carParams.track_width / 1000
  const gc = props.carParams.ground_clearance / 1000
  const hoodLen = props.carParams.hood_length / 1000
  const wheelR = props.carParams.wheel_diameter / 2000
  const roofH = props.carParams.roof_height / 1000
  const wAngle = props.carParams.windshield_angle * Math.PI / 180
  const rAngle = props.carParams.rear_window_angle * Math.PI / 180

  const bodyColor = new THREE.Color(props.carColor)

  const bodyMat = new THREE.MeshStandardMaterial({
    color: bodyColor,
    metalness: 0.6,
    roughness: 0.25,
    wireframe: wireframeMode.value
  })

  const glassMat = new THREE.MeshStandardMaterial({
    color: 0x88ccff,
    metalness: 0.1,
    roughness: 0.05,
    transparent: true,
    opacity: 0.35,
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

  const frontWheelZ = WB / 2
  const rearWheelZ = -WB / 2
  const halfTrack = track / 2

  const bodyShape = new THREE.Shape()
  const frontZ = L / 2
  const rearZ = -L / 2
  const hoodEndZ = frontZ - hoodLen
  const trunkStartZ = rearZ + hoodLen * 0.6

  const windshieldHeight = roofH * 0.7
  const windshieldTopZ = hoodEndZ - windshieldHeight / Math.tan(wAngle)
  
  const rearWindowHeight = roofH * 0.65
  const rearWindowTopZ = trunkStartZ + rearWindowHeight / Math.tan(rAngle)

  const bodyBottomY = gc
  const bodyTopY = gc + H * 0.4
  const roofTopY = gc + H * 0.4 + roofH
  const beltLineY = gc + H * 0.55

  bodyShape.moveTo(frontZ, bodyBottomY)
  bodyShape.quadraticCurveTo(frontZ + 0.05, bodyTopY - 0.1, frontZ, bodyTopY)
  bodyShape.quadraticCurveTo(hoodEndZ - 0.1, beltLineY - 0.05, hoodEndZ, beltLineY)
  bodyShape.lineTo(windshieldTopZ, roofTopY)
  bodyShape.lineTo(rearWindowTopZ, roofTopY)
  bodyShape.quadraticCurveTo(trunkStartZ + 0.1, beltLineY + 0.05, trunkStartZ, beltLineY)
  bodyShape.quadraticCurveTo(rearZ + 0.05, bodyTopY - 0.15, rearZ, bodyBottomY + 0.05)
  bodyShape.lineTo(rearZ, bodyBottomY)
  bodyShape.closePath()

  const extrudeSettings = {
    depth: W,
    bevelEnabled: true,
    bevelThickness: 0.04,
    bevelSize: 0.04,
    bevelSegments: 3,
    curveSegments: 16
  }

  const bodyGeom = new THREE.ExtrudeGeometry(bodyShape, extrudeSettings)
  bodyGeom.translate(0, 0, -W / 2)
  bodyGeom.rotateY(0)
  bodyGeom.rotateZ(0)
  
  const tempGroup = new THREE.Group()
  const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat)
  bodyMesh.rotation.y = Math.PI / 2
  bodyMesh.rotation.x = 0
  tempGroup.add(bodyMesh)
  group.add(tempGroup)

  const roofLen = Math.abs(rearWindowTopZ - windshieldTopZ)
  const roofShape = new THREE.Shape()
  roofShape.moveTo(-roofLen / 2, 0)
  roofShape.quadraticCurveTo(0, -0.03, roofLen / 2, 0)
  roofShape.lineTo(roofLen / 2, 0.02)
  roofShape.lineTo(-roofLen / 2, 0.02)
  roofShape.closePath()

  const roofGeom = new THREE.ExtrudeGeometry(roofShape, {
    depth: W - 0.1,
    bevelEnabled: true,
    bevelThickness: 0.02,
    bevelSize: 0.02,
    bevelSegments: 2
  })
  const roofMesh = new THREE.Mesh(roofGeom, bodyMat)
  roofMesh.rotation.y = Math.PI / 2
  roofMesh.rotation.x = 0
  roofMesh.position.set(0, roofTopY + 0.01, (windshieldTopZ + rearWindowTopZ) / 2)
  group.add(roofMesh)

  const windowShape = new THREE.Shape()
  windowShape.moveTo(hoodEndZ, beltLineY)
  windowShape.lineTo(windshieldTopZ, roofTopY - 0.02)
  windowShape.lineTo(rearWindowTopZ, roofTopY - 0.02)
  windowShape.lineTo(trunkStartZ, beltLineY)
  windowShape.closePath()

  const windowGeom = new THREE.ExtrudeGeometry(windowShape, {
    depth: W - 0.15,
    bevelEnabled: false
  })
  const windowMesh = new THREE.Mesh(windowGeom, glassMat)
  windowMesh.rotation.y = Math.PI / 2
  windowMesh.position.set(0, 0, 0)
  group.add(windowMesh)

  const createWheel = (z, x) => {
    const wheelGroup = new THREE.Group()
    
    const tireGeom = new THREE.CylinderGeometry(wheelR, wheelR, 0.28, 24)
    tireGeom.rotateX(Math.PI / 2)
    const tire = new THREE.Mesh(tireGeom, wheelMat)
    wheelGroup.add(tire)

    const rimGeom = new THREE.CylinderGeometry(wheelR * 0.6, wheelR * 0.6, 0.25, 12)
    rimGeom.rotateX(Math.PI / 2)
    const rim = new THREE.Mesh(rimGeom, rimMat)
    wheelGroup.add(rim)

    const hubGeom = new THREE.CylinderGeometry(wheelR * 0.2, wheelR * 0.2, 0.26, 8)
    hubGeom.rotateX(Math.PI / 2)
    const hub = new THREE.Mesh(hubGeom, chromeMat)
    wheelGroup.add(hub)

    for (let i = 0; i < 5; i++) {
      const spokeGeom = new THREE.BoxGeometry(wheelR * 0.5, 0.04, 0.06)
      const spoke = new THREE.Mesh(spokeGeom, rimMat)
      spoke.rotation.y = (i * Math.PI * 2) / 5
      wheelGroup.add(spoke)
    }

    wheelGroup.position.set(x, gc + wheelR, z)
    return wheelGroup
  }

  group.add(createWheel(frontWheelZ, halfTrack))
  group.add(createWheel(frontWheelZ, -halfTrack))
  group.add(createWheel(rearWheelZ, halfTrack))
  group.add(createWheel(rearWheelZ, -halfTrack))

  const bumperGeom = new THREE.BoxGeometry(W - 0.1, 0.1, 0.08)
  const frontBumper = new THREE.Mesh(bumperGeom, chromeMat)
  frontBumper.position.set(0, gc + 0.15, L / 2 - 0.05)
  group.add(frontBumper)

  const rearBumper = new THREE.Mesh(bumperGeom, chromeMat)
  rearBumper.position.set(0, gc + 0.15, -L / 2 + 0.05)
  group.add(rearBumper)

  const headlightMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xffffcc,
    emissiveIntensity: 0.5,
    wireframe: wireframeMode.value
  })
  const headlightGeom = new THREE.BoxGeometry(0.15, 0.08, 0.06)
  const hl1 = new THREE.Mesh(headlightGeom, headlightMat)
  hl1.position.set(W / 2 - 0.15, gc + H * 0.35, L / 2 - 0.02)
  group.add(hl1)
  const hl2 = new THREE.Mesh(headlightGeom, headlightMat)
  hl2.position.set(-W / 2 + 0.15, gc + H * 0.35, L / 2 - 0.02)
  group.add(hl2)

  const taillightMat = new THREE.MeshStandardMaterial({
    color: 0xff0000,
    emissive: 0xff0000,
    emissiveIntensity: 0.4,
    wireframe: wireframeMode.value
  })
  const taillightGeom = new THREE.BoxGeometry(0.12, 0.1, 0.05)
  const tl1 = new THREE.Mesh(taillightGeom, taillightMat)
  tl1.position.set(W / 2 - 0.15, gc + H * 0.4, -L / 2 + 0.02)
  group.add(tl1)
  const tl2 = new THREE.Mesh(taillightGeom, taillightMat)
  tl2.position.set(-W / 2 + 0.15, gc + H * 0.4, -L / 2 + 0.02)
  group.add(tl2)

  const mirrorGeom = new THREE.BoxGeometry(0.12, 0.08, 0.15)
  const mirror1 = new THREE.Mesh(mirrorGeom, bodyMat)
  mirror1.position.set(W / 2 + 0.05, beltLineY + 0.1, hoodEndZ - 0.1)
  group.add(mirror1)
  const mirror2 = new THREE.Mesh(mirrorGeom, bodyMat)
  mirror2.position.set(-W / 2 - 0.05, beltLineY + 0.1, hoodEndZ - 0.1)
  group.add(mirror2)

  if (props.carType === 'sport') {
    const wingGeom = new THREE.BoxGeometry(W * 0.8, 0.04, 0.25)
    const wing = new THREE.Mesh(wingGeom, bodyMat)
    wing.position.set(0, roofTopY + 0.15, rearWindowTopZ + 0.1)
    group.add(wing)
    
    const wingSupportGeom = new THREE.BoxGeometry(0.03, 0.15, 0.03)
    const ws1 = new THREE.Mesh(wingSupportGeom, chromeMat)
    ws1.position.set(W * 0.25, roofTopY + 0.07, rearWindowTopZ + 0.1)
    group.add(ws1)
    const ws2 = new THREE.Mesh(wingSupportGeom, chromeMat)
    ws2.position.set(-W * 0.25, roofTopY + 0.07, rearWindowTopZ + 0.1)
    group.add(ws2)
  }

  if (props.carType === 'suv' || props.carType === 'mpv') {
    const railGeom = new THREE.BoxGeometry(0.04, 0.03, roofLen * 0.8)
    const rail1 = new THREE.Mesh(railGeom, chromeMat)
    rail1.position.set(W / 2 - 0.1, roofTopY + 0.02, (windshieldTopZ + rearWindowTopZ) / 2)
    group.add(rail1)
    const rail2 = new THREE.Mesh(railGeom, chromeMat)
    rail2.position.set(-W / 2 + 0.1, roofTopY + 0.02, (windshieldTopZ + rearWindowTopZ) / 2)
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
      child.castShadow = true
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

const updateCar = () => {
  if (!scene || !carGroup) return
  scene.remove(carGroup)
  carGroup = createCar()
  carGroup.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true
      child.receiveShadow = true
    }
  })
  scene.add(carGroup)
}

watch(
  () => [props.carParams, props.carType, props.carColor],
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
    renderer.dispose()
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
  background: #0a0a0f;
}

.view-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  z-index: 10;
  background: rgba(22, 22, 31, 0.85);
  backdrop-filter: blur(8px);
  padding: 6px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.view-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.5);
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
  background: rgba(22, 22, 31, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
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
  color: #4ade80;
  font-family: Inter, sans-serif;
  background: rgba(22, 22, 31, 0.85);
  backdrop-filter: blur(8px);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.status-item {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  font-family: Inter, sans-serif;
  letter-spacing: 0.5px;
}
</style>
