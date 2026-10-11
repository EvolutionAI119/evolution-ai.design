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

        <!-- SISA 真车参考顶线（可选叠加） -->
        <g v-if="sisaOverlay">
          <polyline :points="sisaOverlay.points" fill="none" stroke="#fbbf24" stroke-width="1.2" stroke-dasharray="6,4" vector-effect="non-scaling-stroke" opacity="0.85" />
          <text :x="s(20)" :y="padTop + 14" fill="#fbbf24" font-size="10.5" font-family="Inter, sans-serif">
            {{ t('designer.sisaLegend') }} · {{ t('designer.sisaRmse') }} {{ sisaOverlay.rmse }}
          </text>
        </g>

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
import { useI18n } from 'vue-i18n'
import {
  SISA_META,
  referenceTopOverlay,
  evalTopRMSE
} from '../config/sisaReference'

const props = defineProps({
  carParams: {
    type: Object,
    required: true
  },
  carType: {
    type: String,
    default: 'sedan'
  },
  // SISA 真车参考线叠加（referenceTopOverlay + 像真度 RMSE）
  showSisaReference: {
    type: Boolean,
    default: false
  }
})

const { t } = useI18n({ useScope: 'global' })

// ============ 画布布局：高度方向与宽度方向共同约束缩放，杜绝车顶越界裁切 ============
const svgWidth = 800
const svgHeight = 420
const padTop = 30          // 车顶上方留白（SISA 图例文字区）
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

