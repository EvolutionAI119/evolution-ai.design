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

        <!-- 内饰布置层（与 3D 同源 carInteriorLayout）：门板 / 地板 / 仪表台 / 座椅 / 中控 / 方向盘 + H 点 -->
        <g v-if="interior2d" class="interior-layer">
          <!-- 门板内表面（沿座舱段走向，含扶手带） -->
          <rect
            :x="interior2d.doorPanel.x" :y="interior2d.doorPanel.y"
            :width="interior2d.doorPanel.w" :height="interior2d.doorPanel.h"
            fill="rgba(148,163,184,0.08)" stroke="rgba(148,163,184,0.42)" stroke-width="1"
            stroke-dasharray="4,3" vector-effect="non-scaling-stroke"
          />
          <line
            :x1="interior2d.doorPanel.x" :y1="interior2d.doorPanel.armrestY"
            :x2="interior2d.doorPanel.x + interior2d.doorPanel.w" :y2="interior2d.doorPanel.armrestY"
            stroke="rgba(203,213,225,0.6)" stroke-width="2" vector-effect="non-scaling-stroke"
          />

          <!-- 座舱地板线（地板面高度由 carInteriorLayout.deriveFloorY 推导） -->
          <line
            :x1="interior2d.floor.x0" :y1="interior2d.floor.y"
            :x2="interior2d.floor.x1" :y2="interior2d.floor.y"
            stroke="rgba(148,163,184,0.55)" stroke-width="1.4" stroke-dasharray="6,3"
            vector-effect="non-scaling-stroke"
          />

          <!-- 地毯面（地板 +10mm）与顶棚内表面（车顶 -20mm）：与 3D createInteriorTrim 同源 -->
          <g v-if="interior2d.trim">
            <rect
              :x="interior2d.trim.carpet.x" :y="interior2d.trim.carpet.y"
              :width="interior2d.trim.carpet.w" :height="Math.max(interior2d.trim.carpet.h, 1)"
              fill="rgba(251,146,60,0.28)" stroke="rgba(251,146,60,0.6)" stroke-width="0.8"
              vector-effect="non-scaling-stroke"
            />
            <line
              :x1="interior2d.trim.headliner.x" :y1="interior2d.trim.headliner.y + interior2d.trim.headliner.h"
              :x2="interior2d.trim.headliner.x + interior2d.trim.headliner.w" :y2="interior2d.trim.headliner.y + interior2d.trim.headliner.h"
              stroke="rgba(203,213,225,0.5)" stroke-width="1.3" stroke-dasharray="9,4"
              vector-effect="non-scaling-stroke"
            />
          </g>

          <!-- 仪表台 IP -->
          <rect
            :x="interior2d.ip.x" :y="interior2d.ip.y" :width="interior2d.ip.w" :height="interior2d.ip.h"
            fill="rgba(148,163,184,0.22)" stroke="#94a3b8" stroke-width="1.2"
            vector-effect="non-scaling-stroke"
          />
          <text :x="interior2d.ipLabel.x" :y="interior2d.ipLabel.y" text-anchor="end" fill="#cbd5e1" font-family="Inter, sans-serif" font-size="9" font-weight="600">IP</text>

          <!-- 座椅（每排一组：坐垫 / 靠背 / 头枕 + H 点） -->
          <g v-for="s in interior2d.rows" :key="'seat' + s.row">
            <rect
              :x="s.cushion.x" :y="s.cushion.y" :width="s.cushion.w" :height="s.cushion.h"
              fill="rgba(148,163,184,0.30)" stroke="#94a3b8" stroke-width="1.1"
              vector-effect="non-scaling-stroke"
            />
            <path :d="s.backrest" fill="rgba(148,163,184,0.30)" stroke="#94a3b8" stroke-width="1.1" vector-effect="non-scaling-stroke" />
            <path :d="s.headrest" fill="rgba(148,163,184,0.24)" stroke="#94a3b8" stroke-width="1.1" vector-effect="non-scaling-stroke" />
            <circle :cx="s.hx" :cy="s.hy" r="2.6" fill="#fbbf24" stroke="rgba(0,0,0,0.6)" stroke-width="0.8" />
            <text :x="s.hx + 5" :y="s.hy + 3.5" fill="#fbbf24" font-family="Inter, sans-serif" font-size="8" font-weight="600">H{{ s.row }}</text>
          </g>

          <!-- 安全带固定点：上固定点（B 柱 / 后侧柱）、下固定点（地板侧），与 3D 网格同坐标 -->
          <g v-if="interior2d.trim" class="belt-layer">
            <rect
              v-for="b in interior2d.trim.belts" :key="b.key"
              :x="b.x - (b.upper ? 2.6 : 2)" :y="b.y - (b.upper ? 1.6 : 2)"
              :width="b.upper ? 5.2 : 4" :height="b.upper ? 3.2 : 4"
              :fill="b.upper ? 'rgba(154,164,178,0.92)' : 'rgba(154,164,178,0.6)'"
              stroke="rgba(15,18,24,0.85)" stroke-width="0.6" vector-effect="non-scaling-stroke"
            />
          </g>

          <!-- 中控总成 CONSOLE（前排双座之间，半透明叠加在座椅之后以便读数） -->
          <rect
            :x="interior2d.console.x" :y="interior2d.console.y"
            :width="interior2d.console.w" :height="interior2d.console.h"
            fill="rgba(148,163,184,0.18)" stroke="rgba(148,163,184,0.85)" stroke-width="1"
            vector-effect="non-scaling-stroke"
          />
          <text
            :x="interior2d.consoleLabel.x" :y="interior2d.consoleLabel.y" text-anchor="middle"
            fill="#94a3b8" font-family="Inter, sans-serif" font-size="7.5" font-weight="600"
          >CONSOLE</text>

          <!-- 后排中央低通道（连通前后排，100mm 高；不侵入两侧座椅 Z 区间） -->
          <rect
            v-if="interior2d.trim"
            :x="interior2d.trim.tunnelRear.x" :y="interior2d.trim.tunnelRear.y"
            :width="interior2d.trim.tunnelRear.w" :height="interior2d.trim.tunnelRear.h"
            fill="rgba(148,163,184,0.16)" stroke="rgba(148,163,184,0.55)" stroke-width="0.8"
            vector-effect="non-scaling-stroke"
          />

          <!-- 方向盘（锚点与 3D 圆环同源：steerWheel.x/y/r） -->
          <circle
            :cx="interior2d.wheel.cx" :cy="interior2d.wheel.cy" :r="interior2d.wheel.r"
            fill="rgba(15,18,24,0.45)" stroke="#cbd5e1" stroke-width="1.4" vector-effect="non-scaling-stroke"
          />

          <!-- A-A 剖切线：横断面（Z-Y 右视图）的取图位置 = 过前排 H 点 -->
          <line
            :x1="interior2d.cut.x" :y1="interior2d.cut.y0" :x2="interior2d.cut.x" :y2="interior2d.cut.y1"
            stroke="rgba(203,213,225,0.5)" stroke-width="1" stroke-dasharray="7,4"
            vector-effect="non-scaling-stroke"
          />
          <text :x="interior2d.cut.x + 3" :y="interior2d.cut.y0 - 3" fill="rgba(203,213,225,0.8)" font-family="Inter, sans-serif" font-size="8" font-weight="700">A</text>
          <text :x="interior2d.cut.x + 3" :y="interior2d.cut.y1 + 11" fill="rgba(203,213,225,0.8)" font-family="Inter, sans-serif" font-size="8" font-weight="700">A</text>
        </g>

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
        <!-- 玻璃分缝工程标注：G1/G2/G3 = 门缝坐标向上延伸进 DLO，δ = 门缝宽（玻璃片各退 δ/2） -->
        <g font-family="Inter, sans-serif">
          <text :x="8" :y="seamNoteY" fill="rgba(147,197,253,0.78)" font-size="9.5">
            {{ seamNoteText }}
          </text>
          <g v-for="g in glassSeams2d" :key="'ga' + g.id">
            <circle :cx="g.x" :cy="g.y2" r="2" fill="#93c5fd" />
            <line
              :x1="g.x" :y1="g.y2 - 2" :x2="g.x" :y2="seamTickY"
              stroke="rgba(147,197,253,0.5)" stroke-width="1"
              vector-effect="non-scaling-stroke"
            />
            <text :x="g.x + 6" :y="seamLabelY" fill="#93c5fd" font-size="10">
              <tspan font-weight="700">{{ g.id }}</tspan>
              <tspan dx="4">{{ g.label }}</tspan>
            </text>
          </g>
        </g>
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
import { deriveInteriorLayout, deriveInteriorTrim } from '../utils/carInteriorLayout.js'
import { createSideViewProjection } from '../utils/car2dProjection.js'
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
const svgHeight = 450
const padTop = 66          // 车顶上方标注带（玻璃分缝引出线 + 标签）
const dimAreaH = 84        // 地面线下方标注区（FO/RO · WB · L 三行尺寸）
const groundY = svgHeight - dimAreaH

