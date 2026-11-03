import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { createScene } from '../three/scene/createScene.js'
import { attachInteractions } from '../three/scene/interactions.js'
import { createFlightFx } from '../three/scene/flightFx.js'
import { createAnimator } from '../three/scene/animator.js'
import { deriveCarProfile, deriveWheelFitment, deriveDoorLayout, deriveLiftDevices } from '../utils/carProfile.js'
import { createNurbsCar, alignNurbsToProfile } from '../three/assembly/nurbsCar.js'
import { buildBodyShell, FRONT_GLASS_TOP_BORDER } from '../three/geometry/bodyShell.js'
import { deriveCabinGlass, pillarPlacement, deriveDloPaneRanges, ROOF_FILLETS } from '../utils/carGlass.js'
import { resolveFlightParams, flightControlEnvelope } from '../utils/flightPhysics.js'
import { createSteeringWheel, resolveSeatPreset } from '../utils/carInterior.js'
import { disposeObject } from '../three/dispose.js'
import { createDoorRig } from '../three/parts/doors.js'
import { addBandGlass, addDloPane } from '../three/parts/glass.js'
import { addInteriorSeats } from '../three/interior/seats.js'
import { createLightsBumpers } from '../three/parts/lightsBumpers.js'
import { createMirrors } from '../three/parts/mirrors.js'
import { createWheels, addArchLiners, createLiftDucts } from '../three/parts/wheels.js'
import { createMaterialSet } from '../three/materials.js'

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
 * 场景编排 composable（P4 拆分）：接管 createCar / initScene / updateCar / 生命周期 / watch。
 * 组件侧只保留模板、props 与纯 UI 状态（isFullscreen / toggleFullscreen）。
 *
 * @param {Object} deps
 * @param {import('vue').Ref} deps.containerRef 挂载容器 ref（只在 initScene 时读取）
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
  // createCar 里与 createLiftDucts 共用同一份 deriveLiftDevices 结果，flightFx.ensure 原样复用
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
   * 内饰座椅 + 舱内附件装配：几何与挂载全部在 three/interior/seats.js（P2 拆分）。
   * 调用时序是契约——必须在 createDoorRig 之后，否则门板内饰拿不到铰链、开门时不跟动。
   */
  const createCar = () => {
    const props = readProps()
    // 每次重建先清空门铰链/门缝引用：NURBS 路径不建门，若残留上一台车的铰链会让
    // 门板内饰误挂到已销毁的 Group。动画每帧读取的也是这里的引用，必须同源。
    doorHinges = []
    doorSeams = []
    // 座椅材质预设由调用方解析（内饰模块不读 props）
    const seatPreset = resolveSeatPreset(props.carType, props.carParams)
    // 有后端真实网格时走高保真路径：车身先对齐到 carProfile 坐标系，再与内饰件同父级共存。
    // NURBS 路径不建门、不建升力装置：门引用清空、liftLayout 显式 null（flightFx.ensure 不建环）。
    if (props.nurbsMesh) {
      const P = deriveCarProfile(props.carParams, props.carType)
      const root = new THREE.Group()
      const body = createNurbsCar(props.nurbsMesh, {
        carColor: props.carColor,
        wireframe: wireframeMode.value
      })
      alignNurbsToProfile(body, props.nurbsMesh, P)
      root.add(body)
      currentLiftLayout = null
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

    // ---- 车身壳（侧围轮廓 + 洞口 + 挤出 + greenhouse 收窄 + 洞壁内饰化）----
    // 几何装配整体在 three/geometry/bodyShell.js（P5 批次 2）：入口只传真源对象，
    // 车身洞口/锥化必需的 carGlass 常量（ROOF_FILLETS / BODY_BEVEL_SIZE /
    // DLO_APERTURE_INSET）在模块内直接从 carGlass 取，不经 composable 转发。
    const shell = buildBodyShell({ P, carType: props.carType, cabin, doorLayout: dl, paneRanges })
    const bodyGeom = shell.bodyGeom
    // 车轮/车门/门缝/后视镜的安装基准：车身实际半宽 bodyExtentZ（= W/2），
    // 不是 W/2 + bevel——否则这些部件会整体浮出车身外表面。
    const bodyExtentZ = shell.bodyExtentZ
    const dloFrame = shell.dloFrame
    const taperK = shell.taperK
    const shoulderY = shell.shoulderY
    const fit = deriveWheelFitment(P, bodyExtentZ)

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
    // 布局在此算一次：悬停风扇环（animator → flightFx.ensure）沿用同一份 deriveLiftDevices，避免环与风道错位
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
      outlineShape: shell.outlineShape,
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