// 双向自适应：同时满足宽度（车长）与高度（离地间隙 + 车高）约束
// 宽度预留 150px：右侧容纳 H 车高垂直标注（rearX+56），左侧容纳延伸线
const scale = computed(() => {
  const usableW = svgWidth - 150
  const usableH = groundY - padTop
  return Math.min(usableW / actualLength.value, usableH / (overallHeight.value + groundClearanceMm.value))
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

// ============ 高度分层：按车型取顶廓线比例（SUV 参考 SISA hood_height_ratio≈0.69 校正） ============
const LINE_RATIOS = {
  sedan:  { hood: 0.60, belt: 0.68, trunk: 0.64 },
  suv:    { hood: 0.66, belt: 0.74, trunk: 0.70 },
  coupe:  { hood: 0.62, belt: 0.66, trunk: 0.64 },
  sport:  { hood: 0.66, belt: 0.68, trunk: 0.72 },
  mpv:    { hood: 0.52, belt: 0.70, trunk: 0.74 },
  pickup: { hood: 0.60, belt: 0.72, trunk: 0.80 }
}
const ratios = computed(() => LINE_RATIOS[props.carType] || LINE_RATIOS.sedan)

const roofTopY = computed(() => underbodyY.value - s(overallHeight.value))
const beltLineY = computed(() => underbodyY.value - s(overallHeight.value * ratios.value.belt))
const hoodLineY = computed(() => underbodyY.value - s(overallHeight.value * ratios.value.hood))
const trunkLineY = computed(() => underbodyY.value - s(overallHeight.value * ratios.value.trunk))

// ============ 侧窗轮廓 X 关键点（全链路钳位，防止 SUV/MPV 大倾角越出车尾） ============
const hoodEndX = computed(() => Math.min(s(props.carParams.hood_length ?? 1000), rearX.value * 0.42))

// Cowl 斜坡：引擎盖面在风挡底之前沿车身上升至腰带线，使玻璃下缘落在车身表面（消除玻璃悬浮）
const cowlStartX = computed(() => {
  const rise = hoodLineY.value - beltLineY.value // 引擎盖到腰带的升高量（正值）
  const run = Math.min(s(140), Math.max(rise * 0.9, s(20)))
  return Math.max(hoodEndX.value - run, s(30))
})

const windshieldAngleRad = computed(() => (props.carParams.windshield_angle ?? 30) * Math.PI / 180)
const rearWindowAngleRad = computed(() => (props.carParams.rear_window_angle ?? 25) * Math.PI / 180)
const slantFactor = computed(() => Math.min(Math.max((props.carParams.rear_slant_angle ?? 15) / 60, 0), 1))

const tailReserve = computed(() => Math.max(s(90), rearX.value * 0.06))

// A 柱顶点：风挡水平投影，钳位保证车顶剩余空间
const windshieldTopX = computed(() => {
  const run = (beltLineY.value - roofTopY.value) / Math.tan(windshieldAngleRad.value)
  const ideal = hoodEndX.value + run
  const maxTop = rearX.value - tailReserve.value - s(120)
  return Math.min(Math.max(ideal, hoodEndX.value + s(120)), maxTop)
})

// 车顶长度：slant 越大越短（保留最小平顶段）
const maxRoofLength = computed(() => rearX.value - tailReserve.value - windshieldTopX.value)
const roofLen = computed(() => {
  const minRoof = Math.min(maxRoofLength.value, Math.max(s(400), maxRoofLength.value * 0.25))
  return Math.max(maxRoofLength.value * (1 - slantFactor.value * 0.6), minRoof)
})
const rearWindowTopX = computed(() => windshieldTopX.value + roofLen.value)

// C 柱底点：后风挡水平投影，钳位到车尾预留区之前
const rearWindowBottomX = computed(() => {
  const vertH = (beltLineY.value - roofTopY.value) * (0.5 + slantFactor.value * 0.35)
  const tan = Math.tan(rearWindowAngleRad.value)
  const run = tan > 0.05 ? vertH / tan : (rearX.value - tailReserve.value - rearWindowTopX.value)
  const maxBottom = rearX.value - tailReserve.value
  return Math.min(Math.max(rearWindowTopX.value + run, rearWindowTopX.value + s(30)), maxBottom)
})

const pillarX = computed(() => windshieldTopX.value + (rearWindowTopX.value - windshieldTopX.value) * 0.55)

// ============ 轮拱：圆心 = 轮心，开口于侧裙下缘 ============
const archRadius = computed(() => wheelRadius.value * 1.16)
const archHalfChord = computed(() => {
  const dy = Math.max(underbodyY.value - wheelCY.value, 0)
  const inner = archRadius.value * archRadius.value - dy * dy
  return Math.sqrt(Math.max(inner, (wheelRadius.value * 0.35) ** 2))
})

// ============ 闭合车身轮廓：前脸 → 引擎盖 → A 柱 → 车顶 → C 柱 → 尾门 → 底边（双侧轮拱） ============
const silhouettePath = computed(() => {
  const fx = 0
  const rx = rearX.value
  const uy = underbodyY.value
  const hy = hoodLineY.value
  const ty = trunkLineY.value
  const noseR = Math.min(s(90), s(FO.value) * 0.5)
  const fArchL = Math.max(frontWheelCX.value - archHalfChord.value, s(30))
  const fArchR = Math.min(frontWheelCX.value + archHalfChord.value, rearWheelCX.value - archHalfChord.value - s(20))
  const rArchL = rearWheelCX.value - archHalfChord.value
  const rArchR = Math.min(rearWheelCX.value + archHalfChord.value, rx - s(20))
  const ar = archRadius.value
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
    `L${rArchR},${uy}`,
    `A${ar},${ar} 0 1 0 ${rArchL},${uy}`,
    `L${fArchR},${uy}`,
    `A${ar},${ar} 0 1 0 ${fArchL},${uy}`,
    `L${fx},${uy}`,
    'Z'
  ].join(' ')
})

const beltLinePath = computed(() => {
  return `M${hoodEndX.value},${beltLineY.value} L${rearWindowBottomX.value},${beltLineY.value}`
})

const windowPath = computed(() => {
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

// ============ SISA 参考线叠加 + 像真度 RMSE ============
const sisaOverlay = computed(() => {
  if (!props.showSisaReference) return null
  const refLen = SISA_META.coordinateSystem.refLengthMm
  const refH = SISA_META.coordinateSystem.refHeightMm
  // 参考车拉伸到当前车长（README §3：归一化 x 跨尺寸比较），z 用同一长度比例 → 暴露车高比例差
  const k = (actualLength.value * scale.value) / refLen
  const points = referenceTopOverlay()
    .map(p => `${(p.x * actualLength.value * scale.value).toFixed(1)},${(groundY - p.z * refH * k).toFixed(1)}`)
    .join(' ')
  // 当前车的顶廓线（z/H 归一化，100 采样）→ 对真车 RMSE
  const n = 100
  const myTop = []
  const hoodEndMm = hoodEndX.value / scale.value
  const wsTopMm = windshieldTopX.value / scale.value
  const rwTopMm = rearWindowTopX.value / scale.value
  const rwBotMm = rearWindowBottomX.value / scale.value
  const zAt = (xMm) => {
    const toZ = (y) => (groundY - y) / scale.value / overallHeight.value
    if (xMm < hoodEndMm) return toZ(hoodLineY.value)
    if (xMm < wsTopMm) return toZ(hoodLineY.value + (roofTopY.value - hoodLineY.value) * (xMm - hoodEndMm) / Math.max(wsTopMm - hoodEndMm, 1))
    if (xMm < rwTopMm) return toZ(roofTopY.value)
    if (xMm < rwBotMm) return toZ(roofTopY.value + (beltLineY.value - roofTopY.value) * (xMm - rwTopMm) / Math.max(rwBotMm - rwTopMm, 1))
    return toZ(trunkLineY.value)
  }
  for (let i = 0; i < n; i++) myTop.push(zAt((i / (n - 1)) * actualLength.value))
  const rmse = evalTopRMSE(myTop)
  return { points, rmse: Number.isFinite(rmse) ? rmse.toFixed(3) : '—' }
})
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
