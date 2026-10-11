import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useCarSessionImage } from '../utils/useCarSessionImage.js'
import { clearFailedMarks } from '../utils/carImageManager.js'

// 回归：L1 /brands/* 静态真车图一次瞬时 error 不得把卡片永久降级成 SVG
// （历史缺陷：CDN 抖动/隧道中断/快速切品牌导致的单次 onerror，会让 minLayer
//  只进不退，而公网 L2 远程图必然失败，整个会话锁死轮廓 SVG——"图片漂移"）
describe('useCarSessionImage L1 静态图瞬时失败重试', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    clearFailedMarks()
  })
  afterEach(() => {
    vi.useRealTimers()
    clearFailedMarks()
  })

  const ctx = {
    brandKey: 'porsche',
    modelKey: 'cayenne',
    params: { front_overhang: 950, rear_overhang: 1081, wheel_base: 2895 },
  }
  const flush = () => vi.advanceTimersByTimeAsync(2000)

  it('L1 连续 3 次瞬时失败：保持在 L1 并重挂重试，不进失败名单', async () => {
    const { imageSrc, handleImageError, stateLabel, __state } =
      useCarSessionImage('test-l1-retry')
    const key = 'k1'

    expect(imageSrc(key, ctx)).toBe('/brands/porsche/cayenne.jpg')
    for (let i = 0; i < 3; i++) {
      handleImageError(key, ctx)
      await flush()
      // 始终解析回 L1 静态图，绝不落入远程图或 SVG
      expect(imageSrc(key, ctx)).toBe('/brands/porsche/cayenne.jpg')
      expect(__state[key].minLayer).toBe(0)
      expect(stateLabel(key)).toBe('L1')
    }
    // renderKey 每次重挂都递增
    expect(__state[key].renderKey).toBe(3)
  })

  it('快速重试耗尽后临时 L3 占位，10s 自愈探测自动回到 L1', async () => {
    const { imageSrc, handleImageError, __state } =
      useCarSessionImage('test-l1-recover')
    const key = 'k2'

    imageSrc(key, ctx)
    for (let i = 0; i < 4; i++) {
      handleImageError(key, ctx)
      await flush()
    }
    // 第 4 次：退到临时 SVG 占位
    expect(__state[key].minLayer).toBe(2)
    expect(imageSrc(key, ctx).startsWith('data:image/svg+xml')).toBe(true)

    // 10s 自愈定时器触发：回到 L1
    await vi.advanceTimersByTimeAsync(10001)
    expect(__state[key].minLayer).toBe(0)
    expect(imageSrc(key, ctx)).toBe('/brands/porsche/cayenne.jpg')
  })

  it('L1 加载成功（@load）：取消挂起重试、状态归零', async () => {
    const { handleImageError, handleImageLoad, __state } =
      useCarSessionImage('test-l1-load')
    const key = 'k3'

    handleImageError(key, ctx)
    expect(__state[key].l1Retries).toBe(1)
    // 第一次重试 delay=0：错误处理后同步可见挂起的定时器
    expect(__state[key]._retryTimer).toBeTruthy()

    handleImageLoad(key)
    expect(__state[key].l1Retries).toBe(0)
    expect(__state[key]._retryTimer).toBeNull()
    expect(__state[key].minLayer).toBe(0)
  })

  it('L2 远程图失败仍按原逻辑逐层推进并进入失败名单', async () => {
    const { imageSrc, handleImageError, __state } =
      useCarSessionImage('test-l2-advance')
    const key = 'k4'
    // brandKey 为空 → 无 L1 静态图层，首层即 L2 远程图
    const remoteCtx = {
      model: { key: 'dream-x', image: 'https://example.invalid/ai.png', params: {} },
      brandKey: '',
    }
    // 无静态图（brandKey 目录不存在）：首层即 L2
    expect(imageSrc(key, remoteCtx)).toBe('https://example.invalid/ai.png')
    handleImageError(key, remoteCtx)
    await flush()
    // L2 失败 → minLayer>=2 → 落到 L3 SVG
    expect(__state[key].minLayer).toBe(2)
    expect(imageSrc(key, remoteCtx).startsWith('data:image/svg+xml')).toBe(true)
  })
})