// 玻璃分缝标注行（车顶上方，自下而上：引出线顶端 → 缝标签 → 说明文字）
const seamTickY = 36       // 引出线顶端
const seamLabelY = 30      // G1/G2/G3 标签基线
const seamNoteY = 12       // 分缝逻辑说明基线

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
  handleXRatio: props.carParams.handle_x_ratio,
  carType: props.carType
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
  const seams = [
    { id: 'G1', x3d: dl2d.value.frontSeamX, label: '前门缝' },
    { id: 'G2', x3d: dl2d.value.midSeamX, label: isPickup.value ? '驾驶室后缝' : 'B柱缝' }
  ]
  if (dl2d.value.rearSeamX !== null) {
    seams.push({ id: 'G3', x3d: dl2d.value.rearSeamX, label: '后门缝' })
  }
  return seams.map((g) => ({
    ...g,
    x: toX(g.x3d),
    y1: doorSeamTopY2d.value,
    y2: dloTopY2d(g.x3d)
  }))
})

// 玻璃分缝说明：缝坐标与门缝同源，缝宽取 door_seam_width，玻璃片两侧各退半个缝宽
const seamWidthMm = computed(() => {
  const w = Number(props.carParams.door_seam_width ?? 8)
  return Math.min(Math.max(Number.isFinite(w) ? w : 8, 2), 20)
})
const seamNoteText = computed(() => {
  const motion = isPickup.value ? '门片随门外摆，A柱前片与后侧窗固定' : '前/后门片随门外摆，A/C柱片固定'
  return `侧窗玻璃分缝 = 门缝坐标延伸 · δ ${seamWidthMm.value}mm（各退半缝）· ${motion}`
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
// 3D 米 → SVG 像素的唯一换算口（与 carInteriorLayout.spec.js 共用，保证 2D 可反解回 3D）
const proj = computed(() => createSideViewProjection(profile.value, pxPerM.value, groundY))
const outX = (x) => proj.value.toX(x)
const outY = (y) => proj.value.toY(y)
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

// ============ 内饰布置（2D 布置图）：与 3D 网格同源 carInteriorLayout ============
// 所有锚点都由 deriveInteriorLayout(P) 输出（单位米），此处只做「米 → SVG」的同一套镜像/翻转换算，
// 因此 2D 布置图与 3D 模型的 X/Y 完全一致（对齐断言见 carInteriorLayout.spec.js）。
const interior2d = computed(() => {
  const L = deriveInteriorLayout(profile.value)
  if (!L) return null
  const p = proj.value
  const T = deriveInteriorTrim(profile.value)

  return {
    rows: L.rows.map((r) => ({
      row: r.row,
      cushion: p.rect(r.envelope.cushion.x0, r.envelope.cushion.x1, r.envelope.cushion.y0, r.envelope.cushion.y1),
      backrest: p.poly(r.envelope.backrest.points),
      headrest: p.poly(r.envelope.headrest.points),
      hx: p.toX(r.x),
      hy: p.toY(r.hPointY),
      labelY: p.toY(r.envelope.topY) + 10
    })),
    ip: p.rect(L.ip.rearX, L.ip.frontX, L.ip.bottomY, L.ip.topY),
    console: p.rect(L.console.rearX, L.console.frontX, L.console.bottomY, L.console.topY),
    doorPanel: {
      ...p.rect(L.doorPanel.x0, L.doorPanel.x1, L.doorPanel.y0, L.doorPanel.y1),
      armrestY: p.toY(L.doorPanel.armrestY)
    },
    floor: {
      y: p.toY(L.floorY),
      x0: p.toX(L.doorPanel.x1),
      x1: p.toX(L.doorPanel.x0)
    },
    // 剩余内饰件（与 3D createInteriorTrim 同一取数口 deriveInteriorTrim）
    trim: T ? {
      carpet: p.rect(T.carpet.x0, T.carpet.x1, T.carpet.y0, T.carpet.y1),
      headliner: p.rect(T.headliner.x0, T.headliner.x1, T.headliner.y0, T.headliner.y1),
      tunnelRear: p.rect(T.tunnel.rear.x0, T.tunnel.rear.x1, T.tunnel.rear.y0, T.tunnel.rear.y1),
      belts: T.belts.map((b) => ({
        key: `belt-${b.row}-${b.side}-${b.kind}`,
        x: p.toX(b.x),
        y: p.toY(b.y),
        upper: b.kind === 'upper'
      }))
    } : null,
    wheel: { cx: p.toX(L.steerWheel.x), cy: p.toY(L.steerWheel.y), r: L.steerWheel.r * p.pxPerM },
    // A-A 剖切线：位置 = 前排 H 点（与 CarSection2D 的取图平面同一 X）
    cut: {
      x: p.toX(L.rows[0].x),
      y0: p.toY(profile.value.roofTopY ?? profile.value.H),
      y1: p.toY(0)
    },
    ipLabel: { x: p.toX(L.ip.rearX) - 4, y: p.toY(L.ip.topY) + 11 },
    consoleLabel: {
      x: (p.toX(L.console.rearX) + p.toX(L.console.frontX)) / 2,
      y: p.toY(L.console.bottomY) - 3
    }
  }
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
