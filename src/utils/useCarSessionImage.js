/**
 * 车型图片渲染：通用 composable，统一 L1 → L2 → L3 → L4 四层降级链，
 * 永远不空白，也不依赖隐式 localStorage 失败记忆。
 *
 * 适用场景（任何需要"会话/车型图片 + 失败自动降级"的地方）：
 *   1. Designer.vue 侧边栏 + 参考卡片（carPresets model 对象）
 *   2. Deliver.vue 导入预览卡片 + sessions 表格缩略图（{brand_key,model_key,params} 预览对象）
 *   3. 未来 reports / project gallery 等页面直接使用（import 即可）
 *
 * 用法示例：
 *   import { useCarSessionImage } from '@/utils/useCarSessionImage.js'
 *
 *   // scope 用于区分多个组合（例如 "designer" / "deliver.import" / "gallery"）
 *   // 不同 scope 的失败 attempt/minLayer 互不干扰
 *   const { imageRenderKey, imageSrc, stateLabel, handleImageError, clearScope } = useCarSessionImage('deliver')
 *
 *   // --- Designer（上下文：model 对象 + brandKey 外查） ---
 *   <img :key="imageRenderKey(model.key)"
 *        :src="imageSrc(model.key, { model, brandKey })"
 *        @error="handleImageError(model.key, { model, brandKey })" />
 *
 *   // --- Deliver（上下文：preview = { brand_key, model_key, params }） ---
 *   <img :key="imageRenderKey('sess_' + sid)"
 *        :src="imageSrc('sess_' + sid, { preview })"
 *        @error="handleImageError('sess_' + sid, { preview })" />
 */
import { reactive } from 'vue'
import {
  getStaticPhotoPath,
  buildRuntimeSvgDataUrl,
  UNIVERSAL_FALLBACK,
  markUrlFailed,
  isUrlMarkedFailed,
} from './carImageManager.js'

/**
 * 全局共享 scopeStore（作用域名 → 状态容器），用 scope 避免不同模块串扰：
 * - 模块 A 用 scope="designer"，状态在 scopeStore.designer 里；
 * - 模块 B 用 scope="deliver"，状态在 scopeStore.deliverer 里；
 * - 同一个 scope 多次 useCarSessionImage(scope) 会拿到同一个 reactive state。
 */
const scopeStore = reactive({})

/**
 * 从「model / preview 二者之一」归一化出 resolveByLayer 所需的四要素：
 *   brandKey / modelKey / modelImageUrl / model-like-obj（供 buildRuntimeSvgDataUrl 用）
 */
const _normalizeCtx = ctx => {
  ctx = ctx || {}
  let brandKey = ''
  let modelKey = ''
  let modelImageUrl = null
  let svgModel = { key: 'x', params: {}, image: null }

  if (ctx.model) {
    // Designer 场景：model.key / model.image / model.params
    brandKey = ctx.brandKey || ''
    modelKey = ctx.model.key || modelKey
    modelImageUrl = ctx.model.image || null
    svgModel = ctx.model
  } else if (ctx.preview) {
    // Deliver 会话预览场景：{brand_key, model_key, params, image?}
    brandKey = ctx.preview.brand_key || ctx.preview.brandKey || ''
    modelKey = ctx.preview.model_key || ctx.preview.model_key || ''
    modelImageUrl = ctx.preview.image || null
    svgModel = {
      key: modelKey || ctx.preview.source_format || 'imported',
      params: ctx.preview.params || {},
      image: null,
    }
  } else if (ctx.brandKey || ctx.modelKey) {
    // 直接传 brand/model 的极简场景
    brandKey = ctx.brandKey || ''
    modelKey = ctx.modelKey || ''
    svgModel = { key: modelKey || 'x', params: ctx.params || {}, image: null }
  }
  return { brandKey, modelKey, modelImageUrl, svgModel }
}

