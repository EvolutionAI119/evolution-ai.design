import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { createScene } from '../three/scene/createScene.js'
import { attachInteractions } from '../three/scene/interactions.js'
import { createFlightFx } from '../three/scene/flightFx.js'
import { createAnimator } from '../three/scene/animator.js'
import { deriveCarProfile, deriveWheelFitment, bodySideOutline, deriveDoorLayout, deriveLiftDevices } from '../utils/carProfile.js'
import { createNurbsCar, alignNurbsToProfile } from '../three/assembly/nurbsCar.js'
import { deriveCabinGlass, pillarPlacement, buildDloFrame, deriveDloPaneRanges, deriveDloApertures, buildDoorAperturePolygon, shellHalfZAt, insideBodyMaterial, ROOF_FILLETS, BODY_BEVEL_SIZE, DLO_APERTURE_INSET } from '../utils/carGlass.js'
import { resolveFlightParams, flightControlEnvelope } from '../utils/flightPhysics.js'
import { createSteeringWheel, resolveSeatPreset } from '../utils/carInterior.js'
import { smoothNormalsKeepHardEdges, splitTrianglesAtY } from '../three/geometry/smoothing.js'
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
