// 侧视投影（3D 布置坐标 → 2D SVG 像素）：2D 布置图与对齐校验的唯一换算口径
//
// 为什么单独拆一层：Car2D 若自行写 (frontX - x) * pxPerM 之类的公式，测试无法对「2D 像素」
// 与「3D 米」做闭环断言。本模块把正/反变换收口，Car2D 与 carInteriorLayout.spec.js 共用，
// 从而可以证明「2D 画出的每一个图形都能还原回 3D 的同一坐标，零偏移」。
//
// 约定：3D 坐标 X+ 指向车头（车头在 2D 图左侧，故镜像）；Y+ 向上（SVG y 向下，故翻转）。

/**
 * @param {object} P deriveCarProfile() 返回值（用于 frontX 基准）
 * @param {number} pxPerM 每米像素（Car2D 的 scale × 1000）
 * @param {number} groundY 地面线在 SVG 中的 y 像素
 */
export const createSideViewProjection = (P, pxPerM, groundY) => {
  const toX = (x) => (P.frontX - x) * pxPerM
  const toY = (y) => groundY - y * pxPerM
  // 反变换：用于「2D 像素 → 3D 米」对齐校验
  const fromX = (sx) => P.frontX - sx / pxPerM
  const fromY = (sy) => (groundY - sy) / pxPerM

  /** 3D 绝对矩形（x0<x1, y0<y1）→ SVG rect 属性 */
  const rect = (x0, x1, y0, y1) => ({
    x: toX(x1),
    y: toY(y1),
    w: (x1 - x0) * pxPerM,
    h: (y1 - y0) * pxPerM
  })

  /** 3D 点位序列 → 闭合 SVG 折线 */
  const poly = (points) => points
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${toX(x)},${toY(y)}`)
    .join(' ') + ' Z'

  return { toX, toY, fromX, fromY, rect, poly, pxPerM, groundY }
}

/**
 * 横断面投影（Z-Y 平面 → 2D SVG 像素）：A-A 断面／右视图的唯一换算口径。
 *
 * 视向约定：站在车头正前方看车（右视图），Y 仍向上（SVG 翻转），
 * Z+ = 副驾侧出现在画面左侧，Z- = 驾驶侧（左舵）出现在画面右侧，故 X 轴镜像。
 *
 * @param {number} centerX 车宽中心在 SVG 中的 x 像素
 * @param {number} groundY 地面线在 SVG 中的 y 像素
 * @param {number} pxPerM 每米像素
 */
export const createFrontViewProjection = (centerX, groundY, pxPerM) => {
  const toX = (z) => centerX - z * pxPerM
  const toY = (y) => groundY - y * pxPerM
  // 反变换：用于「断面像素 → 3D 米」对齐校验
  const fromX = (sx) => (centerX - sx) / pxPerM
  const fromY = (sy) => (groundY - sy) / pxPerM

  /** 3D 绝对矩形（z0<z1, y0<y1）→ SVG rect 属性 */
  const rect = (z0, z1, y0, y1) => ({
    x: toX(z1),
    y: toY(y1),
    w: (z1 - z0) * pxPerM,
    h: (y1 - y0) * pxPerM
  })

  return { toX, toY, fromX, fromY, rect, pxPerM, groundY, centerX }
}