export const useCarSessionImage = (scope = 'default', { maxAttempts = 5 } = {}) => {
  // 拿到 scope 对应的状态容器
  if (!scopeStore[scope] || typeof scopeStore[scope] !== 'object') {
    scopeStore[scope] = reactive({})
  }
  const imageStates = scopeStore[scope]

  const ensureState = key => {
    const k = String(key || '')
    if (!imageStates[k] || typeof imageStates[k] !== 'object') {
      imageStates[k] = { layer: 0, attempt: 0, renderKey: 0, minLayer: 0 }
    }
    return imageStates[k]
  }

  const imageRenderKey = key => {
    const s = ensureState(key)
    return `${scope}::${key}__r${s.renderKey}`
  }

  const stateLabel = key => {
    const s = ensureState(key)
    if (s.layer === 3 || s.layer === 4) return 'local-fallback'
    if (s.attempt === 0 && s.layer === 0) return 'loading'
    return `L${s.layer}`
  }

  /**
   * 四层降级解析：L1 本地 JPG → L2 远程 AI 图 → L3 运行时 SVG → L4 UNIVERSAL_FALLBACK
   * @returns {{src: string, layer: number}}
   */
  const resolveByLayer = (ctx, minLayer = 0) => {
    const { brandKey, modelImageUrl, svgModel, modelKey } = _normalizeCtx(ctx)
    const all = []
    // L1 本地 JPG（真车图，存在且未被加入失败名单）
    if (brandKey && modelKey) {
      const staticPath = getStaticPhotoPath(brandKey, modelKey)
      if (staticPath && !isUrlMarkedFailed(staticPath)) {
        all.push({ src: staticPath, layer: 1 })
      }
    }
    // L2 远程 AI 图（只有 Designer 的 model.image 会有）
    if (modelImageUrl && !isUrlMarkedFailed(modelImageUrl)) {
      all.push({ src: modelImageUrl, layer: 2 })
    }
    // L3 运行时 SVG（按 overrides 参数绘制，参数越准越准）
    const svg = buildRuntimeSvgDataUrl(svgModel, brandKey)
    if (svg) all.push({ src: svg, layer: 3 })
    // L4 终极兜底
    all.push({ src: UNIVERSAL_FALLBACK, layer: 4 })

    const chosen = all.find(a => a.layer > minLayer) || all[all.length - 1]
    return chosen
  }

  const imageSrc = (key, ctx) => {
    const s = ensureState(key)
    const resolved = resolveByLayer(ctx, s.minLayer || 0)
    // 渲染阶段只写 layer（用于 stateLabel 显示 L1/L2/L3），不触发新的响应式更新
    s.layer = resolved.layer
    return resolved.src
  }

  /**
   * <img @error> 统一处理：
   *   - 失败 URL 若不是 data: 就记入 markUrlFailed（下次全局不再尝试）
   *   - state.minLayer 至少提升到本次失败 layer
   *   - renderKey++ 让 Vue 重新挂载 <img>（onerror 钩子可以再次触发）
   *   - attempt 封顶就锁在 L4（终极兜底 data: URL，不会再请求网络）
   */
  const handleImageError = (key, ctx) => {
    const state = ensureState(key)
    state.attempt++
    const resolved = resolveByLayer(ctx, state.minLayer || 0)
    if (resolved.src && !resolved.src.startsWith('data:')) {
      markUrlFailed(resolved.src)
    }
    if (state.attempt >= maxAttempts) {
      state.minLayer = 4
      state.renderKey++
      return
    }
    state.minLayer = Math.max(state.minLayer || 0, resolved.layer)
    if (state.minLayer >= 4) state.minLayer = 4
    state.renderKey++
  }

  /** 清理本 scope 下的所有状态（慎用；需要整个画布刷新时用） */
  const clearScope = () => {
    const keys = Object.keys(imageStates)
    for (const k of keys) {
      imageStates[k] = { layer: 0, attempt: 0, renderKey: 0, minLayer: 0 }
    }
  }

  /** 重置某个 key 的状态（切换 model/session 时调用，避免跨会话 attempt 污染） */
  const resetState = key => {
    const s = ensureState(key)
    s.layer = 0
    s.attempt = 0
    s.renderKey = 0
    s.minLayer = 0
  }

  return {
    // —— 模板里常用 ——
    imageRenderKey,
    imageSrc,
    stateLabel,
    handleImageError,
    // —— 业务侧细粒度 ——
    ensureState,
    resolveByLayer,
    resetState,
    clearScope,
    // —— 调试用 ——
    __state: imageStates,
  }
}

export default useCarSessionImage
