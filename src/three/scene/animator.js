import { resolveFlightParams, quinticSmoothstep, hoverBobOffset,
  turnDurationSec, attitudeSample } from '../../utils/flightPhysics.js'

/**
 * 帧循环（P3 animate 批）：相机 target/current 缓动、VTOL 升降 + 转向、车门开合、渲染。
 *
 * 持有权：
 * - 相机 target/current（rotation / distance / pan）、isOrthoCamera、isDragging 全部由本实例
 *   持有；createScene 的 viewControls（snap / setTargets / setOrtho）与 interactions 的
 *   view 六方法都只做转发，语义不变。
 * - VTOL 数值状态（flightProgress / flightLastMs / flightYaw*）与 doorProgress 同样只在
 *   本实例内；UI 侧的 ref（flightEngaged / yawTurning / doorOpen / autoRotate / currentView）
 *   一律通过 getter 读取、通过 setYawTurning 回调写回，禁止把 ref 塞进模块。
 * - carGroup / doorHinges / doorSeams 每帧通过 getter 取：updateCar 会整体换对象，
 *   模块内禁止缓存引用。
 *
 * 时序：
 * - start() 与 resetTiming() 都重置 flightLastMs，避免首帧 vdt 吃到 0.05 上限造成瞬跳。
 * - flightFx.update 每帧调用（仅在 carGroup + flightAvailable 分支内），与旧实现一致。
 *
 * 逐字保留：currentPan.x += (targetPan.x - targetPan.x) * 0.08（现存 no-op，不修）、
 * 门缓动 vdt / 0.8、door_open_angle ?? 70、seamVisible < 0.02、0.08 缓动系数、+1 抬升。
 *
 * @param {object} ctx
 * @returns {object} animator
 */
