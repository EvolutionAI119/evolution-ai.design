/**
 * 相机交互（P3 拆分：原 Car3D.vue 的鼠标/滚轮/resize 监听段）
 *
 * 只改 `target*`（目标值），`current*` 的逐帧缓动、门与 VTOL 帧循环仍留在 animate 批：
 * 两批合并会让回归差异无法归因到单批。
 *
 * 行为常量逐字保留：
 * - 左键绕轨：`targetRotation.y += dx*0.01`、`targetRotation.x += dy*0.008`，x 夹在 ±π/2.5；
 * - 右键平移：`targetPan.x -= dx*0.01`、`targetPan.y += dy*0.01`，x 夹 ±3、y 夹 ±2；
 * - 滚轮缩放：`targetDistance += deltaY*0.008`，夹在 3~20。
 *
 * 监听注册细节不改：`wheel` 不带 options（加 passive 会让 preventDefault 失效）；
 * `contextmenu` 用具名函数，右键平移依赖它阻止浏览器菜单，两者同生同灭。
 *
 * `detach()` 必须由调用方用**缓存的容器引用**调用（Vue 卸载时模板 ref 已清空）。
 *
 * @param {object} opts
 * @param {HTMLElement} opts.container 事件宿主与尺寸来源
 * @param {THREE.PerspectiveCamera} opts.camera
 * @param {THREE.OrthographicCamera} opts.orthoCamera
 * @param {THREE.WebGLRenderer} opts.renderer
 * @param {object} opts.view 目标值访问器：
 *   { getRotation(): {x,y}, setRotation(x,y), getPan(): {x,y}, setPan(x,y),
 *     getDistance(): number, setDistance(v), setDragging(v) }
 *   `setDragging` 仅镜像拖拽状态给 animate 里的自动旋转暂停判断，不参与相机数值。
 * @returns {() => void} detach
 */
export function attachInteractions({ container, camera, orthoCamera, renderer, view }) {
  let isDragging = false
  let previousMousePosition = { x: 0, y: 0 }

  const onMouseDown = (e) => {
    isDragging = true
    previousMousePosition = { x: e.clientX, y: e.clientY }
    view.setDragging(true)
  }

  const onMouseMove = (e) => {
    if (!isDragging) return
    const dx = e.clientX - previousMousePosition.x
    const dy = e.clientY - previousMousePosition.y
    previousMousePosition = { x: e.clientX, y: e.clientY }

    if (e.button === 2) {
      const pan = view.getPan()
      const px = Math.max(-3, Math.min(3, pan.x - dx * 0.01))
      const py = Math.max(-2, Math.min(2, pan.y + dy * 0.01))
      view.setPan(px, py)
    } else if (e.button === 0) {
      const rot = view.getRotation()
      const rx = Math.max(-Math.PI / 2.5, Math.min(Math.PI / 2.5, rot.x + dy * 0.008))
      view.setRotation(rx, rot.y + dx * 0.01)
    }
  }

  const onMouseUp = () => {
    isDragging = false
    view.setDragging(false)
  }

  const onContextMenu = (e) => e.preventDefault()

  const onWheel = (e) => {
    e.preventDefault()
    view.setDistance(Math.max(3, Math.min(20, view.getDistance() + e.deltaY * 0.008)))
  }

  const onWindowResize = () => {
    if (!container || !renderer) return
    const w = container.clientWidth
    const h = container.clientHeight

    camera.aspect = w / h
    camera.updateProjectionMatrix()

    const aspect = w / h
    const d = 5
    orthoCamera.left = -d * aspect
    orthoCamera.right = d * aspect
    orthoCamera.top = d
    orthoCamera.bottom = -d
    orthoCamera.updateProjectionMatrix()

    renderer.setSize(w, h)
  }

  container.addEventListener('mousedown', onMouseDown)
  container.addEventListener('mousemove', onMouseMove)
  container.addEventListener('mouseup', onMouseUp)
  container.addEventListener('mouseleave', onMouseUp)
  container.addEventListener('wheel', onWheel)
  container.addEventListener('contextmenu', onContextMenu)   // 具名注册，卸载可解绑
  window.addEventListener('resize', onWindowResize)

  return function detach() {
    container.removeEventListener('mousedown', onMouseDown)
    container.removeEventListener('mousemove', onMouseMove)
    container.removeEventListener('mouseup', onMouseUp)
    container.removeEventListener('mouseleave', onMouseUp)
    container.removeEventListener('wheel', onWheel)
    container.removeEventListener('contextmenu', onContextMenu)
    window.removeEventListener('resize', onWindowResize)
  }
}
