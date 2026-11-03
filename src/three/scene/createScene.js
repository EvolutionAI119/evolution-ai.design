import * as THREE from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'

/**
 * 场景基座（P3 拆分：原 Car3D.vue initScene 的渲染器/相机/灯光/环境段）
 *
 * 只搬实现、不增删调试钩子字段，渲染参数逐字保留：
 * - 透视相机 45° / near 0.1 / far 100；正交相机半视口高 5、aspect 展开；
 * - WebGLRenderer antialias + alpha，阴影 PCFSoft，ACES 色调映射，曝光 1.0；
 * - RoomEnvironment 发光板颜色乘 0.04（压掠射角白带），PMREM 0.04 粗糙度；
 * - 环境光 0.35 / 主光 1.0（阴影相机 near0.5 far50 ±10）/ 补光 0x88aaff 0.3 / 轮拱光 0xffddaa 0.25。
 *
 * 调试钩子契约（采集端依赖，签名与字段冻结）：
 * `scene.userData.__car3d__ = { wireframe, nurbs, setViewInstant, setCameraPose, ... }`
 * —— 本模块只负责创建对象与两个与机位相关的函数；`setDoor` / `viewState` 依赖车门
 * 铰链与动画状态，仍由组件在 createCar 之后补挂（挂载时机不变）。
 *
 * @param {object} opts
 * @param {HTMLElement} opts.container 渲染画布挂载点（同时用于取宽高）
 * @param {boolean} opts.wireframe 线框态标记（供多实例采样端定位）
 * @param {boolean} opts.nurbs NURBS 态标记（供多实例采样端定位）
 * @param {object} opts.viewControls 机位状态访问器（组件提供）：
 *   { applyPreset(key), snap(), setTargets(pose), setOrtho(bool) }
 */
export function createScene({ container, wireframe = false, nurbs = false, viewControls }) {
  const width = container.clientWidth
  const height = container.clientHeight

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0a0f)
  // 调试/验收钩子：暴露场景供浏览器端几何校验（只读引用，不影响渲染）。
  // Designer 同页挂载多个 Car3D 实例（基础模型/实时预览），单一 __THREE_SCENE__
  // 会被后挂载实例覆盖导致采错场景；__CAR3D_SCENES__ 数组注册全部存活实例，
  // userData 标记视口特征（wireframe/nurbs）供采样端定位正确实例。
  scene.userData.__car3d__ = { wireframe, nurbs }
  if (typeof window !== 'undefined') {
    const reg = (window.__CAR3D_SCENES__ = window.__CAR3D_SCENES__ || [])
    reg.push(scene)
    window.__THREE_SCENE__ = scene
  }

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
  camera.position.set(6, 3, 6)
  camera.lookAt(0, 1, 0)

  const aspect = width / height
  const d = 5
  const orthoCamera = new THREE.OrthographicCamera(-d * aspect, d * aspect, d, -d, 0.1, 100)
  orthoCamera.position.set(6, 3, 6)
  orthoCamera.lookAt(0, 1, 0)

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.0
  container.appendChild(renderer.domElement)

  // PBR 环境反射：RoomEnvironment 经 PMREM 预处理，供车漆/金属反射。
  // 默认发光板辐射值高达 17~100，近水平机盖/尾盖在掠射角会整片反成白带；
  // 只降低发光板的镜面反射能量，保留室内漫反射与直接光，不改动车身法线。
  const studio = new RoomEnvironment()
  studio.traverse((object) => {
    if (object.isMesh && object.material?.isMeshBasicMaterial) {
      object.material.color.multiplyScalar(0.04)
    }
  })
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(studio, 0.04).texture
  studio.dispose()
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

  // 瞬时定位到预设机位：相机缓动依赖帧数，截图采集需与帧率解耦
  const setViewInstant = (key) => {
    viewControls.applyPreset(key)
    viewControls.snap()
  }
  // 任意机位瞬时定位（cockpit 等非预设机位）：同样与帧率/缓动解耦，仅采集端使用
  const setCameraPose = (pose = {}) => {
    viewControls.setTargets(pose)
    viewControls.setOrtho(!!pose.ortho)
    viewControls.snap()
  }
  scene.userData.__car3d__.setViewInstant = setViewInstant
  scene.userData.__car3d__.setCameraPose = setCameraPose

  return { scene, camera, renderer, orthoCamera, setViewInstant, setCameraPose }
}
