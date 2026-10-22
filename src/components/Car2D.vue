<template>
  <div class="car-2d-container">
    <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="car-2d-svg" preserveAspectRatio="xMidYMid meet">
      <defs>
        <pattern id="grid2d" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid2d)" />

      <g :transform="`translate(${contentX}, 0)`">
        <!-- 车底地面阴影 -->
        <ellipse :cx="shadowCX" :cy="groundY" :rx="shadowRX" :ry="s(12)" fill="rgba(0,0,0,0.5)" />

        <!-- 闭合车身轮廓（含前后保险杠立面与轮拱开口） -->
        <path :d="silhouettePath" fill="rgba(74,222,128,0.06)" stroke="#4ade80" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />

        <!-- 侧窗 DLO（四角锚点与 3D 玻璃同源 deriveCabinGlass）+ B 柱 -->
        <path :d="windowPath" fill="rgba(59,130,246,0.12)" stroke="#3b82f6" stroke-width="1.1" vector-effect="non-scaling-stroke" />
        <!-- 玻璃门缝：分缝线延伸进侧窗（与 3D 侧窗切片同坐标，开门时该片随门外摆） -->
        <line
          v-for="g in glassSeams2d"
          :key="'gs' + g.x"
          :x1="g.x" :y1="g.y1" :x2="g.x" :y2="g.y2"
          stroke="rgba(59,130,246,0.5)" stroke-width="1" stroke-dasharray="2,3"
          vector-effect="non-scaling-stroke"
        />
        <!-- B 柱：车身色实体，宽度 = b_pillar_width_ratio 联动（与 3D 立柱同宽同高）+ 中心线标注 -->
        <rect :x="bPillarX2d" :y="bPillarTopY2d" :width="bPillarW2d" :height="bPillarH2d" fill="rgba(10,12,18,0.85)" stroke="rgba(59,130,246,0.6)" stroke-width="1" vector-effect="non-scaling-stroke" />
        <line :x1="pillarCenterX2d" :y1="bPillarTopY2d" :x2="pillarCenterX2d" :y2="bPillarTopY2d + bPillarH2d" stroke="rgba(59,130,246,0.85)" stroke-width="1" />

        <!-- 腰带线 -->
        <path :d="beltLinePath" fill="none" stroke="rgba(74,222,128,0.55)" stroke-width="1" stroke-dasharray="4,3" vector-effect="non-scaling-stroke" />

        <!-- 车轮（触地、同心：轮胎/轮辋/轮毂） -->
        <g v-for="w in wheelGroups" :key="w.cx">
          <circle :cx="w.cx" :cy="w.cy" :r="w.r" fill="rgba(10,12,18,0.9)" stroke="rgba(255,255,255,0.75)" stroke-width="1.6" vector-effect="non-scaling-stroke" />
          <circle :cx="w.cx" :cy="w.cy" :r="w.r * 0.58" fill="none" stroke="rgba(74,222,128,0.55)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <circle :cx="w.cx" :cy="w.cy" :r="w.r * 0.12" fill="rgba(255,255,255,0.5)" />
        </g>

        <!-- 灯具侧视标记（与 3D 新增零件同源布置） -->
        <rect :x="0" :y="hoodLineY + s(60)" :width="s(55)" :height="s(90)" fill="rgba(255,240,170,0.5)" stroke="#fbbf24" stroke-width="1" vector-effect="non-scaling-stroke" />
        <rect :x="rearX - s(50)" :y="trunkLineY + s(60)" :width="s(50)" :height="s(90)" fill="rgba(255,90,90,0.4)" stroke="#ff6b6b" stroke-width="1" vector-effect="non-scaling-stroke" />

        <!-- 车门分缝线（与 3D 门板同上下界）+ 门把手（与 3D 同源 deriveDoorLayout） -->
        <line :x1="frontSeamX2d" :y1="doorSeamBotY2d" :x2="frontSeamX2d" :y2="doorSeamTopY2d" stroke="rgba(59,130,246,0.6)" stroke-width="1" stroke-dasharray="3,3" vector-effect="non-scaling-stroke" />
        <line :x1="midSeamX2d" :y1="doorSeamBotY2d" :x2="midSeamX2d" :y2="doorSeamTopY2d" stroke="rgba(59,130,246,0.6)" stroke-width="1" stroke-dasharray="3,3" vector-effect="non-scaling-stroke" />
        <line v-if="rearSeamX2d !== null" :x1="rearSeamX2d" :y1="doorSeamBotY2d" :x2="rearSeamX2d" :y2="doorSeamTopY2d" stroke="rgba(59,130,246,0.6)" stroke-width="1" stroke-dasharray="3,3" vector-effect="non-scaling-stroke" />
        <line :x1="frontHandleX2d - s(70)" :y1="handleY2d" :x2="frontHandleX2d + s(70)" :y2="handleY2d" stroke="rgba(255,255,255,0.7)" stroke-width="2.4" vector-effect="non-scaling-stroke" />
        <line v-if="rearHandleX2d !== null" :x1="rearHandleX2d - s(70)" :y1="handleY2d" :x2="rearHandleX2d + s(70)" :y2="handleY2d" stroke="rgba(255,255,255,0.7)" stroke-width="2.4" vector-effect="non-scaling-stroke" />

        <!-- 接近角/离去角构造线：接地点 → 车身立面底角（坡面 cornerY 由可调角度驱动，与 3D 同源） -->
        <line :x1="frontWheelCX" :y1="groundY" :x2="0" :y2="frontCornerY2d" stroke="#fbbf24" stroke-width="1" stroke-dasharray="5,4" vector-effect="non-scaling-stroke" />
        <text :x="frontWheelCX * 0.42" :y="groundY - s(groundClearanceMm * 0.45) - 8" text-anchor="middle" fill="#fbbf24" font-family="Inter, sans-serif" font-size="11" font-weight="600">α {{ approachLabel }}</text>
        <line :x1="rearWheelCX" :y1="groundY" :x2="rearX" :y2="rearCornerY2d" stroke="#fbbf24" stroke-width="1" stroke-dasharray="5,4" vector-effect="non-scaling-stroke" />
        <text :x="(rearWheelCX + rearX) / 2" :y="groundY - s(groundClearanceMm * 0.45) - 8" text-anchor="middle" fill="#fbbf24" font-family="Inter, sans-serif" font-size="11" font-weight="600">β {{ departureLabel }}</text>

        <!-- 地面线 -->
        <line :x1="groundX1" :y1="groundY" :x2="groundX2" :y2="groundY" stroke="rgba(255,255,255,0.22)" stroke-width="1" vector-effect="non-scaling-stroke" />

        <!-- ===== 尺寸标注区：地面线下方三行（FO/RO · WB · L）+ 右侧车高 H，延伸线规范 ===== -->
        <g font-family="Inter, sans-serif" font-size="11">
          <!-- 延伸线（从地面线垂至对应尺寸行） -->
          <line :x1="0" :y1="groundY + 3" :x2="0" :y2="dimY3 + 4" stroke="rgba(255,255,255,0.32)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <line :x1="frontWheelCX" :y1="groundY + 3" :x2="frontWheelCX" :y2="dimY2 + 4" stroke="rgba(255,255,255,0.32)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <line :x1="rearWheelCX" :y1="groundY + 3" :x2="rearWheelCX" :y2="dimY2 + 4" stroke="rgba(255,255,255,0.32)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <line :x1="rearX" :y1="groundY + 3" :x2="rearX" :y2="dimY3 + 4" stroke="rgba(255,255,255,0.32)" stroke-width="1" vector-effect="non-scaling-stroke" />

          <!-- 第一行：前悬 FO / 后悬 RO -->
          <line :x1="0" :y1="dimY1" :x2="frontWheelCX" :y2="dimY1" stroke="#00ff88" stroke-width="1" vector-effect="non-scaling-stroke" />
          <text :x="frontWheelCX / 2" :y="dimY1 - 5" text-anchor="middle" fill="#00ff88" font-weight="600">FO {{ FO }}mm</text>
          <line :x1="rearWheelCX" :y1="dimY1" :x2="rearX" :y2="dimY1" stroke="#ff6b6b" stroke-width="1" vector-effect="non-scaling-stroke" />
          <text :x="(rearWheelCX + rearX) / 2" :y="dimY1 - 5" text-anchor="middle" fill="#ff6b6b" font-weight="600">RO {{ RO }}mm</text>

          <!-- 第二行：轴距 WB -->
          <line :x1="frontWheelCX" :y1="dimY2" :x2="rearWheelCX" :y2="dimY2" stroke="rgba(255,255,255,0.6)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <text :x="wheelBaseMidX" :y="dimY2 - 5" text-anchor="middle" fill="rgba(255,255,255,0.78)">WB {{ WB }}mm</text>

          <!-- 第三行：整车长 L -->
          <line :x1="0" :y1="dimY3" :x2="rearX" :y2="dimY3" stroke="rgba(255,255,255,0.6)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <text :x="rearX / 2" :y="dimY3 - 5" text-anchor="middle" fill="rgba(255,255,255,0.78)" font-weight="600">L {{ actualLength }}mm</text>

          <!-- 车高 H：车尾右侧垂直尺寸线 + 车顶延伸线 -->
          <line :x1="rearWindowTopX" :y1="roofTopY" :x2="rearX + 48" :y2="roofTopY" stroke="rgba(255,255,255,0.32)" stroke-width="1" stroke-dasharray="3,3" vector-effect="non-scaling-stroke" />
          <line :x1="rearX + 44" :y1="groundY" :x2="rearX + 44" :y2="roofTopY" stroke="rgba(255,255,255,0.6)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <text :transform="`rotate(-90 ${rearX + 56} ${(groundY + roofTopY) / 2})`" :x="rearX + 56" :y="(groundY + roofTopY) / 2" text-anchor="middle" fill="rgba(255,255,255,0.78)" font-weight="600">H {{ overallHeight }}mm</text>

          <!-- 车宽 W：侧视图无法直接标注，车顶右上方文本给出 -->
          <text :x="rearX + 44" :y="roofTopY - 10" text-anchor="end" fill="rgba(255,255,255,0.55)">W {{ overallWidth }}mm</text>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { deriveCarProfile, deriveDoorLayout, bodySideOutline } from '../utils/carProfile.js'
