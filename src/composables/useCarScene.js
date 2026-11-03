import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { createScene } from '../three/scene/createScene.js'
import { attachInteractions } from '../three/scene/interactions.js'
import { createFlightFx } from '../three/scene/flightFx.js'
import { createAnimator } from '../three/scene/animator.js'
import { viewPresets, orthoViewportSize } from '../three/scene/viewPresets.js'
import { assembleCar } from '../three/assembly/assembleCar.js'
import { resolveFlightParams, flightControlEnvelope } from '../utils/flightPhysics.js'
import { disposeObject } from '../three/dispose.js'

/**
 * 场景编排 composable（P4 拆分）：接管 createCar / initScene / updateCar / 生命周期 / watch。
 * 组件侧只保留模板、props 与纯 UI 状态（isFullscreen / toggleFullscreen）。
 *
 * @param {Object} deps
 * @param {Object} deps.containerRef 挂载容器 ref（只在 initScene 时读取）
 * @param {Function} deps.getProps 只读 props 访问器（每次调用返回组件 props 对象）
 * @param {Function} deps.emitViewAngle update:viewAngle 转发回调
 * @param {Function} deps.emitWireframe update:wireframe 转发回调
 */
export function useCarScene({ containerRef, getProps, emitViewAngle, emitWireframe }) {
  const readProps = () => getProps()

  const wireframeMode = ref(readProps().wireframe)
  const autoRotate = ref(true)
  const currentView = ref(readProps().viewAngle)

  let scene, camera, renderer, carGroup
  // initScene 实际绑定事件的容器元素。onUnmounted 触发时 Vue 已清空模板 ref
  // （containerRef.value === null），卸载解绑必须用这个缓存引用，否则监听泄漏。
  let boundContainer = null

  // ---- 平稳垂直起降（VTOL）分支状态 ----
  // 数值状态（flightProgress / flightLastMs / flightYaw*）与帧循环一起在 scene/animator.js；
  // 组件只保留 UI 开关、能耗 HUD 与特效实例。飞行契约：高度 = hoverAltitude ×
  // quinticSmoothstep(progress)（C² 连续，端点加速度为零），全程纯垂直 + 零滚转。
  const flightEngaged = ref(false)
  const flightAvailable = computed(() => readProps().carParams?.enable_vtol !== false)
  // VTOL 特效（升力环 + 地面能量场）持有权在 scene/flightFx.js：组件只保留实例与布局，
  // 不再保存 rings / groundGlow 镜像，animator 一律通过 flightFx.update 读写。
  let flightFx = null
  // assembleCar 返回的 deriveLiftDevices 结果，flightFx.ensure 原样复用（同一份布局）
  let currentLiftLayout = null

  // ---- 车门打开动画状态 ----
  // doorOpen 开关；doorProgress ∈ [0,1] 缓动趋近目标；doorHinges 由 createCar 重建
  const doorOpen = ref(false)
  let doorHinges = []
  let doorSeams = []
  const toggleDoor = () => { doorOpen.value = !doorOpen.value }

  // 门洞/玻璃洞口**常挖**（与门开合状态无关）：门板 + 门片玻璃是全车唯一的门几何——
  // 关门时门板/玻璃盖住洞口封闭，开门时随铰链外摆、原位留下全空通透孔洞。
  // 动画本身由 doorProgress 平滑驱动，开合不再触发车身重建。

  // ---- 反重力飞控：360° 原地转向 + 姿态微摆 ----
  // 偏航为累计角（无 wrap）：连续指令多圈累加，全自由度无限制；
  // 转向剖面 Δ·quintic(t/T) —— C² 端点归零（角速度/角加速度平滑起落，无卡顿无失稳）。
  // 累计角与转向进度在 scene/animator.js 内，组件只用 yawTurning 驱动按钮 busy 态。
  const yawTurning = ref(false)

  /** 能耗 HUD（悬停功率 + 续航倍数，公式与后端 flight_envelope 同源） */
  const flightEnergy = computed(() => {
    const props = readProps()
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
    animator?.startTurn(delta)   // yawTurning 由 animator 在起转/到位时回调置位与复位
  }
  let detachInteractions = null   // attachInteractions 返回的解绑函数
  // 帧循环唯一实例（scene/animator.js）：持有相机 target/current 与 isDragging；
  // 每次 initScene 新建，未挂载时为 null，所有调用点都用可选链。
  let animator = null
  let orthoCamera

  /**
   * 整车装配入口（P5 批次 3）：几何编排全部在 three/assembly/assembleCar.js，
   * 本处只做「传快照 → 同步写回 → 返回车组」三步，不再持有任何装配细节。
   *
   * 写回必须**同步**发生在返回之前：animator.start() 首帧就要读 doorHinges，
   * flightFx.ensure 首帧就要读 currentLiftLayout；NURBS 路径 liftLayout 由
   * assembleCar 显式返回 null（不建环），任何异步化都会让首帧读到上一台车的引用。
   *
   * 入参快照只读：carParams / carType / carColor / wireframe / nurbsMesh 逐一取出，
   * assembly 层拿到的是值而非 ref/getter，因此不会反向依赖响应式状态（单向依赖）。
   */
  const createCar = () => {
    const props = readProps()
    // 入口清空门铰链/门缝引用：NURBS 路径不建门，若残留上一台车的铰链会让
    // 门板内饰误挂到已销毁的 Group。动画每帧读取的也是这里的引用，必须同源。
    doorHinges = []
    doorSeams = []
    const built = assembleCar({
      carParams: props.carParams,
      carType: props.carType,
      carColor: props.carColor,
      wireframe: wireframeMode.value,
      nurbsMesh: props.nurbsMesh
    })
    // 同步写回本次装配的真引用（消除 createCar 内部对这三处外部状态的三次隐式赋值）
    doorHinges = built.doorHinges
    doorSeams = built.doorSeams
    currentLiftLayout = built.liftLayout
    return built.group
  }

  const initScene = () => {
    const container = containerRef.value
    if (!container) return
    const props = readProps()

    // 机位状态访问器：target/current 全部在 scene/animator.js 持有（P3 animate 批），
    // 这里只转发；钩子签名、字段与挂载时机保持不变。
    const viewControls = {
      applyPreset: (key) => setViewAngle(key),
      snap: () => animator?.snap(),
      setTargets: (pose) => animator?.setTargets(pose),
      setOrtho: (ortho) => animator?.setOrtho(ortho)
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
    // 特效实例与场景同作用域；ensure 仍由 animator 首帧调用（保持 noCastShadow 时序）
    flightFx = createFlightFx({ scene })
    // 帧循环唯一实例：carGroup / 铰链 / 场景状态一律走 getter，重建换对象后不会读到旧引用
    animator = createAnimator({
      scene, camera, orthoCamera, renderer,
      getCarGroup: () => carGroup,
      getDoorHinges: () => doorHinges,
      getDoorSeams: () => doorSeams,
      getCarParams: () => readProps().carParams,
      getCarType: () => readProps().carType,
      getLiftLayout: () => currentLiftLayout,
      getAutoRotate: () => autoRotate.value,
      getCurrentView: () => currentView.value,
      getDoorOpen: () => doorOpen.value,
      getFlightEngaged: () => flightEngaged.value,
      getFlightAvailable: () => flightAvailable.value,
      getFlightFx: () => flightFx,
      setYawTurning: (v) => { yawTurning.value = v }
    })

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
      animator?.setDoorInstant(open)
    }
    scene.userData.__car3d__.viewState = () => animator.getState()

    boundContainer = container
    // 交互（拖拽/缩放/resize）在 scene/interactions.js：只写 target*，缓动留给 animate 批。
    // 传入的宿主是缓存的 boundContainer（卸载时 containerRef 已为空），detach 也解绑它。
    detachInteractions = attachInteractions({
      container: boundContainer,
      camera,
      orthoCamera,
      renderer,
      view: {
        getRotation: animator.getRotation,
        setRotation: animator.setRotation,
        getPan: animator.getPan,
        setPan: animator.setPan,
        getDistance: animator.getDistance,
        setDistance: animator.setDistance,
        setDragging: animator.setDragging
      }
    })

    animator.start()
  }

  // ---- VTOL 特效：升力风扇环（随车）+ 地面能量场（贴地衰减）----
  // 实现已迁至 scene/flightFx.js（P3）：持有权、建环常量、逐帧外观公式全部在模块内；
  // 这里只保留 dispose 调用点，保证 updateCar / onUnmounted 的释放时序不变
  // （ensure / update 由 animator 每帧调用）。
  const disposeFlightFx = () => {
    flightFx?.dispose()
  }

  const toggleFlight = () => {
    if (!flightAvailable.value) return
    flightEngaged.value = !flightEngaged.value
  }

  // 帧循环已迁至 scene/animator.js（P3 animate 批）：相机 target/current 缓动、VTOL 升降与
  // 转向、车门开合、渲染全部在模块内；组件只保留 start/stop 句柄与状态 getter 注入。

  const setViewAngle = (view) => {
    currentView.value = view
    emitViewAngle(view)

    const preset = viewPresets[view]
    if (preset) {
      animator?.setTargets({ rotX: preset.x, rotY: preset.y, distance: preset.dist })
      animator?.setOrtho(preset.ortho)

      if (preset.ortho) {
        // 容器尺寸由组件侧 containerRef 读取后传入；模块只负责纯函数换算
        const container = containerRef.value
        if (container) {
          const vp = orthoViewportSize(preset.dist, container.clientWidth, container.clientHeight)
          orthoCamera.left = vp.left
          orthoCamera.right = vp.right
          orthoCamera.top = vp.top
          orthoCamera.bottom = vp.bottom
          orthoCamera.updateProjectionMatrix()
        }
      }
    }
  }

  const resetView = () => {
    animator?.setTargets({ rotX: 0.4, rotY: 0.8, distance: 8, panX: 0, panY: 0 })
    currentView.value = 'perspective'
    animator?.setOrtho(false)
    emitViewAngle('perspective')
  }

  const toggleWireframe = () => {
    wireframeMode.value = !wireframeMode.value
    emitWireframe(wireframeMode.value)
    if (scene) scene.userData.__car3d__.wireframe = wireframeMode.value   // 多实例定位标记同步
    updateCar()
  }

  const toggleAutoRotate = () => {
    autoRotate.value = !autoRotate.value
  }

  // 材质随附贴图（alphaMap 等 CanvasTexture）必须显式 dispose，否则内存泄漏
  // —— 实现已迁至 src/three/dispose.js（P1 拆分）

  const updateCar = () => {
    const props = readProps()
    if (!scene || !carGroup) return
    scene.userData.__car3d__.nurbs = !!props.nurbsMesh   // 生成后 nurbs 标记同步，供多实例定位
    scene.remove(carGroup)
    disposeFlightFx()
    currentLiftLayout = null   // 旧布局随旧车失效，createCar 重新赋值后再被 flightFx.ensure 复用
    animator?.resetTiming()    // 重建后重置帧间计时，首帧 vdt = 0
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

  // watch 分两组，严禁合并：
  // 1) 重建组：车身参数 / 车型 / 车色 / NURBS 网格 / 线框 → 重建几何（updateCar）
  watch(
    () => [readProps().carParams, readProps().carType, readProps().carColor, readProps().nurbsMesh],
    () => updateCar(),
    { deep: true }
  )

  watch(
    () => readProps().wireframe,
    (val) => {
      if (val !== wireframeMode.value) {
        wireframeMode.value = val
        updateCar()
      }
    }
  )

  // 2) 机位组：viewAngle 只走机位，绝不触发重建
  watch(
    () => readProps().viewAngle,
    (val) => {
      if (val !== currentView.value) {
        setViewAngle(val)
      }
    }
  )

  // 生命周期唯一注册点：组件内不得再注册第二个 onMounted / onUnmounted。
  onMounted(() => {
    initScene()
    const viewAngle = readProps().viewAngle
    if (viewAngle !== 'perspective') {
      setViewAngle(viewAngle)
    }
  })

  onUnmounted(() => {
    // 卸载顺序：先停帧循环 → 再释放特效 → 最后解绑交互，禁止最后一帧用已释放对象渲染
    if (animator) {
      animator.stop()
      animator = null
    }
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

  return {
    wireframeMode,
    autoRotate,
    currentView,
    doorOpen,
    flightEngaged,
    flightAvailable,
    yawTurning,
    flightEnergy,
    setViewAngle,
    resetView,
    toggleWireframe,
    toggleAutoRotate,
    toggleDoor,
    toggleFlight,
    startTurn
  }
}
