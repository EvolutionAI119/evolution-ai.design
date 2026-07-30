import { llmAPI } from '../api.js'

const DEFAULT_PROVIDERS = ['ernie', 'qwen', 'hunyuan', 'doubao', 'deepseek', 'kimi']

class LLMClient {
  constructor(options = {}) {
    this.defaultProvider = options.provider || 'ernie'
    this.defaultModel = options.model || null
    this.defaultTemperature = options.temperature || 0.8
    this.providers = [...DEFAULT_PROVIDERS]
    this._readyPromise = null
  }

  async ready() {
    if (this._readyPromise) return this._readyPromise
    
    this._readyPromise = (async () => {
      try {
        const response = await llmAPI.listProviders()
        this.providers = response.data?.providers || [...DEFAULT_PROVIDERS]
      } catch {
        this.providers = [...DEFAULT_PROVIDERS]
      }
    })()
    
    return this._readyPromise
  }

  async chat(messages, options = {}) {
    await this.ready()
    
    const provider = options.provider || this.defaultProvider
    const model = options.model || this.defaultModel
    const temperature = options.temperature ?? this.defaultTemperature

    const formattedMessages = this.formatMessages(messages)

    try {
      const response = await llmAPI.chat(provider, formattedMessages, model)
      return this.parseResponse(response)
    } catch (error) {
      return this.handleError(error, 'chat', provider)
    }
  }

  async streamChat(messages, options = {}, onChunk) {
    await this.ready()
    
    const provider = options.provider || this.defaultProvider
    const model = options.model || this.defaultModel

    const formattedMessages = this.formatMessages(messages)

    try {
      const response = await llmAPI.chat(provider, formattedMessages, model)
      const content = this.parseResponse(response)?.content || ''
      
      if (onChunk && typeof onChunk === 'function') {
        for (let i = 0; i <= content.length; i += 2) {
          const chunk = content.slice(0, i)
          onChunk(chunk, i === content.length)
          await new Promise(resolve => setTimeout(resolve, 15))
        }
      }
      
      return content
    } catch (error) {
      return this.handleError(error, 'streamChat', provider)
    }
  }

  async embeddings(text, options = {}) {
    await this.ready()
    
    const provider = options.provider || this.defaultProvider

    try {
      const response = await llmAPI.embeddings(provider, text)
      return this.parseEmbeddings(response)
    } catch (error) {
      return this.handleError(error, 'embeddings', provider)
    }
  }

  async images(prompt, options = {}) {
    await this.ready()
    
    const provider = options.provider || this.defaultProvider

    try {
      const response = await llmAPI.images(provider, prompt)
      return this.parseImages(response)
    } catch (error) {
      return this.handleError(error, 'images', provider)
    }
  }

  formatMessages(messages) {
    if (Array.isArray(messages)) {
      return messages.map(msg => ({
        role: msg.role || 'user',
        content: String(msg.content || '')
      }))
    }
    return [{ role: 'user', content: String(messages) }]
  }

  parseResponse(response) {
    const data = response?.data
    if (!data) return null

    if (data.choices && data.choices.length > 0) {
      const choice = data.choices[0]
      return {
        success: true,
        content: choice.message?.content || '',
        role: choice.message?.role || 'assistant',
        finishReason: choice.finish_reason,
        usage: data.usage,
        raw: data
      }
    }

    if (data.result) {
      return {
        success: true,
        content: data.result,
        role: 'assistant',
        raw: data
      }
    }

    return {
      success: true,
      content: JSON.stringify(data),
      role: 'assistant',
      raw: data
    }
  }

  parseEmbeddings(response) {
    const data = response?.data
    if (!data) return null

    if (data.data && data.data.length > 0) {
      return {
        success: true,
        embedding: data.data[0].embedding,
        usage: data.usage,
        raw: data
      }
    }

    return {
      success: true,
      embedding: data.embedding || data,
      raw: data
    }
  }

  parseImages(response) {
    const data = response?.data
    if (!data) return null

    if (data.data && data.data.length > 0) {
      return {
        success: true,
        images: data.data.map(img => img.url || img.image),
        raw: data
      }
    }

    return {
      success: true,
      images: [data.url, data.image].filter(Boolean),
      raw: data
    }
  }

  handleError(error, type, provider) {
    const errorInfo = {
      success: false,
      error: true,
      type,
      provider,
      message: error?.message || 'LLM API error',
      response: error?.response?.data,
      status: error?.response?.status
    }

    console.error(`❌ LLM ${type} error [${provider}]:`, errorInfo)
    return errorInfo
  }

  getSupportedProviders() {
    return [...this.providers]
  }

  setDefaultProvider(provider) {
    if (this.providers.includes(provider)) {
      this.defaultProvider = provider
      return true
    }
    return false
  }

  setDefaultModel(model) {
    this.defaultModel = model
  }
}

const createLLMClient = (options = {}) => {
  return new LLMClient(options)
}

const llm = createLLMClient()

export { LLMClient, createLLMClient, llm }
export default llm