import { deriveCabinGlass, ROOF_FILLETS } from '../utils/carGlass.js'

const props = defineProps({
  carParams: {
    type: Object,
    required: true
  },
  carType: {
    type: String,
    default: 'sedan'
  }
})

// ============ 画布布局：高度方向与宽度方向共同约束缩放，杜绝车顶越界裁切 ============
const svgWidth = 800
const svgHeight = 420
const padTop = 30          // 车顶上方留白
const dimAreaH = 84        // 地面线下方标注区（FO/RO · WB · L 三行尺寸）
const groundY = svgHeight - dimAreaH

// 尺寸标注行（地面线下方）
const dimY1 = groundY + 20 // 前悬 FO / 后悬 RO
const dimY2 = groundY + 42 // 轴距 WB
const dimY3 = groundY + 64 // 整车长 L

const FO = computed(() => props.carParams.front_overhang ?? 1000)
const RO = computed(() => props.carParams.rear_overhang ?? 1000)
const WB = computed(() => props.carParams.wheel_base)
const overallHeight = computed(() => props.carParams.overall_height ?? 1400)
const overallWidth = computed(() => props.carParams.overall_width ?? 1800)
const groundClearanceMm = computed(() => props.carParams.ground_clearance ?? 140)

const actualLength = computed(() => FO.value + WB.value + RO.value)

