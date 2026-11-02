<template>
  <div class="car-section-2d">
    <div class="section-graphic">
      <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="section-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <pattern id="gridSection" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#gridSection)" />

        <g font-family="Inter, sans-serif">
          <text :x="centerX" :y="13" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="700">A-A</text>
          <text :x="centerX" :y="24" text-anchor="middle" fill="rgba(148,163,184,0.85)" font-size="7.5">SECTION · Z-Y</text>
          <text :x="8" :y="13" fill="rgba(148,163,184,0.75)" font-size="8">Z+ 副驾</text>
          <text :x="svgWidth - 8" :y="13" text-anchor="end" fill="rgba(148,163,184,0.75)" font-size="8">Z- 驾驶</text>
        </g>

        <g v-if="draw" font-family="Inter, sans-serif">
          <!-- 车身断面外轮廓（A-A 剖切平面上的 ±W/2 车身包络，顶部含车顶圆角） -->
          <path
            :d="draw.bodyPath" fill="rgba(74,222,128,0.05)" stroke="#4ade80" stroke-width="1.6"
            stroke-linejoin="round" vector-effect="non-scaling-stroke"
          />

          <!-- 腰带线 / 顶棚内表面 / 地毯面（Y 值与侧视布置图逐值同源） -->
          <line :x1="draw.belt.x1" :y1="draw.belt.y" :x2="draw.belt.x2" :y2="draw.belt.y" stroke="rgba(74,222,128,0.45)" stroke-width="1" stroke-dasharray="4,3" vector-effect="non-scaling-stroke" />
          <line :x1="draw.headliner.x1" :y1="draw.headliner.y" :x2="draw.headliner.x2" :y2="draw.headliner.y" stroke="rgba(203,213,225,0.55)" stroke-width="1.3" stroke-dasharray="9,4" vector-effect="non-scaling-stroke" />
          <line :x1="draw.floor.x1" :y1="draw.floor.y" :x2="draw.floor.x2" :y2="draw.floor.y" stroke="rgba(148,163,184,0.6)" stroke-width="1.2" stroke-dasharray="6,3" vector-effect="non-scaling-stroke" />

          <!-- 门板内表面（±内壁）+ 扶手带 -->
          <line
            v-for="(d, i) in draw.doorTrim" :key="'dt' + i"
            :x1="d.x" :y1="d.y0" :x2="d.x" :y2="d.y1"
            stroke="rgba(148,163,184,0.5)" stroke-width="1" vector-effect="non-scaling-stroke"
          />
          <line
            v-for="(a, i) in draw.armrests" :key="'ar' + i"
            :x1="a.x1" :y1="a.y" :x2="a.x2" :y2="a.y"
            stroke="rgba(203,213,225,0.75)" stroke-width="2" vector-effect="non-scaling-stroke"
          />

          <!-- 座椅：前排实线（A-A 剖切位），后排虚线淡色（仅作纵深参照） -->
          <g v-for="s in draw.seats" :key="'sec' + s.key">
            <rect
              :x="s.cushion.x" :y="s.cushion.y" :width="s.cushion.w" :height="s.cushion.h"
              :fill="s.solid ? 'rgba(148,163,184,0.30)' : 'none'"
              stroke="#94a3b8" :stroke-width="s.solid ? 1.1 : 0.9"
              :stroke-dasharray="s.solid ? null : '3,3'" :opacity="s.solid ? 1 : 0.45"
              vector-effect="non-scaling-stroke"
            />
            <rect
              :x="s.back.x" :y="s.back.y" :width="s.back.w" :height="s.back.h"
              :fill="s.solid ? 'rgba(148,163,184,0.30)' : 'none'"
              stroke="#94a3b8" :stroke-width="s.solid ? 1.1 : 0.9"
              :stroke-dasharray="s.solid ? null : '3,3'" :opacity="s.solid ? 1 : 0.45"
              vector-effect="non-scaling-stroke"
            />
            <rect
              :x="s.head.x" :y="s.head.y" :width="s.head.w" :height="s.head.h"
              :fill="s.solid ? 'rgba(148,163,184,0.24)' : 'none'"
              stroke="#94a3b8" :stroke-width="s.solid ? 1.1 : 0.9"
              :stroke-dasharray="s.solid ? null : '3,3'" :opacity="s.solid ? 1 : 0.45"
              vector-effect="non-scaling-stroke"
            />
            <template v-if="s.solid">
              <!-- H 点：与 3D 座椅原点同 Z、与侧视布置图同 Y -->
              <circle :cx="s.hx" :cy="s.hy" r="2.4" fill="#fbbf24" stroke="rgba(0,0,0,0.6)" stroke-width="0.8" />
              <text :x="s.hx" :y="s.hy + 10" text-anchor="middle" fill="#fbbf24" font-size="7" font-weight="700">H1</text>
            </template>
          </g>

          <!-- 中控总成：夹在双座之间，断面里首次完整可见（侧视被坐垫遮挡） -->
          <rect
            :x="draw.console.x" :y="draw.console.y" :width="draw.console.w" :height="draw.console.h"
            fill="rgba(148,163,184,0.38)" stroke="#e2e8f0" stroke-width="1.6"
            vector-effect="non-scaling-stroke"
          />
          <text
            :x="draw.consoleLabel.x" :y="draw.consoleLabel.y" text-anchor="middle"
            fill="#e2e8f0" font-size="7.5" font-weight="700" letter-spacing="0.4"
          >CONSOLE</text>

          <!-- 中控台 ↔ 座椅净距：虚线量规（数值见下方读数） -->
          <line
            v-for="(g, i) in draw.clearance" :key="'cg' + i"
            :x1="g.x1" :y1="g.y" :x2="g.x2" :y2="g.y"
            stroke="rgba(251,191,36,0.95)" stroke-width="1.2" vector-effect="non-scaling-stroke"
          />

          <!-- 地面线 -->
          <line :x1="draw.ground.x1" :y1="draw.ground.y" :x2="draw.ground.x2" :y2="draw.ground.y" stroke="rgba(255,255,255,0.22)" stroke-width="1" vector-effect="non-scaling-stroke" />

          <!-- 尺寸标注：整车宽 W / 座舱内宽 IW（与车宽参数同源） -->
          <g font-size="8">
            <line :x1="draw.dims.wLine.x1" :y1="draw.dims.wLine.y" :x2="draw.dims.wLine.x2" :y2="draw.dims.wLine.y" stroke="rgba(255,255,255,0.55)" stroke-width="1" vector-effect="non-scaling-stroke" />
            <line :x1="draw.dims.wLine.x1" :y1="draw.dims.wLine.ext0" :x2="draw.dims.wLine.x1" :y2="draw.dims.wLine.ext1" stroke="rgba(255,255,255,0.3)" stroke-width="1" vector-effect="non-scaling-stroke" />
            <line :x1="draw.dims.wLine.x2" :y1="draw.dims.wLine.ext0" :x2="draw.dims.wLine.x2" :y2="draw.dims.wLine.ext1" stroke="rgba(255,255,255,0.3)" stroke-width="1" vector-effect="non-scaling-stroke" />
            <text :x="draw.dims.wLabel.x" :y="draw.dims.wLabel.y" text-anchor="middle" fill="rgba(255,255,255,0.85)" font-weight="600">{{ draw.dims.wLabel.text }}</text>

            <line :x1="draw.dims.iwLine.x1" :y1="draw.dims.iwLine.y" :x2="draw.dims.iwLine.x2" :y2="draw.dims.iwLine.y" stroke="rgba(255,255,255,0.42)" stroke-width="1" vector-effect="non-scaling-stroke" />
            <text :x="draw.dims.iwLabel.x" :y="draw.dims.iwLabel.y" text-anchor="middle" fill="rgba(255,255,255,0.7)">{{ draw.dims.iwLabel.text }}</text>
          </g>
        </g>
      </svg>
    </div>

    <!-- 读数区（HTML 文本，不随 SVG 缩放，窄栏下仍清晰可读；单位 mm） -->
    <div v-if="readout" class="section-readout">
      <div class="readout-row">
        <span class="readout-key">CONSOLE</span>
        <span class="readout-val">{{ readout.console }}</span>
      </div>
      <div class="readout-row">
        <span class="readout-key">CLEAR</span>
        <span class="readout-val warn">{{ readout.clear }}</span>
      </div>
      <div class="readout-row">
        <span class="readout-key">SEAT W</span>
        <span class="readout-val">{{ readout.seatWidth }}</span>
      </div>
      <div class="readout-row">
        <span class="readout-key">IW</span>
        <span class="readout-val">{{ readout.cabinWidth }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { deriveCarProfile } from '../utils/carProfile.js'
import { deriveSectionLayout } from '../utils/carInteriorLayout.js'
import { createFrontViewProjection } from '../utils/car2dProjection.js'

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

// 画布：窄侧栏用竖长条；上方断面标题带、下方两层宽度尺寸标注
const svgWidth = 220
const svgHeight = 206
const padTop = 26
const dimAreaH = 30
const groundY = svgHeight - dimAreaH
const centerX = svgWidth / 2

const profile = computed(() => deriveCarProfile(props.carParams, props.carType))
const section = computed(() => deriveSectionLayout(profile.value))

// 双向自适应：车宽与「车身底 → 车顶」共同约束缩放
const scale = computed(() => {
  const s = section.value
  if (!s) return 90
  const usableW = svgWidth - 32
  const usableH = groundY - padTop - 8
  return Math.min(usableW / s.width, usableH / Math.max(s.roofTopY - s.bodyBottomY, 0.5))
})
const proj = computed(() => createFrontViewProjection(centerX, groundY, scale.value))

const draw = computed(() => {
  const s = section.value
  if (!s) return null
  const p = proj.value
  const yOf = (y) => p.toY(y)

  const roofY = yOf(s.roofTopY)
  const bottomY = yOf(s.bodyBottomY)
  const xL = p.toX(s.halfBody)    // Z+（副驾侧）在画面左侧
  const xR = p.toX(-s.halfBody)   // Z-（驾驶侧）在画面右侧
  const fillet = Math.max(0.05 * p.pxPerM, 4)

  // 外轮廓：左下 → 左上圆角 → 顶边 → 右上圆角 → 右下 → 闭合
  const bodyPath = [
    `M${xL},${bottomY}`,
    `L${xL},${roofY + fillet}`,
    `Q${xL},${roofY} ${xL + fillet},${roofY}`,
    `L${xR - fillet},${roofY}`,
    `Q${xR},${roofY} ${xR},${roofY + fillet}`,
    `L${xR},${bottomY}`,
    'Z'
  ].join(' ')

  const xInnerL = p.toX(s.halfInterior)
  const xInnerR = p.toX(-s.halfInterior)

  // 座椅：坐垫 / 靠背 / 头枕三条 Z 区间；前排（A-A 剖切位）实线，其后虚线淡色
  const seats = []
  for (const r of s.rows) {
    for (const seat of r.seats) {
      seats.push({
        key: `${r.row}-${seat.z.toFixed(3)}`,
        solid: r.row === 1,
        cushion: p.rect(seat.z0, seat.z1, r.cushionY0, r.cushionY1),
        back: p.rect(seat.z0, seat.z1, r.hPointY, r.backTopY),
        head: p.rect(seat.z - r.headrestWidth / 2, seat.z + r.headrestWidth / 2, r.headrestY0, r.headrestTopY),
        hx: p.toX(seat.z),
        hy: yOf(r.hPointY)
      })
    }
  }

  const consoleRect = p.rect(s.console.z0, s.console.z1, s.console.bottomY, s.console.topY)

  // 净距量规：从中控台两侧边缘引到相邻座椅内缘（数值在下方读数区）
  const clearance = []
  for (const seat of s.rows[0].seats) {
    const onRight = seat.z0 > s.console.z1
    const xa = p.toX(onRight ? s.console.z1 : s.console.z0)
    const xb = p.toX(onRight ? seat.z0 : seat.z1)
    clearance.push({ x1: xa, x2: xb, y: consoleRect.y - 5 })
  }

  const wLineY = groundY + 12
  const iwLineY = groundY + 28

  return {
    bodyPath,
    belt: { x1: xInnerL, x2: xInnerR, y: yOf(s.beltLineY) },
    // 顶棚内表面（车顶下 20mm）与地毯面（地板 +10mm）：与 3D 内饰件同源（deriveInteriorTrim）
    headliner: { x1: xInnerL, x2: xInnerR, y: yOf(s.headlinerY) },
    floor: { x1: xInnerL, x2: xInnerR, y: yOf(s.carpetY) },
    doorTrim: [
      { x: xInnerL, y0: yOf(s.beltLineY), y1: yOf(s.floorY) },
      { x: xInnerR, y0: yOf(s.beltLineY), y1: yOf(s.floorY) }
    ],
    armrests: [
      { x1: xInnerL, x2: xInnerL + 0.10 * p.pxPerM, y: yOf(s.door.armrestY) },
      { x1: xInnerR, x2: xInnerR - 0.10 * p.pxPerM, y: yOf(s.door.armrestY) }
    ],
    seats,
    console: consoleRect,
    consoleLabel: { x: consoleRect.x + consoleRect.w / 2, y: consoleRect.y - 6 },
    clearance,
    ground: { x1: xL - 6, x2: xR + 6, y: groundY },
    dims: {
      wLine: { x1: xL, x2: xR, y: wLineY, ext0: bottomY, ext1: wLineY + 4 },
      wLabel: { x: centerX, y: wLineY - 2, text: `W ${Math.round(s.width * 1000)}` },
      iwLine: { x1: xInnerL, x2: xInnerR, y: iwLineY },
      iwLabel: { x: centerX, y: iwLineY - 2, text: `IW ${Math.round(s.metrics.cabinWidth * 1000)}` }
    }
  }
})

const readout = computed(() => {
  const s = section.value
  if (!s) return null
  return {
    console: Math.round(s.metrics.consoleWidth * 1000),
    clear: s.metrics.seatToConsoleGap == null ? '-' : Math.round(s.metrics.seatToConsoleGap * 1000),
    seatWidth: Math.round(s.metrics.seatWidth * 1000),
    cabinWidth: Math.round(s.metrics.cabinWidth * 1000)
  }
})
</script>

<style scoped>
.car-section-2d {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
}

.section-graphic {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-radius: 8px;
  overflow: hidden;
}

.section-svg {
  width: 100%;
  height: 100%;
}

.section-readout {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 10px;
  padding: 4px 6px;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.08);
}

.readout-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 4px;
  font-size: 9px;
  line-height: 1.35;
}

.readout-key {
  color: rgba(148, 163, 184, 0.95);
  letter-spacing: 0.4px;
}

.readout-val {
  color: #e2e8f0;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.readout-val.warn {
  color: #fbbf24;
}
</style>