export function createAnimator({
  scene, camera, orthoCamera, renderer,
  getCarGroup, getDoorHinges, getDoorSeams,
  getCarParams, getCarType, getLiftLayout,
  getAutoRotate, getCurrentView, getDoorOpen,
  getFlightEngaged, getFlightAvailable, getFlightFx,
  setYawTurning
}) {
  let rafId = null
  let isDragging = false
  let targetRotation = { x: 0.4, y: 0.8 }
  let currentRotation = { x: 0.4, y: 0.8 }
  let targetDistance = 8
  let currentDistance = 8
  let targetPan = { x: 0, y: 0 }
  let currentPan = { x: 0, y: 0 }
  let isOrthoCamera = false

  // ---- VTOL 数值状态（0=地面，1=稳态悬浮；偏航为累计角，无 wrap）----
  let flightProgress = 0
  let flightLastMs = 0
  let flightYawCurrent = 0
  let flightYawFrom = 0
  let flightYawTarget = 0
  let flightYawProgress = 1   // 1 = 就绪（可接受新转向指令）
  let flightYawDuration = 1

  // ---- 车门开合状态（doorProgress ∈ [0,1] 缓动趋近目标）----
  let doorProgress = 0

  const tick = () => {
    rafId = requestAnimationFrame(tick)

    // ---- VTOL 飞行动画（无眩晕：C² 平滑起升 + 过阻尼悬浮呼吸 + 零滚转）----
    const vnow = performance.now()
    const vdt = flightLastMs ? Math.min((vnow - flightLastMs) / 1000, 0.05) : 0
    flightLastMs = vnow
    const carGroup = getCarGroup()
    const fx = getFlightFx()
    if (carGroup && getFlightAvailable()) {
      // 首帧建环（晚于 createCar 的 castShadow 遍历，保持 noCastShadow 时序）
      fx?.ensure({ carGroup, carParams: getCarParams(), liftLayout: getLiftLayout() })
      const fp = resolveFlightParams(getCarType(), getCarParams())
      const target = getFlightEngaged() ? 1 : 0
      if (flightProgress !== target) {
        const step = vdt / Math.max(fp.liftDuration, 0.1)
        flightProgress = target > flightProgress
          ? Math.min(flightProgress + step, 1)
          : Math.max(flightProgress - step, 0)
      }
      const lift = quinticSmoothstep(flightProgress)
      // 悬浮呼吸：振幅随 lift² 衰减（地面为零），频率 < 0.2Hz 远离晕动敏感频段
      const bob = hoverBobOffset(vnow / 1000, fp) * lift * lift
      carGroup.position.y = (fp.hoverAltitude * lift + bob) / 1000
      // ---- 反重力飞控：360° 原地转向（累计角无 wrap，C² 剖面无卡顿）----
      if (flightYawProgress < 1) {
        flightYawProgress = Math.min(1, flightYawProgress + vdt / Math.max(flightYawDuration, 0.1))
        const eased = quinticSmoothstep(flightYawProgress)
        flightYawCurrent = flightYawFrom + (flightYawTarget - flightYawFrom) * eased
        if (flightYawProgress >= 1) {
          flightYawCurrent = flightYawTarget
          setYawTurning(false)
        }
      }
      carGroup.rotation.y = flightYawCurrent * Math.PI / 180
      // 姿态微摆（roll/pitch 双低频谱，峰值 ≤0.85°/ζ < ±2° 包络；振幅随 lift² 衰减）：
      // 原地转向零向心加速度 → 零侧倾耦合，roll 与 yaw 解耦（全自由度姿态稳定）
      const attRoll = attitudeSample(vnow / 1000, fp.darkMatterRatio) * lift * lift
      const attPitch = attitudeSample(vnow / 1000 + 17.3, fp.darkMatterRatio) * lift * lift
      carGroup.rotation.z = attRoll * Math.PI / 180
      carGroup.rotation.x = attPitch * Math.PI / 180
      // 特效：风扇环脉冲（蓝），地面能量场随高度衰减（绿）
      fx?.update({ now: vnow, lift, progress: flightProgress })
    }

    // ---- 车门开合动画：doorProgress 缓动趋近目标，铰链绕竖直轴 rotation.y 开合（把手随门板）----
    const hinges = getDoorHinges()
    if (hinges.length) {
      const dTarget = getDoorOpen() ? 1 : 0
      if (doorProgress !== dTarget) {
        const step = vdt / 0.8
        doorProgress = dTarget > doorProgress ? Math.min(doorProgress + step, 1) : Math.max(doorProgress - step, 0)
      }
      const openRad = ((getCarParams()?.door_open_angle ?? 70) * Math.PI) / 180
      const e = quinticSmoothstep(doorProgress) * openRad
      for (const d of hinges) d.hinge.rotation.y = d.sign * e   // 正负号使门板向外摆（+Z 侧向 +Z、−Z 侧向 −Z）
      // 门缝条属于「关门时的分缝观感」：门一开就与门板脱开、悬在洞口中央，
      // 必须在 doorProgress 抬起后立即隐藏，只在完全关闭时显示。
      const seamVisible = doorProgress < 0.02
      for (const s of getDoorSeams()) s.visible = seamVisible
    }

    if (getAutoRotate() && !isDragging && getCurrentView() === 'perspective') {
      targetRotation.y += 0.004
    }

    currentRotation.x += (targetRotation.x - currentRotation.x) * 0.08
    currentRotation.y += (targetRotation.y - currentRotation.y) * 0.08
    currentDistance += (targetDistance - currentDistance) * 0.08
    currentPan.x += (targetPan.x - targetPan.x) * 0.08
    currentPan.y += (targetPan.y - currentPan.y) * 0.08

    const activeCamera = isOrthoCamera ? orthoCamera : camera

    activeCamera.position.x = currentPan.x + Math.sin(currentRotation.y) * Math.cos(currentRotation.x) * currentDistance
    activeCamera.position.y = currentPan.y + Math.sin(currentRotation.x) * currentDistance + 1
    activeCamera.position.z = Math.cos(currentRotation.y) * Math.cos(currentRotation.x) * currentDistance
    activeCamera.lookAt(currentPan.x, 1, currentPan.y)

    renderer.render(scene, activeCamera)
  }

  const start = () => {
    if (rafId !== null) return
    flightLastMs = 0   // 首帧 vdt = 0，避免重建/重开后第一帧跳变
    tick()
  }

  const stop = () => {
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
  }

  /** updateCar 重建车身后重置帧间计时 */
  const resetTiming = () => { flightLastMs = 0 }

  /** 相机 target → current 瞬时对齐（createScene 的 setViewInstant 调用） */
  const snap = () => {
    currentRotation.x = targetRotation.x
    currentRotation.y = targetRotation.y
    currentDistance = targetDistance
    currentPan.x = targetPan.x
    currentPan.y = targetPan.y
  }

  const setTargets = (pose) => {
    if (typeof pose.rotX === 'number') targetRotation.x = pose.rotX
    if (typeof pose.rotY === 'number') targetRotation.y = pose.rotY
    if (typeof pose.distance === 'number') targetDistance = pose.distance
    if (typeof pose.panX === 'number') targetPan.x = pose.panX
    if (typeof pose.panY === 'number') targetPan.y = pose.panY
  }

  const setOrtho = (ortho) => { isOrthoCamera = ortho }

  // interactions.js 的 view 访问器（六方法语义与拆分前一致，另加 setDragging 镜像）
  const getRotation = () => ({ x: targetRotation.x, y: targetRotation.y })
  const setRotation = (x, y) => {
    targetRotation.x = x
    targetRotation.y = y
  }
  const getPan = () => ({ x: targetPan.x, y: targetPan.y })
  const setPan = (x, y) => {
    targetPan.x = x
    targetPan.y = y
  }
  const getDistance = () => targetDistance
  const setDistance = (v) => { targetDistance = v }
  const setDragging = (v) => { isDragging = v }

  /** 调试钩子 __car3d__.viewState() 的字段快照（签名冻结） */
  const getState = () => ({
    rotX: currentRotation.x,
    rotY: currentRotation.y,
    targetX: targetRotation.x,
    targetY: targetRotation.y,
    distance: currentDistance,
    targetDistance,
    ortho: isOrthoCamera
  })

  /** 原地转向：Δ ∈ (-∞,∞) 累计；时长按峰值角速度 45°/s 舒适限动态计算 */
  const startTurn = (delta) => {
    flightYawFrom = flightYawTarget
    flightYawTarget += delta
    flightYawDuration = turnDurationSec(delta)
    flightYawProgress = 0
    setYawTurning(true)
  }

  /** 门瞬时落位（setDoor 钩子）：与缓动共用同一 doorProgress，避免两套状态 */
  const setDoorInstant = (open) => {
    doorProgress = open ? 1 : 0
    const openRad = ((getCarParams()?.door_open_angle ?? 70) * Math.PI) / 180
    for (const d of getDoorHinges()) d.hinge.rotation.y = d.sign * openRad
    for (const s of getDoorSeams()) s.visible = !open
  }

  return {
    start, stop, resetTiming,
    snap, setTargets, setOrtho,
    getRotation, setRotation, getPan, setPan, getDistance, setDistance, setDragging,
    getState, startTurn, setDoorInstant
  }
}