// 双向自适应：同时满足宽度（车长）与高度（离地总高 H，含离地间隙）约束
// 宽度预留 150px：右侧容纳 H 车高垂直标注（rearX+56），左侧容纳延伸线
const scale = computed(() => {
  const usableW = svgWidth - 150
  const usableH = groundY - padTop
  return Math.min(usableW / actualLength.value, usableH / overallHeight.value)
})
const s = (val) => val * scale.value

// 水平居中
const contentX = computed(() => (svgWidth - actualLength.value * scale.value) / 2)

const rearX = computed(() => s(actualLength.value))
const frontWheelCX = computed(() => s(FO.value))
const rearWheelCX = computed(() => s(FO.value + WB.value))
const wheelBaseMidX = computed(() => (frontWheelCX.value + rearWheelCX.value) / 2)

// 车轮：触地（轮胎最低点 = 地面），轮胎/轮辋/轮毂同心
const wheelRadius = computed(() => s((props.carParams.wheel_diameter ?? 680) / 2))
const wheelCY = computed(() => groundY - wheelRadius.value)
const wheelGroups = computed(() => [
  { cx: frontWheelCX.value, cy: wheelCY.value, r: wheelRadius.value },
  { cx: rearWheelCX.value, cy: wheelCY.value, r: wheelRadius.value }
])

