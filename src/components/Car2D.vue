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

        <!-- 侧窗 DLO + B 柱 -->
        <path :d="windowPath" fill="rgba(59,130,246,0.12)" stroke="#3b82f6" stroke-width="1.1" vector-effect="non-scaling-stroke" />
        <line :x1="pillarX" :y1="roofTopY + s(60)" :x2="pillarX" :y2="beltLineY - s(40)" stroke="rgba(59,130,246,0.55)" stroke-width="1" vector-effect="non-scaling-stroke" />

        <!-- 腰带线 -->
        <path :d="beltLinePath" fill="none" stroke="rgba(74,222,128,0.55)" stroke-width="1" stroke-dasharray="4,3" vector-effect="non-scaling-stroke" />

        <!-- 车轮（触地、同心：轮胎/轮辋/轮毂） -->
        <g v-for="w in wheelGroups" :key="w.cx">
          <circle :cx="w.cx" :cy="w.cy" :r="w.r" fill="rgba(10,12,18,0.9)" stroke="rgba(255,255,255,0.75)" stroke-width="1.6" vector-effect="non-scaling-stroke" />
          <circle :cx="w.cx" :cy="w.cy" :r="w.r * 0.58" fill="none" stroke="rgba(74,222,128,0.55)" stroke-width="1" vector-effect="non-scaling-stroke" />
          <circle :cx="w.cx" :cy="w.cy" :r="w.r * 0.12" fill="rgba(255,255,255,0.5)" />
        </g>

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
import { deriveCarProfile } from '../utils/carProfile.js'

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

// 车身底边（侧裙下缘 = 离地间隙；SISA ground_alignment：z 原点 = 地面）
const underbodyY = computed(() => groundY - s(groundClearanceMm.value))

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
const windshieldTopX = computed(() => toX(profile.value.windshieldTopX))
const rearWindowTopX = computed(() => toX(profile.value.rearWindowTopX))
const rearWindowBottomX = computed(() => toX(profile.value.rearWindowBottomX))
// 皮卡：驾驶室后壁 / 后窗下沿（与 3D pickup 结构同源）
const cabRearX2d = computed(() => (profile.value.pickup ? toX(profile.value.pickup.cabRearX) : 0))
const cabWindowBottomX2d = computed(() => (profile.value.pickup ? toX(profile.value.pickup.cabWindowBottomX) : 0))

const pillarX = computed(() => windshieldTopX.value + (rearWindowTopX.value - windshieldTopX.value) * 0.55)

// ============ 轮拱：包络椭圆（拱心=轮心，2D/3D 共享 deriveWheelArch 唯一来源）============
// 竖直拱唇自侧裙下缘升至轮心高度，椭圆上弧过顶（含转向/跳动包络间隙）
const arch2d = computed(() => {
  const a = profile.value.wheelArch
  return {
    cy: wheelCY.value,
    front: { rx: s(a.front.rx * 1000), ry: s(a.front.ry * 1000) },
    rear: { rx: s(a.rear.rx * 1000), ry: s(a.rear.ry * 1000) }
  }
})

// ============ 闭合车身轮廓：前脸 → 引擎盖 → A 柱 → 车顶 → C 柱 → 尾门 → 底边（双侧轮拱） ============
const silhouettePath = computed(() => {
  const fx = 0
  const rx = rearX.value
  const uy = underbodyY.value
  const hy = hoodLineY.value
  const ty = trunkLineY.value
  const noseR = Math.min(s(90), s(FO.value) * 0.5)
  // 轮拱锚点：竖唇位于 ax ± rx（椭圆最宽处=轮心高度），唇顶接椭圆弧
  const fa = arch2d.value.front
  const ra = arch2d.value.rear
  const cy2d = arch2d.value.cy
  const fArchL = Math.max(frontWheelCX.value - fa.rx, s(30))
  const fArchR = Math.min(frontWheelCX.value + fa.rx, rearWheelCX.value - ra.rx - s(20))
  const rArchL = rearWheelCX.value - ra.rx
  const rArchR = Math.min(rearWheelCX.value + ra.rx, rx - s(20))
  const arches = [
    `L${rArchR},${uy}`,
    `L${rArchR},${cy2d}`,
    `A${ra.rx},${ra.ry} 0 1 0 ${rArchL},${cy2d}`,
    `L${rArchL},${uy}`,
    `L${fArchR},${uy}`,
    `L${fArchR},${cy2d}`,
    `A${fa.rx},${fa.ry} 0 1 0 ${fArchL},${cy2d}`,
    `L${fArchL},${uy}`,
    `L${fx},${uy}`,
    'Z'
  ]
  if (isPickup.value) {
    // 皮卡拓扑：车顶止于驾驶室后壁 → 后壁下落至货箱栏板 → 栏板顶贯通至尾门（与 3D carProfile.js 同源）
    const bedY = ty                       // 货箱栏板顶 = H × bed 比例
    return [
      `M${fx},${uy}`,
      `L${fx},${hy + s(55)}`,
      `Q${fx + noseR},${hy} ${cowlStartX.value},${hy}`,
      `L${hoodEndX.value},${beltLineY.value}`,
      `L${windshieldTopX.value},${roofTopY.value}`,
      `L${cabRearX2d.value},${roofTopY.value}`,
      `L${cabWindowBottomX2d.value},${bedY}`,
      `L${rx - s(24)},${bedY}`,
      `Q${rx},${bedY + s(8)} ${rx},${bedY + s(48)}`,
      `L${rx},${uy + s(26)}`,
      `Q${rx},${uy} ${rx - s(36)},${uy}`,
      ...arches
    ].join(' ')
  }
  return [
    `M${fx},${uy}`,
    `L${fx},${hy + s(55)}`,
    `Q${fx + noseR},${hy} ${cowlStartX.value},${hy}`,
    `L${hoodEndX.value},${beltLineY.value}`,
    `L${windshieldTopX.value},${roofTopY.value}`,
    `L${rearWindowTopX.value},${roofTopY.value}`,
    `L${rearWindowBottomX.value},${beltLineY.value}`,
    `Q${rx - s(20)},${ty + s(16)} ${rx},${ty + s(56)}`,
    `L${rx},${uy + s(26)}`,
    `Q${rx},${uy} ${rx - s(36)},${uy}`,
    ...arches
  ].join(' ')
})

// 腰带线：皮卡仅覆盖驾驶室段（货箱栏板顶线由轮廓表达），其余车型贯通至 C 柱底
const beltLinePath = computed(() => {
  const endX = isPickup.value ? cabRearX2d.value : rearWindowBottomX.value
  return `M${hoodEndX.value},${beltLineY.value} L${endX},${beltLineY.value}`
})

const windowPath = computed(() => {
  if (isPickup.value) {
    // 玻璃仅覆盖驾驶室：风挡 → 车顶 → 驾驶室后窗（近直立、下沿微向前收）
    return [
      `M${hoodEndX.value},${beltLineY.value}`,
      `L${windshieldTopX.value},${roofTopY.value}`,
      `L${cabRearX2d.value},${roofTopY.value}`,
      `L${cabWindowBottomX2d.value},${beltLineY.value}`,
      'Z'
    ].join(' ')
  }
  return [
    `M${hoodEndX.value},${beltLineY.value}`,
    `L${windshieldTopX.value},${roofTopY.value}`,
    `L${rearWindowTopX.value},${roofTopY.value}`,
    `L${rearWindowBottomX.value},${beltLineY.value}`,
    'Z'
  ].join(' ')
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
