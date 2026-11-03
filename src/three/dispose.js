// Three.js 资源释放（自 Car3D.vue P1 拆分，无场景依赖）

/** 释放材质及其随附贴图（alphaMap 等 CanvasTexture 显式 dispose，避免内存泄漏） */
export function disposeMaterial(m) {
  for (const slot of ['map', 'alphaMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap']) {
    if (m[slot] && typeof m[slot].dispose === 'function') m[slot].dispose()
  }
  m.dispose()
}

/** 递归释放对象树上的几何与材质 */
export function disposeObject(obj) {
  if (!obj) return
  obj.traverse((child) => {
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach(disposeMaterial)
      } else {
        disposeMaterial(child.material)
      }
    }
  })
  if (obj.geometry) obj.geometry.dispose()
  if (obj.material) {
    if (Array.isArray(obj.material)) {
      obj.material.forEach(disposeMaterial)
    } else {
      disposeMaterial(obj.material)
    }
  }
}