// ============ 轮廓锚点：全部由 deriveCarProfile 推导（2D/3D 唯一来源，镜像换算） ============
// 3D 坐标 X+ 朝车头 → 2D x = 距前保险杠距离；高度线 = 离地高度（与 3D 完全同值）
const profile = computed(() => deriveCarProfile(props.carParams, props.carType))
const isPickup = computed(() => props.carType === 'pickup')
const toX = (x3d) => s((profile.value.frontX - x3d) * 1000)

const roofTopY = computed(() => groundY - s(profile.value.roofTopY * 1000))
const beltLineY = computed(() => groundY - s(profile.value.beltLineY * 1000))
const hoodLineY = computed(() => groundY - s(profile.value.hoodLineY * 1000))
const trunkLineY = computed(() => groundY - s(profile.value.trunkLineY * 1000))

const hoodEndX = computed(() => toX(profile.value.hoodEndX))
// Cowl 斜坡锚点（共享）：机盖面在风挡底之前上升至腰带线
const cowlStartX = computed(() => toX(profile.value.cowlStartX))
const rearWindowTopX = computed(() => toX(profile.value.rearWindowTopX))
const rearWindowBottomX = computed(() => toX(profile.value.rearWindowBottomX))
// 皮卡：驾驶室后壁（与 3D pickup 结构同源）
const cabRearX2d = computed(() => (profile.value.pickup ? toX(profile.value.pickup.cabRearX) : 0))

// ============ 侧窗 / B 柱 / 车门：与 3D 完全同源（deriveCabinGlass + deriveDoorLayout） ============
// 2D 不再保留任何独立启发式（原 pillarX = 0.55 分段、手写 DLO 梯形、手写轮廓均已删除）
const cabin2d = computed(() => deriveCabinGlass(profile.value, {
  carType: props.carType,
  sideGlassAngle: props.carParams.side_glass_angle,
  glassBarrelAngle: props.carParams.glass_barrel_angle,
  glassBarrelRadius: props.carParams.glass_barrel_radius
}))
const dl2d = computed(() => deriveDoorLayout(profile.value, cabin2d.value, {
  bPillarWidthRatio: props.carParams.b_pillar_width_ratio,
  handleDropRatio: props.carParams.handle_drop_ratio,
  handleXRatio: props.carParams.handle_x_ratio
}))

// B 柱：与 3D 立柱同宽同高同 X（宽度 = b_pillar_width_ratio × 座舱高；X = 门模块分缝）
const pillarCenterX2d = computed(() => toX(dl2d.value.midSeamX))
const bPillarW2d = computed(() => dl2d.value.bWidth * 1000 * scale.value)
const bPillarX2d = computed(() => toX(dl2d.value.midSeamX + dl2d.value.bWidth / 2))
const bPillarTopY2d = computed(() => groundY - cabin2d.value.pillar.topY * 1000 * scale.value)
const bPillarH2d = computed(() => (cabin2d.value.pillar.topY - cabin2d.value.pillar.botY) * 1000 * scale.value)

const frontSeamX2d = computed(() => toX(dl2d.value.frontSeamX))
const midSeamX2d = computed(() => toX(dl2d.value.midSeamX))
const rearSeamX2d = computed(() => (dl2d.value.rearSeamX === null ? null : toX(dl2d.value.rearSeamX)))
const frontHandleX2d = computed(() => toX(dl2d.value.frontHandleX))
const rearHandleX2d = computed(() => (dl2d.value.rearHandleX === null ? null : toX(dl2d.value.rearHandleX)))
const handleY2d = computed(() => groundY - s(dl2d.value.handleY * 1000))
// 门缝上下界 = 3D 门板上下界（doorBottom = 底板 + 0.02，doorTop = 腰带线 - 0.004）
const doorSeamBotY2d = computed(() => groundY - s((profile.value.bodyBottomY + 0.02) * 1000))
const doorSeamTopY2d = computed(() => groundY - s((profile.value.beltLineY - 0.004) * 1000))

