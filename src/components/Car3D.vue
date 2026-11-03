<template>
  <div ref="containerRef" class="car-3d-container">
    <div class="view-controls">
      <button
        v-for="view in viewAngles"
        :key="view.key"
        type="button"
        class="view-btn"
        :class="{ active: currentView === view.key }"
        @click="setViewAngle(view.key)"
        :title="view.label"
        :aria-label="view.label"
      >
        {{ view.icon }}
      </button>
    </div>
    <div class="control-buttons">
      <div class="ctrl-btn" @click="resetView" :title="t('designer.viewerReset')" :aria-label="t('designer.viewerReset')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
          <path d="M3 3v5h5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleWireframe" :class="{ active: wireframeMode }" :title="t('designer.viewerWireframe')" :aria-label="t('designer.viewerWireframe')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18M9 3v18M3 15h18M15 3v18"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleAutoRotate" :class="{ active: autoRotate }" :title="t('designer.viewerAutoRotate')" :aria-label="t('designer.viewerAutoRotate')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
        </svg>
      </div>
      <div class="ctrl-btn" @click="toggleFullscreen" :class="{ active: isFullscreen }" :title="t('designer.viewerFullscreen')" :aria-label="t('designer.viewerFullscreen')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
        </svg>
      </div>
      <div
        class="ctrl-btn door-btn"
        :class="{ active: doorOpen }"
        :title="t('designer.doorToggle')"
        :aria-label="t('designer.doorToggle')"
        @click="toggleDoor"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="4" width="13" height="16" rx="1"/>
          <path d="M16 8l4-2v12l-4-2"/>
          <circle cx="13" cy="12" r="0.8" fill="currentColor"/>
        </svg>
      </div>
      <div
        v-if="flightAvailable"
        class="ctrl-btn vtol-btn"
        :class="{ active: flightEngaged }"
        :title="flightEngaged ? t('designer.vtolDisengage') : t('designer.vtolEngage')"
        :aria-label="flightEngaged ? t('designer.vtolDisengage') : t('designer.vtolEngage')"
        @click="toggleFlight"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20V7"/>
          <path d="M8 11l4-4 4 4"/>
          <path d="M4 20h16"/>
        </svg>
      </div>
      <template v-if="flightEngaged">
        <div
          class="ctrl-btn turn-btn"
          :class="{ busy: yawTurning }"
          :title="t('designer.turnLeft90')"
          :aria-label="t('designer.turnLeft90')"
          @click="startTurn(-90)"
        >↺</div>
        <div
          class="ctrl-btn turn-btn"
          :class="{ busy: yawTurning }"
          :title="t('designer.turnRight90')"
          :aria-label="t('designer.turnRight90')"
          @click="startTurn(90)"
        >↻</div>
        <div
          class="ctrl-btn turn-btn turn-full"
          :class="{ busy: yawTurning }"
          :title="t('designer.fullTurn360')"
          :aria-label="t('designer.fullTurn360')"
          @click="startTurn(360)"
        >360°</div>
      </template>
    </div>
    <div class="status-bar">
      <span class="view-label">{{ currentViewLabel }}</span>
      <span class="status-item">DAYLIGHT</span>
      <span class="status-item">PERSPECTIVE</span>
      <span v-if="flightEngaged" class="status-item vtol-status">VTOL HOVER</span>
      <span
        v-if="flightEngaged && flightEnergy"
        class="status-item vtol-status energy-status"
      >{{ flightEnergy.kw }} kW · ×{{ flightEnergy.mult.toFixed(1) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCarScene } from '../composables/useCarScene.js'

const { t } = useI18n()

const props = defineProps({
  carParams: {
    type: Object,
    required: true
  },
  carType: {
    type: String,
    default: 'sedan'
  },
  carColor: {
    type: String,
    default: '#4ade80'
  },
  viewAngle: {
    type: String,
    default: 'perspective'
  },
  wireframe: {
    type: Boolean,
    default: false
  },
  // 车门是否处于打开位（外部可绑开门按钮状态）：
  // 门洞常挖、门板为唯一门几何；本 prop 仅作外部状态同步入口，几何不受影响。
  doorOpened: {
    type: Boolean,
    default: false
  },
  // 后端真实 NURBS 采样网格（Designer 生成后传入）：
  // { parts: [{name,type,points:[[[x,y,z]]](canonical,mm),color,opacity}],
  //   wheels: [{radius,width,position:{x,y,z}(author,mm)}] }
  // 缺省时走 2D 轮廓 ExtrudeGeometry 近似路径（Demo 页/游客态）
  nurbsMesh: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:viewAngle', 'update:wireframe'])

const containerRef = ref(null)
const isFullscreen = ref(false)

const viewAngles = [
  { key: 'front', label: 'Front', icon: 'F' },
  { key: 'rear', label: 'Rear', icon: 'R' },
  { key: 'left', label: 'Left', icon: 'L' },
  { key: 'right', label: 'Right', icon: 'R' },
  { key: 'top', label: 'Top', icon: 'T' },
  { key: 'bottom', label: 'Bottom', icon: 'B' },
  { key: 'isometric', label: 'Isometric', icon: 'I' },
  { key: 'perspective', label: 'Perspective', icon: 'P' }
]

// 场景编排全部在 composables/useCarScene.js（P4 拆分）：createCar / initScene / updateCar /
// 生命周期 / watch 与 VTOL、车门、视角动作。props 只读经 getter 传入，emit 经回调转发，
// composable 不依赖组件实例。返回的 UI refs 直接解构回模板（保持 ref，不包 computed）。
const {
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
} = useCarScene({
  containerRef,
  getProps: () => props,
  emitViewAngle: (v) => emit('update:viewAngle', v),
  emitWireframe: (v) => emit('update:wireframe', v)
})

const currentViewLabel = computed(() => {
  const v = viewAngles.find(v => v.key === currentView.value)
  return v ? v.label.toUpperCase() : 'PERSPECTIVE'
})

// 全屏是纯 UI 行为（document API + 组件态），不涉及场景生命周期，留在组件内。
const toggleFullscreen = () => {
  const container = containerRef.value
  if (!container) return
  if (!document.fullscreenElement) {
    container.requestFullscreen().then(() => { isFullscreen.value = true }).catch(() => {})
  } else {
    document.exitFullscreen().then(() => { isFullscreen.value = false }).catch(() => {})
  }
}
</script>

<style scoped>
.car-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: var(--bg-primary);
}

.view-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  z-index: 10;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  padding: 6px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.view-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  border: none;
  padding: 0;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: Inter, sans-serif;
}

.view-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
}

