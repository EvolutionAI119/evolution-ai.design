import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { demoMode, probeApi } from '../utils/apiProbe'

const CACHE_KEY = 'evo_api_probe_v1'

// API 探测 / 演示模式判定
describe('apiProbe：后端可达性探测与演示模式', () => {
  beforeEach(() => {
    sessionStorage.clear()
    demoMode.value = false
    vi.unstubAllGlobals()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('fetch 200 → API 可用，demoMode=false', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200 })))
    const ok = await probeApi()
    expect(ok).toBe(true)
    expect(demoMode.value).toBe(false)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('fetch 404（静态站）→ demoMode=true', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404 })))
    const ok = await probeApi()
    expect(ok).toBe(false)
    expect(demoMode.value).toBe(true)
  })

  it('fetch 网络异常/超时 → demoMode=true（不抛出）', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    const ok = await probeApi()
    expect(ok).toBe(false)
    expect(demoMode.value).toBe(true)
  })

  it('sessionStorage 缓存：10 分钟内第二次探测不再发请求', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404 })))
    await probeApi()
    expect(sessionStorage.getItem(CACHE_KEY)).toBeTruthy()
    demoMode.value = false // 强行复位，验证缓存回填
    const ok = await probeApi()
    expect(fetch).toHaveBeenCalledTimes(1)   // 仅首次探测发请求
    expect(ok).toBe(false)
    expect(demoMode.value).toBe(true)        // 结论从缓存回填
  })

  it('缓存损坏时重新探测，不抛异常', async () => {
    sessionStorage.setItem(CACHE_KEY, '{broken json')
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200 })))
    const ok = await probeApi()
    expect(ok).toBe(true)
    expect(demoMode.value).toBe(false)
  })
})
