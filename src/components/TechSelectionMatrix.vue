<template>
  <div class="tech-matrix">
    <!-- 依赖关系图 -->
    <div class="dependency-graph-card">
      <div class="card-header">
        <span class="card-title">DEPENDENCY GRAPH</span>
        <span class="graph-hint">依赖箭头方向：前置 → 后置</span>
      </div>
      <div class="graph-body">
        <svg class="dependency-svg" :viewBox="`0 0 ${graphWidth} ${graphHeight}`" preserveAspectRatio="xMidYMid meet">
          <!-- 连线层 -->
          <g class="edges">
            <g v-for="edge in edges" :key="`edge-${edge.from}-${edge.to}`">
              <path
                :d="edge.path"
                class="edge-path"
                :class="{ 'edge-highlight': isEdgeHovered(edge) }"
                fill="none"
                :stroke="getEdgeColor(edge)"
                :stroke-width="isEdgeHovered(edge) ? 2.5 : 1.5"
                :stroke-dasharray="isEdgeHovered(edge) ? 'none' : '6 4'"
                marker-end="url(#arrowhead)"
              />
              <text
                :x="edge.midX"
                :y="edge.midY - 6"
                class="edge-label"
                text-anchor="middle"
              >{{ edge.label }}</text>
            </g>
          </g>
          <!-- 节点层 -->
          <g class="nodes">
            <g
              v-for="node in nodes"
              :key="`node-${node.id}`"
              :transform="`translate(${node.x}, ${node.y})`"
              class="node-group"
              @mouseenter="hoveredNode = node.id"
              @mouseleave="hoveredNode = null"
            >
              <rect
                :x="-nodeWidth / 2"
                :y="-nodeHeight / 2"
                :width="nodeWidth"
                :height="nodeHeight"
                :rx="8"
                class="node-rect"
                :class="`node-priority-${node.priority.toLowerCase()}`"
                :stroke="isNodeHighlighted(node.id) ? 'var(--accent)' : 'var(--border-color)'"
                :stroke-width="isNodeHighlighted(node.id) ? 2 : 1"
              />
              <text x="0" y="-8" class="node-title" text-anchor="middle">{{ node.dimension }}</text>
              <text x="0" y="10" class="node-sub" text-anchor="middle">{{ node.stage }} · {{ node.priority }}</text>
            </g>
          </g>
          <!-- 箭头标记定义 -->
          <defs>
            <marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
            </marker>
          </defs>
        </svg>
        <div class="legend">
          <span class="legend-item"><span class="dot dot-p0"></span>P0 最高优先级</span>
          <span class="legend-item"><span class="dot dot-p1"></span>P1 高优先级</span>
          <span class="legend-item"><span class="dot dot-p2"></span>P2 中优先级</span>
          <span class="legend-item"><span class="line-demo"></span>依赖关系</span>
        </div>
      </div>
    </div>

    <!-- 决策矩阵表 -->
    <div class="matrix-card">
      <div class="card-header">
        <span class="card-title">DECISION MATRIX</span>
      </div>
      <div class="table-wrapper">
        <table class="matrix-table">
          <thead>
            <tr>
              <th class="col-id">#</th>
              <th class="col-dim">选型维度</th>
              <th class="col-current">当前方案</th>
              <th class="col-recommend">推荐方案</th>
              <th class="col-stage">阶段</th>
              <th class="col-priority">优先级</th>
              <th class="col-dependency">依赖链</th>
              <th class="col-reason">核心理由</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedMatrix"
              :key="item.id"
              @mouseenter="hoveredNode = item.id"
              @mouseleave="hoveredNode = null"
              :class="{ 'row-highlight': isNodeHighlighted(item.id) }"
            >
              <td class="col-id">{{ item.id }}</td>
              <td class="col-dim">{{ item.dimension }}</td>
              <td class="col-current">{{ item.currentSolution }}</td>
              <td class="col-recommend">
                <span class="recommend-tag">{{ item.recommendedSolution }}</span>
              </td>
              <td class="col-stage">
                <span class="stage-tag" :class="`stage-${item.stage}`">{{ item.stage }}</span>
              </td>
              <td class="col-priority">
                <span class="priority-tag" :class="`priority-${item.priority.toLowerCase()}`">{{ item.priority }}</span>
              </td>
              <td class="col-dependency">
                <div v-if="item.dependencies.length === 0" class="dep-none">无前置</div>
                <div v-else class="dep-chain">
                  <span
                    v-for="(depId, idx) in item.dependencies"
                    :key="depId"
                    class="dep-item"
                  >
                    <span class="dep-node">{{ getDimensionName(depId) }}</span>
                    <span v-if="idx < item.dependencies.length - 1" class="dep-arrow">→</span>
                  </span>
                  <span class="dep-arrow dep-final">→</span>
                  <span class="dep-node dep-self">{{ item.dimension }}</span>
                </div>
              </td>
              <td class="col-reason">{{ item.coreReason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { techSelectionMatrix, matrixMetadata } from '../data/techSelectionMatrix.js'

const hoveredNode = ref(null)

const nodeWidth = 150
const nodeHeight = 56
const graphWidth = 900
const graphHeight = 320

// 构建节点位置：按依赖层级分层布局
const nodes = computed(() => {
  const items = techSelectionMatrix
  const layers = {}

  // 计算每个节点的层级
  const getLayer = (id, visited = new Set()) => {
    if (visited.has(id)) return 0
    visited.add(id)
    const item = items.find(i => i.id === id)
    if (!item || item.dependencies.length === 0) return 0
    return 1 + Math.max(...item.dependencies.map(d => getLayer(d, visited)))
  }

  items.forEach(item => {
    const layer = getLayer(item.id)
    if (!layers[layer]) layers[layer] = []
    layers[layer].push(item)
  })

  const maxLayer = Math.max(...Object.keys(layers).map(Number))
  const result = []
  const layerKeys = Object.keys(layers).map(Number).sort((a, b) => a - b)

  layerKeys.forEach((layer, layerIdx) => {
    const layerItems = layers[layer]
    const layerWidth = graphWidth
    const startX = layerWidth / (layerItems.length + 1)
    layerItems.forEach((item, idx) => {
      result.push({
        ...item,
        x: startX * (idx + 1),
        y: 60 + layerIdx * 110,
        layer
      })
    })
  })

  return result
})

// 构建依赖边
const edges = computed(() => {
  const nodeMap = new Map(nodes.value.map(n => [n.id, n]))
  const result = []

  techSelectionMatrix.forEach(item => {
    item.dependencies.forEach(depId => {
      const from = nodeMap.get(depId)
      const to = nodeMap.get(item.id)
      if (from && to) {
        const midX = (from.x + to.x) / 2
        const midY = (from.y + to.y) / 2
        // 贝塞尔曲线路径
        const dx = to.x - from.x
        const dy = to.y - from.y
        const ctrl1X = from.x + dx * 0.5
        const ctrl1Y = from.y + 20
        const ctrl2X = to.x - dx * 0.5
        const ctrl2Y = to.y - 20
        result.push({
          from: depId,
          to: item.id,
          path: `M ${from.x} ${from.y + nodeHeight / 2} C ${ctrl1X} ${ctrl1Y}, ${ctrl2X} ${ctrl2Y}, ${to.x} ${to.y - nodeHeight / 2}`,
          midX,
          midY,
          label: '依赖'
        })
      }
    })
  })

  return result
})

// 拓扑排序：无依赖的在前
const sortedMatrix = computed(() => {
  const result = []
  const visited = new Set()
  const visit = (id) => {
    if (visited.has(id)) return
    visited.add(id)
    const item = techSelectionMatrix.find(i => i.id === id)
    if (item.dependencies.length > 0) {
      item.dependencies.forEach(d => visit(d))
    }
    result.push(item)
  }
  techSelectionMatrix.forEach(item => visit(item.id))
  return result
})

const getDimensionName = (id) => {
  const item = techSelectionMatrix.find(i => i.id === id)
  return item ? item.dimension : `#${id}`
}

const isNodeHighlighted = (id) => {
  if (!hoveredNode.value) return false
  if (hoveredNode.value === id) return true
  // 高亮直接相关的节点
  return edges.value.some(e =>
    (e.from === hoveredNode.value && e.to === id) ||
    (e.to === hoveredNode.value && e.from === id)
  )
}

const isEdgeHovered = (edge) => {
  if (!hoveredNode.value) return false
  return edge.from === hoveredNode.value || edge.to === hoveredNode.value
}

const getEdgeColor = (edge) => {
  if (isEdgeHovered(edge)) return 'var(--accent)'
  return 'var(--text-muted)'
}
</script>

<style scoped>
.tech-matrix {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dependency-graph-card,
.matrix-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.graph-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.graph-body {
  padding: 16px;
}

.dependency-svg {
  width: 100%;
  height: 320px;
}

.edge-path {
  transition: stroke 0.2s ease, stroke-width 0.2s ease;
}

.edge-label {
  font-size: 10px;
  fill: var(--text-muted);
  pointer-events: none;
}

.node-rect {
  fill: var(--bg-secondary);
  transition: stroke 0.2s ease, stroke-width 0.2s ease;
}

.node-priority-p0 {
  fill: rgba(239, 68, 68, 0.08);
}

.node-priority-p1 {
  fill: rgba(245, 158, 11, 0.08);
}

.node-priority-p2 {
  fill: rgba(34, 197, 94, 0.08);
}

.node-title {
  font-size: 12px;
  font-weight: 600;
  fill: var(--text-primary);
}

.node-sub {
  font-size: 10px;
  fill: var(--text-muted);
}

.node-group {
  cursor: pointer;
}

.legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.dot-p0 { background: #ef4444; }
.dot-p1 { background: #f59e0b; }
.dot-p2 { background: #22c55e; }

.line-demo {
  width: 24px;
  height: 2px;
  border-top: 1.5px dashed var(--accent);
  display: inline-block;
}

.table-wrapper {
  overflow-x: auto;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.matrix-table th,
.matrix-table td {
  border-bottom: 1px solid var(--border-color);
  padding: 12px 14px;
  text-align: left;
  vertical-align: middle;
}

.matrix-table th {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: sticky;
  top: 0;
  z-index: 1;
}

.matrix-table tbody tr {
  transition: background 0.15s ease;
}

.matrix-table tbody tr:hover,
.row-highlight {
  background: var(--accent-bg);
}

.col-id { width: 32px; text-align: center; color: var(--text-muted); }
.col-dim { font-weight: 600; color: var(--text-primary); white-space: nowrap; }
.col-current { color: var(--text-muted); }
.col-recommend { white-space: nowrap; }
.col-stage, .col-priority { text-align: center; white-space: nowrap; }
.col-dependency { min-width: 200px; }
.col-reason { color: var(--text-secondary); max-width: 280px; }

.recommend-tag {
  color: var(--accent);
  font-weight: 600;
}

.stage-tag,
.priority-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.stage-tag.stage-短期 { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
.stage-tag.stage-中期 { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.stage-tag.stage-长期 { background: rgba(167, 139, 250, 0.15); color: #a78bfa; }

.priority-tag.priority-p0 { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.priority-tag.priority-p1 { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.priority-tag.priority-p2 { background: rgba(34, 197, 94, 0.15); color: #22c55e; }

.dep-none {
  color: var(--text-muted);
  font-size: 12px;
  font-style: italic;
}

.dep-chain {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.dep-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dep-node {
  display: inline-block;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.dep-self {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}

.dep-arrow {
  color: var(--text-muted);
  font-size: 14px;
}

.dep-final {
  margin-left: 2px;
}
</style>