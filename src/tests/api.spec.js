// API 层集成测试：锁定前端调用路径与后端路由一致，并验证 JWT 注入与 401 处理。
//
// 做法：替换共享 axios 实例的 adapter，请求不发出网络但完整经过拦截器链，
// 从而断言 method/url/请求体以及 Authorization 头；错误路径模拟上游 401。
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api, {
  aiAPI, apiKeyAPI, authAPI, bayesAPI, designIntentAPI, llmAPI, modifyAPI, setApiToken
} from '../api'

describe('API 路径与后端路由契约', () => {
  let captured

  beforeEach(() => {
    localStorage.clear()
    setApiToken('')
    window.location.hash = '#/'
    captured = null
    // 成功适配器：记录最终配置并返回标准成功响应
    api.defaults.adapter = vi.fn(async (config) => {
      captured = config
      return {
        data: { ok: true }, status: 200, statusText: 'OK',
        headers: {}, config
      }
    })
  })

  it('authAPI 调用注册/登录/当前用户端点', async () => {
    await authAPI.register({ email: 'a@b.com', username: 'u', password: 'pass123' })
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/auth/register')

    await authAPI.login({ email: 'a@b.com', password: 'pass123' })
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/auth/login')

    await authAPI.me()
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/auth/me')
  })

  it('apiKeyAPI 调用 Token 增查删端点并携带正确请求体', async () => {
    await apiKeyAPI.list()
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/api-keys')

    await apiKeyAPI.set('deepseek', 'sk-xxxx')
    expect(captured.method).toBe('put')
    expect(captured.url).toBe('/api-keys/deepseek')
    expect(JSON.parse(captured.data)).toEqual({ api_key: 'sk-xxxx' })

    await apiKeyAPI.remove('kimi')
    expect(captured.method).toBe('delete')
    expect(captured.url).toBe('/api-keys/kimi')
  })

  it('aiAPI 训练任务端点与 /ai/train 后台路由一致', async () => {
    await aiAPI.train({ epochs: 5 })
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/ai/train')

    await aiAPI.trainBatch({ batch_size: 10 })
    expect(captured.url).toBe('/ai/train/batch')

    await aiAPI.listTasks()
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/ai/tasks')

    await aiAPI.getTask(7)
    expect(captured.url).toBe('/ai/tasks/7')

    await aiAPI.cancelTask(7)
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/ai/tasks/7/cancel')

    await aiAPI.getTrainingCapabilities()
    expect(captured.url).toBe('/ai/training/capabilities')
  })

  it('aiAPI 分析端点路径与后端一致', async () => {
    await aiAPI.getDatasetStats()
    expect(captured.url).toBe('/ai/dataset-stats')

    await aiAPI.evaluateQuality({ surface_data: {} })
    expect(captured.url).toBe('/ai/evaluate-quality')

    await aiAPI.generateDesign({ car_type: 'sport' })
    expect(captured.url).toBe('/ai/generate-design')

    await aiAPI.optimize({ parameters: {} })
    expect(captured.url).toBe('/ai/optimize')

    await llmAPI.listProviders()
    expect(captured.url).toBe('/llm/providers')
  })

  it('modifyAPI 参数端点对接持久化路由', async () => {
    await modifyAPI.getParameters()
    expect(captured.url).toBe('/modify/parameters')

    await modifyAPI.addParameter({ name: 'p', value: 1 })
    expect(captured.url).toBe('/modify/parameters/add')

    await modifyAPI.updateParameter('p', 2)
    expect(captured.url).toBe('/modify/parameters/update')
  })

  it('bayesAPI 贝叶斯寻优容器端点与后端一致', async () => {
    await bayesAPI.createSession({ goal: 'maximize', acquisition: 'ei' })
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/bayes/sessions')

    await bayesAPI.getSession('abc')
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/bayes/sessions/abc')

    await bayesAPI.suggest('abc', 3)
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/bayes/sessions/abc/suggest')
    expect(captured.params).toEqual({ n: 3 })

    await bayesAPI.observe('abc', { overall_length: 5000 }, 88.5)
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/bayes/sessions/abc/observe')
    expect(JSON.parse(captured.data)).toEqual({
      parameters: { overall_length: 5000 }, score: 88.5
    })

    await bayesAPI.best('abc')
    expect(captured.url).toBe('/bayes/sessions/abc/best')

    await bayesAPI.samples('abc')
    expect(captured.url).toBe('/bayes/sessions/abc/samples')

    await bayesAPI.deleteSession('abc')
    expect(captured.method).toBe('delete')
    expect(captured.url).toBe('/bayes/sessions/abc')
  })

  it('designIntentAPI 意图引擎端点与后端一致并携带正确请求体', async () => {
    await designIntentAPI.parse('一台运动轿跑')
    expect(captured.method).toBe('post')
    expect(captured.url).toBe('/design-intent/parse')
    // 默认语言为 zh，lang 必须随请求体发送
    expect(JSON.parse(captured.data)).toEqual({ prompt: '一台运动轿跑', lang: 'zh' })

    await designIntentAPI.parse('a sporty coupe', 'en')
    expect(JSON.parse(captured.data)).toEqual({ prompt: 'a sporty coupe', lang: 'en' })

    await designIntentAPI.examples()
    expect(captured.method).toBe('get')
    expect(captured.url).toBe('/design-intent/examples')
  })
})

