import * as THREE from 'three'
import { deriveCarProfile, deriveWheelFitment, deriveDoorLayout, deriveLiftDevices } from '../../utils/carProfile.js'
import { deriveCabinGlass, pillarPlacement, deriveDloPaneRanges, ROOF_FILLETS } from '../../utils/carGlass.js'
import { resolveFlightParams } from '../../utils/flightPhysics.js'
import { createSteeringWheel, resolveSeatPreset } from '../../utils/carInterior.js'
import { createMaterialSet } from '../materials.js'
import { createNurbsCar, alignNurbsToProfile } from './nurbsCar.js'
import { buildBodyShell, FRONT_GLASS_TOP_BORDER } from '../geometry/bodyShell.js'
import { createDoorRig } from '../parts/doors.js'
import { addBandGlass, addDloPane } from '../parts/glass.js'
import { addInteriorSeats } from '../interior/seats.js'
import { createLightsBumpers } from '../parts/lightsBumpers.js'
import { createMirrors } from '../parts/mirrors.js'
import { createWheels, addArchLiners, createLiftDucts } from '../parts/wheels.js'

/**
 * 整车装配编排（P5 批次 3）：只做编排，不做 UI。
 *
 * 入参快照**只读**：不持有 ref/getter，构建期把车色与线框定成字符串/布尔；
 * 依赖单向（assembly → parts/utils/geometry），禁止反向 import composable。
 *
 * @param {Object} snapshot
 * @param {Object} snapshot.carParams 设计参数（mm）
 * @param {string} snapshot.carType 车型
 * @param {string} snapshot.carColor 车漆色
 * @param {boolean} snapshot.wireframe 线框快照
 * @param {Object|null} snapshot.nurbsMesh 后端真实网格（null 走挤出路径）
 * @returns {{ group: THREE.Group, doorHinges: Array, doorSeams: Array, liftLayout: Object|null }}
 *   调用方必须在帧循环启动前同步写回 doorHinges / doorSeams / liftLayout：
 *   animator 每帧通过 getter 读取门铰链，flightFx.ensure 首帧读取 liftLayout。
 */
export function assembleCar({ carParams, carType, carColor, wireframe, nurbsMesh }) {
  // 每次装配从空引用开始：NURBS 路径不建门，若残留上一台车的铰链会让门板内饰
  // 误挂到已销毁的 Group。返回的是本次装配的真引用，由调用方同步替换。
  let doorHinges = []
  let doorSeams = []
  // 座椅材质预设由编排层解析（内饰模块不读参数对象）
  const seatPreset = resolveSeatPreset(carType, carParams)
  // 有后端真实网格时走高保真路径：车身先对齐到 carProfile 坐标系，再与内饰件同父级共存。
  // NURBS 路径不建门、不建升力装置：doorHinges/doorSeams 为空、liftLayout 显式 null。
  if (nurbsMesh) {
    const P = deriveCarProfile(carParams, carType)
    const root = new THREE.Group()
    const body = createNurbsCar(nurbsMesh, { carColor, wireframe })
    alignNurbsToProfile(body, nurbsMesh, P)
    root.add(body)
    addInteriorSeats({ parent: root, P, preset: seatPreset, doorHinges })
    return { group: root, doorHinges, doorSeams, liftLayout: null }
  }
  const group = new THREE.Group()

  // 侧围轮廓（米）：mm 推导与物理约束集中在纯函数，保证全车型拓扑合法
  const P = deriveCarProfile(carParams, carType)
  const {
    W, H, gc, wheelR, halfTrack,
    frontWheelX, rearWheelX, frontX, rearX,
    bodyBottomY, roofTopY, beltLineY, hoodLineY, trunkLineY,
    hoodEndX, cowlStartX, trunkStartX,
    windshieldTopX, rearWindowTopX, rearWindowBottomX,
    wheelArchRadius, archY, wheelArch,
    pickup, rails: railSpec, wing: wingSpec
  } = P

  // 材质集合：构建内工厂，每次装配新建（车色/线框变化都走 updateCar 重建）
  const {
    bodyMat, interiorMat, bodyMats, glassMat,
    wheelMat, rimMat, rimDiscMat, chromeMat,
    ductMat, lipMat, linerMat
  } = createMaterialSet({ carColor, wireframe })

  // 座舱玻璃划分（与 2D Car2D windowPath 同源锚点）；倾角/桶面参数先于车身变形计算，
  // 供车身 greenhouse 收窄与玻璃面板共用同一轮廓公式
  const cabin = deriveCabinGlass(P, {
    carType,
    sideGlassAngle: carParams?.side_glass_angle,
    glassBarrelAngle: carParams?.glass_barrel_angle,
    glassBarrelRadius: carParams?.glass_barrel_radius
  })

  // 车门分缝线 / B柱宽度 / 门把手布置（2D/3D 同源，参数可调）；侧窗分片与门板共用同一条分缝
  const dl = deriveDoorLayout(P, cabin, {
    bPillarWidthRatio: carParams?.b_pillar_width_ratio,
    handleDropRatio: carParams?.handle_drop_ratio,
    handleXRatio: carParams?.handle_x_ratio,
    carType
  })

  // 侧窗分片（A 柱前固定片/前门片/后门片/C 柱后固定片）：玻璃切片与玻璃洞口
  // 共用同一份分片口径（carGlass 纯函数，可单测）；须在车身挖洞前定义
  const paneRanges = deriveDloPaneRanges(dl, carParams?.door_seam_width ?? 8)

  // ---- 车身壳（侧围轮廓 + 洞口 + 挤出 + greenhouse 收窄 + 洞壁内饰化）----
  // 几何装配整体在 three/geometry/bodyShell.js（P5 批次 2）：入口只传真源对象，
  // 车身洞口/锥化必需的 carGlass 常量（ROOF_FILLETS / BODY_BEVEL_SIZE /
  // DLO_APERTURE_INSET）在模块内直接从 carGlass 取，不经编排层转发。
  const shell = buildBodyShell({ P, carType, cabin, doorLayout: dl, paneRanges })
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
      wireframe
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
  // （与门板同轴同角度）——收集顺序是 doors 的输入契约，必须在本编排里完成。
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
  const liftLayout = deriveLiftDevices(P, resolveFlightParams(carType, carParams).liftFans)
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
    wireframe
  })

  // ---- 车门分缝线 + 门板（可绕前铰链打开）+ 门把手（随门板运动）----
  // 几何组装整体在 parts/doors.js（P2 拆分）：此处只传真源坐标与共用材质实例，
  // 返回的铰链/缝条引用交给 animator 逐帧驱动开合，运动学与拆分前一致。
  const doorRig = createDoorRig({
    parent: group,
    wall: fit.wall,
    doorLayout: dl,
    bodyBottomY,
    shoulderY,
    bodyMat,
    chromeMat,
    doorSeamWidth: carParams?.door_seam_width ?? 8,
    doorGlass,
    wireframe
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
    wireframe
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
  // 纯参数化几何、无贴图；由编排层统一构建 → 车型切换时随 updateCar() 整体重建。
  // 玻璃为 depthWrite:false 透明件，座舱内座椅可从风挡/侧窗看到。
  addInteriorSeats({ parent: group, P, preset: seatPreset, doorHinges })

  return { group, doorHinges, doorSeams, liftLayout }
}
