/**
 * 视角预设与正交视口尺寸（P6 收口：从 composables/useCarScene.js 抽出）
 *
 * 只放纯数据与纯函数：不读 ref/props、不碰相机实例。
 * containerRef 属于组件侧依赖，宽度/高度由调用方读好后传入。
 */

// 车长沿 X 轴（X+ 朝车头）。正交视角 dist 经 0.6 系数映射为半视口高度 d
// front=相机在 +X（正对车头）/ rear=-X / left=-Z（驾驶员侧）/ right=+Z
export const viewPresets = {
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
 * 正交相机视口尺寸（纯函数）：dist 按 0.6 系数映射为半视口高，按容器宽高比横向展开。
 *
 * @param {number} dist 预设距离（viewPresets[key].dist）
 * @param {number} width 容器宽度（px，由组件侧从 containerRef 读取）
 * @param {number} height 容器高度（px）
 * @returns {{ left:number, right:number, top:number, bottom:number }}
 */
export function orthoViewportSize(dist, width, height) {
  const d = dist * 0.6
  const aspect = width / height
  return { left: -d * aspect, right: d * aspect, top: d, bottom: -d }
}