.view-btn.active {
  background: rgba(59, 130, 246, 0.25);
  color: #60a5fa;
}

.control-buttons {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 10;
}

.ctrl-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
}

.ctrl-btn svg {
  width: 16px;
  height: 16px;
}

.ctrl-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
}

.ctrl-btn.active {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.4);
}

/* VTOL 飞行分支：翡翠绿主色（品牌一致），激活时呼吸辉光 */
.ctrl-btn.vtol-btn:hover {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.35);
}

.ctrl-btn.vtol-btn.active {
  background: rgba(16, 185, 129, 0.22);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.5);
  animation: vtol-glow 1.6s ease-in-out infinite;
}

@keyframes vtol-glow {
  0%, 100% { box-shadow: 0 0 4px rgba(16, 185, 129, 0.25); }
  50% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.55); }
}

.status-item.vtol-status {
  color: #10b981;
  letter-spacing: 0.12em;
}

/* 反重力飞控：原地转向按钮（悬停态出现；字号缩小承载度数文本） */
.ctrl-btn.turn-btn {
  color: #10b981;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

.ctrl-btn.turn-btn:hover {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.35);
}

.ctrl-btn.turn-btn.busy {
  opacity: 0.45;
  pointer-events: none;
}

.ctrl-btn.turn-btn.turn-full {
  font-size: 11px;
  letter-spacing: 0.02em;
}

.status-item.energy-status {
  letter-spacing: 0.04em;
}

.status-bar {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10;
}

.view-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  font-family: Inter, sans-serif;
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.status-item {
  font-size: 10px;
  color: var(--text-muted);
  font-family: Inter, sans-serif;
  letter-spacing: 0.5px;
}
</style>
