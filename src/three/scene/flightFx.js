import * as THREE from 'three'
import { disposeObject } from '../dispose.js'

/**
 * VTOL 升力风扇环 + 地面能量场（P3 拆分：原 Car3D.vue 的 ensureFlightFx / disposeFlightFx）
 *
 * 持有权唯一：环与地面场只存在本实例内，组件侧不得再保存 `rings` /
 * `groundGlow` 之类的镜像变量，避免双真源。
 *
 * 归属与释放：
 * - 环是 `carGroup` 子对象（随车升降），`dispose()` 只清数组，几何/材质由调用方随后的
 *   `disposeObject(carGroup)` 统一释放，禁止在这里二次释放。
 * - 地面场是 `scene` 子对象，切车时必须 `scene.remove` + dispose，否则会叠加多个能量场。
 *
 * 布局来源：`liftLayout` 必须由调用方传入与 `createLiftDucts` 同一份 `deriveLiftDevices`
 * 结果；模块内不再调用 `deriveCarProfile`，避免环与风道错位。
 *
 * 逐帧外观（pulse / opacity / scale）与建环常量均为原值，不得重排或化简。
 *
 * @param {object} opts
 * @param {THREE.Scene} opts.scene 地面能量场宿主
 * @returns {{ ensure: Function, update: Function, dispose: Function }}
 */
export function createFlightFx({ scene }) {
  let rings = []
  let groundGlow = null
  let built = false

  /** 建环 + 地面场；由 animate 首帧调用（晚于装配层 applyShadowFlags 遍历） */
  const ensure = ({ carGroup, carParams, liftLayout }) => {
    if (!scene || !carGroup || built || !liftLayout) return
    const ringMat = () => new THREE.MeshBasicMaterial({
      color: 0x38bdf8, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false
    })
    // 升力环与底盘上升装置同坐标（装置本体在 createCar 中常显，环仅飞行时可见）
    for (const d of liftLayout.devices) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(d.r * 0.86, 0.016, 10, 40), ringMat())
      ring.rotation.x = Math.PI / 2
      ring.position.set(d.x, liftLayout.y - 0.03, d.z)
      ring.userData.noCastShadow = true
      ring.visible = false
      carGroup.add(ring)
      rings.push(ring)
    }
    // 地面能量场：半径随车长缩放，绿色翡翠（品牌主色），悬浮越高越弱
    const glowR = Math.max(2.0, (carParams.overall_length || 4800) / 1000 * 0.42)
    const glowGeo = new THREE.CircleGeometry(glowR, 48)
    groundGlow = new THREE.Mesh(glowGeo, new THREE.MeshBasicMaterial({
      color: 0x10b981, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false
    }))
    groundGlow.rotation.x = -Math.PI / 2
    groundGlow.position.y = 0.02
    groundGlow.visible = false
    scene.add(groundGlow)
    built = true
  }

  /**
   * 逐帧外观：环脉冲（蓝）与地面场随高度衰减（绿）
   * @param {object} state
   * @param {number} state.now performance.now()
   * @param {number} state.lift quinticSmoothstep(flightProgress)
   * @param {number} state.progress flightProgress ∈ [0,1]
   */
  const update = ({ now, lift, progress }) => {
    const pulse = 0.5 + 0.5 * Math.sin(now / 1000 * Math.PI * 2 * 0.8)
    const ringOn = progress > 0.001
    for (const r of rings) {
      r.visible = ringOn
      r.material.opacity = ringOn ? 0.55 * (0.35 + 0.65 * pulse) * (0.3 + 0.7 * lift) : 0
      const s = 1 + 0.10 * pulse
      r.scale.set(s, s, 1)
    }
    if (groundGlow) {
      groundGlow.visible = ringOn
      groundGlow.material.opacity = ringOn
        ? 0.22 * (1 - 0.72 * lift) * (0.4 + 0.6 * pulse) : 0
      const gs = 1 + 0.35 * (1 - lift)
      groundGlow.scale.set(gs, gs, 1)
    }
  }

  /** 清数组 + 移除地面场；环本体由 carGroup 的 disposeObject 统一释放 */
  const dispose = () => {
    if (groundGlow) {
      scene.remove(groundGlow)
      disposeObject(groundGlow)
      groundGlow = null
    }
    rings = []
    built = false   // 复位后切色/线框重建可再次建环
  }

  return { ensure, update, dispose }
}
