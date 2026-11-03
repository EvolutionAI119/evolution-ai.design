// Three.js 资源释放（自 Car3D.vue P1 拆分，无场景依赖）

// 同一实例可能被多个 mesh/多材质槽引用（例如轮辋亮银同时用于辐条与轮唇、
// 两片外后视镜共用一张 alphaMap 贴花）。three 的 dispose() 本身可重复调用，
// 但贴图会被每个持有它的材质各释放一次，跨构建复用纹理时风险更大。
// 因此按「一次释放会话」去重：同一几何/材质/贴图只释放一次。

/** 释放材质及其随附贴图（`seen` 为本次会话的去重集合，可跨材质共享） */
export function disposeMaterial(m, seen = new WeakSet()) {
  if (!m) return
  for (const slot of ['map', 'alphaMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'emissiveMap']) {
    const tex = m[slot]
    if (tex && typeof tex.dispose === 'function' && !seen.has(tex)) {
      seen.add(tex)
      tex.dispose()
    }
  }
  if (!seen.has(m)) {
    seen.add(m)
    m.dispose()
  }
}

/** 递归释放对象树上的几何与材质（同一实例只释放一次，含根节点自身） */
export function disposeObject(obj) {
  if (!obj) return
  const seen = new WeakSet()
  obj.traverse((child) => {
    if (child.geometry && !seen.has(child.geometry)) {
      seen.add(child.geometry)
      child.geometry.dispose()
    }
    if (child.material) {
      if (Array.isArray(child.material)) {
        child.material.forEach((m) => disposeMaterial(m, seen))
      } else {
        disposeMaterial(child.material, seen)
      }
    }
  })
}