// 玻璃门缝：分缝线在 DLO 内继续向上（与 3D 侧窗按门缝切片同坐标）
// DLO 顶缘 = 车顶水平线；分缝在车顶 X 范围之外时取 A/C 柱斜边交点
const dloTopY2d = (x3d) => {
  const d = cabin2d.value.dlo          // [底前, 顶前, 顶后, 底后]
  const fxB = d[0][0], yb = d[0][1]
  const fxT = d[1][0], yt = d[1][1]
  const rtx = d[2][0], rxB = d[3][0]
  let t = 1
  if (x3d > fxT) t = Math.min(Math.max((fxB - x3d) / (fxB - fxT), 0), 1)
  else if (x3d < rtx) t = Math.min(Math.max((rxB - x3d) / (rxB - rtx), 0), 1)
  return outY(yb + t * (yt - yb))
}
const glassSeams2d = computed(() => {
  const xs = [dl2d.value.frontSeamX, dl2d.value.midSeamX]
  if (dl2d.value.rearSeamX !== null) xs.push(dl2d.value.rearSeamX)
  return xs.map((x3d) => ({ x: toX(x3d), y1: doorSeamTopY2d.value, y2: dloTopY2d(x3d) }))
})

// 接近角/离去角标注 + 坡面底角 Y（carProfile 同源角度，ramps 驱动立面底角高度）
const approachLabel = computed(() => `${profile.value.approachAngleDeg.toFixed(1)}°`)
const departureLabel = computed(() => `${profile.value.departureAngleDeg.toFixed(1)}°`)
const frontCornerY2d = computed(() => groundY - s(profile.value.ramps.front.cornerY * 1000))
const rearCornerY2d = computed(() => groundY - s(profile.value.ramps.rear.cornerY * 1000))

// ============ 闭合车身轮廓：bodySideOutline 单一真源 → SVG（X 镜像 + Y 翻转） ============
// 与 Car3D bodyShape 逐指令同源：顶边 G1 圆角、底边轮拱 notch（真正挖通）、接近/离去角切角、
// 皮卡驾驶室+货箱专属拓扑，全部无 2D 侧重复推导
const pxPerM = computed(() => scale.value * 1000)
const outX = (x) => (profile.value.frontX - x) * pxPerM.value
const outY = (y) => groundY - y * pxPerM.value
const silhouettePath = computed(() => {
  const parts = []
  for (const c of bodySideOutline(profile.value, props.carType, ROOF_FILLETS, profile.value.ramps)) {
    if (c.k === 'M') parts.push(`M${outX(c.x)},${outY(c.y)}`)
    else if (c.k === 'L') parts.push(`L${outX(c.x)},${outY(c.y)}`)
    else if (c.k === 'Q') parts.push(`Q${outX(c.cx)},${outY(c.cy)} ${outX(c.x)},${outY(c.y)}`)
    else if (c.k === 'A') {
      // 3D 椭圆弧（角度制、y 向上）→ SVG 端点弧；上半弧在屏幕上向上鼓 = sweep 0
      const p0x = c.cx + c.rx * Math.cos(c.a0)
      const p0y = c.cy + c.ry * Math.sin(c.a0)
      const p1x = c.cx + c.rx * Math.cos(c.a1)
      const p1y = c.cy + c.ry * Math.sin(c.a1)
      const midY = c.cy + c.ry * Math.sin((c.a0 + c.a1) / 2)
      const sweep = midY > Math.max(p0y, p1y) ? 0 : 1
      parts.push(`A${c.rx * pxPerM.value},${c.ry * pxPerM.value} 0 0 ${sweep} ${outX(p1x)},${outY(p1y)}`)
    }
  }
  parts.push('Z')
  return parts.join(' ')
})

// 腰带线：皮卡仅覆盖驾驶室段（货箱栏板顶线由轮廓表达），其余车型贯通至 C 柱底
const beltLinePath = computed(() => {
  const endX = isPickup.value ? cabRearX2d.value : rearWindowBottomX.value
  return `M${hoodEndX.value},${beltLineY.value} L${endX},${beltLineY.value}`
})

// 侧窗 DLO：四角 = 3D 玻璃面板四角（含 A/C 柱圆角修裁量），侧视投影逐点一致
const windowPath = computed(() => {
  return cabin2d.value.dlo
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${outX(p[0])},${outY(p[1])}`)
    .join(' ') + ' Z'
})

// 阴影：覆盖轴距 + 轮径范围
const shadowCX = computed(() => (frontWheelCX.value + rearWheelCX.value) / 2)
const shadowRX = computed(() => (WB.value + (props.carParams.wheel_diameter ?? 680) * 1.6) / 2 * scale.value)

const groundX1 = computed(() => -24)
const groundX2 = computed(() => rearX.value + 48)
</script>

<style scoped>
.car-2d-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-radius: 8px;
  overflow: hidden;
}

.car-2d-svg {
  width: 100%;
  height: 100%;
}
</style>