describe('JWT 请求拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    setApiToken('')
  })

  it('内存中存在令牌时自动注入 Authorization 头', async () => {
    setApiToken('jwt-abc')
    let seen
    api.defaults.adapter = vi.fn(async (config) => {
      seen = config
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })
    await authAPI.me()
    expect(seen.headers.Authorization).toBe('Bearer jwt-abc')
    // 不写入任何持久存储
    expect(localStorage.length).toBe(0)
  })

  it('无 token 时不注入 Authorization 头', async () => {
    let seen
    api.defaults.adapter = vi.fn(async (config) => {
      seen = config
      return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
    })
    await llmAPI.listProviders()
    expect(seen.headers.Authorization).toBeUndefined()
  })
})

describe('401 响应统一处理', () => {
  /** 构造一个返回 401 的适配器 */
  function unauthorizedAdapter(url) {
    return vi.fn(async (config) => {
      // 仅在目标 url 上返回 401，避免拦截其他请求
      if (config.url !== url) {
        return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
      }
      return Promise.reject({
        config,
        response: { status: 401, statusText: 'Unauthorized', data: {}, headers: {} }
      })
    })
  }

  beforeEach(() => {
    localStorage.clear()
    setApiToken('')
  })

  it('非认证端点 401：清除 token 并广播登录事件（游客可继续浏览，不强制跳转）', async () => {
    setApiToken('jwt-expired')
    window.location.hash = '#/deep-learning'
    let prompted = false
    window.addEventListener('evoai:auth-required', () => { prompted = true }, { once: true })
    api.defaults.adapter = unauthorizedAdapter('/ai/tasks')

    await expect(aiAPI.listTasks()).rejects.toBeTruthy()
    expect(prompted).toBe(true)
    expect(window.location.hash).toBe('#/deep-learning')

    // 内存令牌已清除：后续请求不再携带 Authorization
    let seen
    api.defaults.adapter = vi.fn(async (config) => {
      seen = config
      return { data: [], status: 200, statusText: 'OK', headers: {}, config }
    })
    await aiAPI.listTasks()
    expect(seen.headers.Authorization).toBeUndefined()
  })

  it('登录接口本身 401：保留现场，不跳转', async () => {
    window.location.hash = '#/login'
    api.defaults.adapter = unauthorizedAdapter('/auth/login')

    await expect(
      authAPI.login({ email: 'a@b.com', password: 'bad' })
    ).rejects.toBeTruthy()
    expect(window.location.hash).toBe('#/login')
  })
})
