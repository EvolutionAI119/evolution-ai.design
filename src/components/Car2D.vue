<template>
  <div class="car-2d-container">
    <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" class="car-2d-svg">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
      
      <g :transform="`translate(${offsetX}, ${offsetY})`">
        <path :d="roofPath" fill="none" stroke="#4ade80" stroke-width="1.5" stroke-linecap="round" />
        <path :d="hoodPath" fill="none" stroke="#4ade80" stroke-width="1.5" stroke-linecap="round" />
        <path :d="trunkPath" fill="none" stroke="#4ade80" stroke-width="1.5" stroke-linecap="round" />
        <path :d="beltLinePath" fill="none" stroke="rgba(74,222,128,0.6)" stroke-width="1" stroke-dasharray="4,3" />
        <path :d="windowPath" fill="rgba(59,130,246,0.1)" stroke="#3b82f6" stroke-width="1" />
        <path :d="frontWheelPath" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.5" />
        <path :d="rearWheelPath" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.5" />
        <path :d="frontWheelInnerPath" fill="none" stroke="rgba(74,222,128,0.5)" stroke-width="1" />
        <path :d="rearWheelInnerPath" fill="none" stroke="rgba(74,222,128,0.5)" stroke-width="1" />
        <line :x1="groundLineX1" :y1="groundLineY" :x2="groundLineX2" :y2="groundLineY" stroke="rgba(255,255,255,0.2)" stroke-width="1" />
        
        <line :x1="frontX" :y1="groundLineY - 8" :x2="frontWheelX" :y2="groundLineY - 8" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="4,2" />
        <line :x1="frontX" :y1="groundLineY - 12" :x2="frontX" :y2="groundLineY - 4" stroke="#00ff88" stroke-width="1.5" />
        <line :x1="frontWheelX" :y1="groundLineY - 12" :x2="frontWheelX" :y2="groundLineY - 4" stroke="#00ff88" stroke-width="1.5" />
        <text :x="frontWheelX / 2" :y="groundLineY - 20" text-anchor="middle" fill="#00ff88" font-size="11" font-family="Inter, sans-serif" font-weight="600">FO: {{ FO }}mm</text>

        <line :x1="rearWheelX" :y1="groundLineY - 8" :x2="rearX" :y2="groundLineY - 8" stroke="#ff6b6b" stroke-width="1.5" stroke-dasharray="4,2" />
        <line :x1="rearWheelX" :y1="groundLineY - 12" :x2="rearWheelX" :y2="groundLineY - 4" stroke="#ff6b6b" stroke-width="1.5" />
        <line :x1="rearX" :y1="groundLineY - 12" :x2="rearX" :y2="groundLineY - 4" stroke="#ff6b6b" stroke-width="1.5" />
        <text :x="(rearWheelX + rearX) / 2" :y="groundLineY - 20" text-anchor="middle" fill="#ff6b6b" font-size="11" font-family="Inter, sans-serif" font-weight="600">RO: {{ RO }}mm</text>

        <text :x="wheelBaseX" :y="dimTextY" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-size="11" font-family="Inter, sans-serif">WB {{ WB }}mm</text>
        <text :x="lengthX" :y="dimTextY + 16" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-size="11" font-family="Inter, sans-serif">L {{ actualLength }}mm</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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

const svgWidth = 800
const svgHeight = 280
const offsetX = 40
const offsetY = 40
const groundLineY = 200
const dimTextY = 240

const FO = computed(() => props.carParams.front_overhang || 1000)
const RO = computed(() => props.carParams.rear_overhang || 1000)
const WB = computed(() => props.carParams.wheel_base)

const actualLength = computed(() => FO.value + WB.value + RO.value)

const scale = computed(() => {
  const usableWidth = svgWidth - offsetX * 2
  return usableWidth / actualLength.value
})

const s = (val) => val * scale.value

const frontWheelX = computed(() => s(FO.value))
const rearWheelX = computed(() => s(FO.value + WB.value))
const wheelBaseX = computed(() => (frontWheelX.value + rearWheelX.value) / 2)

const frontX = computed(() => 0)
const rearX = computed(() => s(actualLength.value))
const lengthX = computed(() => rearX.value / 2)

const wheelRadius = computed(() => s(props.carParams.wheel_diameter / 2))
const groundClearance = computed(() => s(props.carParams.ground_clearance))

const bodyTopY = computed(() => groundLineY - groundClearance.value - s(props.carParams.overall_height * 0.4))
const roofTopY = computed(() => groundLineY - groundClearance.value - s(props.carParams.overall_height * 0.75))
const beltLineY = computed(() => groundLineY - groundClearance.value - s(props.carParams.overall_height * 0.55))

const hoodEndX = computed(() => s(props.carParams.hood_length))
const trunkLength = computed(() => Math.min(s(props.carParams.rear_overhang * 0.6), s(props.carParams.hood_length * 0.5)))
const trunkStartX = computed(() => rearX.value - trunkLength.value)

const windshieldAngleRad = computed(() => props.carParams.windshield_angle * Math.PI / 180)
const rearWindowAngleRad = computed(() => props.carParams.rear_window_angle * Math.PI / 180)
const rearSlantAngleRad = computed(() => props.carParams.rear_slant_angle * Math.PI / 180)

const windshieldHeight = computed(() => (beltLineY.value - roofTopY.value) * 0.7)
const windshieldTopX = computed(() => {
  return hoodEndX.value + windshieldHeight.value / Math.tan(windshieldAngleRad.value)
})

const maxRoofLength = computed(() => trunkStartX.value - windshieldTopX.value)
const slantFactor = computed(() => Math.min(Math.max(props.carParams.rear_slant_angle / 60, 0), 1))
const roofLen = computed(() => Math.max(maxRoofLength.value * (1 - slantFactor.value * 0.7), s(800)))
const rearWindowTopX = computed(() => windshieldTopX.value + roofLen.value)

const rearWindowVertHeight = computed(() => beltLineY.value - roofTopY.value)
const rearWindowHeightRatio = computed(() => 0.5 + slantFactor.value * 0.3)
const rearWindowHeight = computed(() => rearWindowVertHeight.value * rearWindowHeightRatio.value)
const rearWindowBottomX = computed(() => {
  return rearWindowTopX.value + rearWindowHeight.value / Math.tan(rearWindowAngleRad.value)
})

const roofPath = computed(() => {
  return `M${windshieldTopX.value},${roofTopY.value} L${rearWindowTopX.value},${roofTopY.value}`
})

const hoodPath = computed(() => {
  return `M${frontX.value},${bodyTopY.value + s(20)} Q${frontX.value + s(100)},${bodyTopY.value} ${hoodEndX.value},${beltLineY.value}`
})

const trunkPath = computed(() => {
  return `M${rearWindowBottomX.value},${beltLineY.value} Q${rearX.value - s(80)},${bodyTopY.value} ${rearX.value},${bodyTopY.value + s(30)}`
})

const beltLinePath = computed(() => {
  return `M${hoodEndX.value},${beltLineY.value} L${rearWindowBottomX.value},${beltLineY.value}`
})

const windowPath = computed(() => {
  return `M${hoodEndX.value},${beltLineY.value} L${windshieldTopX.value},${roofTopY.value} L${rearWindowTopX.value},${roofTopY.value} L${rearWindowBottomX.value},${beltLineY.value} Z`
})

const frontWheelPath = computed(() => {
  return `M${frontWheelX.value - wheelRadius.value},${groundLineY - groundClearance.value} 
          A${wheelRadius.value},${wheelRadius.value} 0 1,0 ${frontWheelX.value + wheelRadius.value},${groundLineY - groundClearance.value}`
})

const rearWheelPath = computed(() => {
  return `M${rearWheelX.value - wheelRadius.value},${groundLineY - groundClearance.value} 
          A${wheelRadius.value},${wheelRadius.value} 0 1,0 ${rearWheelX.value + wheelRadius.value},${groundLineY - groundClearance.value}`
})

const frontWheelInnerPath = computed(() => {
  const r = wheelRadius.value * 0.5
  const cy = groundLineY - groundClearance.value - wheelRadius.value
  return `M${frontWheelX.value - r},${cy} A${r},${r} 0 1,0 ${frontWheelX.value + r},${cy} A${r},${r} 0 1,0 ${frontWheelX.value - r},${cy}`
})

const rearWheelInnerPath = computed(() => {
  const r = wheelRadius.value * 0.5
  const cy = groundLineY - groundClearance.value - wheelRadius.value
  return `M${rearWheelX.value - r},${cy} A${r},${r} 0 1,0 ${rearWheelX.value + r},${cy} A${r},${r} 0 1,0 ${rearWheelX.value - r},${cy}`
})

const groundLineX1 = computed(() => frontX.value - 20)
const groundLineX2 = computed(() => rearX.value + 20)
</script>

<style scoped>
.car-2d-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0f;
  border-radius: 8px;
}

.car-2d-svg {
  width: 100%;
  height: 100%;
}
</style>
