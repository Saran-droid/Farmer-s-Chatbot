export interface User {
  id: number
  name: string
  email: string
}

export interface Conversation {
  id: number
  title: string
  created_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface MarketRecord {
  market: string
  price: number
  min_price: number
  max_price: number
  date: string
}

export interface MarketData {
  crop: string
  state: string
  records: MarketRecord[]
}

class API {
  private baseURL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

  async register(name: string, email: string, password: string): Promise<User> {
    const res = await fetch(`${this.baseURL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, email, password })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Registration failed')
    }
    const data = await res.json()
    return data.user
  }

  async login(email: string, password: string): Promise<User> {
    const res = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    return data.user
  }

  async logout(): Promise<void> {
    await fetch(`${this.baseURL}/auth/logout`, {
      method: 'POST',
      credentials: 'include'
    })
  }

  async getMe(): Promise<User | null> {
    try {
      const res = await fetch(`${this.baseURL}/auth/me`, {
        credentials: 'include'
      })
      if (!res.ok) return null
      return await res.json()
    } catch {
      return null
    }
  }

  async getConversations(): Promise<Conversation[]> {
    const res = await fetch(`${this.baseURL}/api/conversations`, {
      credentials: 'include'
    })
    if (!res.ok) throw new Error('Failed to fetch conversations')
    return await res.json()
  }

  async createConversation(): Promise<Conversation> {
    const res = await fetch(`${this.baseURL}/api/conversations`, {
      method: 'POST',
      credentials: 'include'
    })
    if (!res.ok) throw new Error('Failed to create conversation')
    return await res.json()
  }

  async deleteConversation(id: number): Promise<void> {
    const res = await fetch(`${this.baseURL}/api/conversations/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    })
    if (!res.ok) throw new Error('Failed to delete conversation')
  }

  async getMessages(conversationId: number): Promise<Message[]> {
    const res = await fetch(`${this.baseURL}/api/conversations/${conversationId}/messages`, {
      credentials: 'include'
    })
    if (!res.ok) throw new Error('Failed to fetch messages')
    return await res.json()
  }

  async analyzeImage(file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${this.baseURL}/api/analyze-image`, {
      method: 'POST',
      credentials: 'include',
      body: formData
    })
    if (!res.ok) throw new Error('Failed to analyze image')
    const data = await res.json()
    return data.analysis
  }

  streamChat(
    query: string,
    conversationId: number | null,
    onToken: (token: string) => void,
    onStatus: (status: string) => void,
    onMarketData: (data: MarketData) => void,
    onConvId: (id: number) => void,
    onDone: (fullResponse: string) => void,
    onError: (error: string) => void
  ): () => void {
    const controller = new AbortController()

    fetch(`${this.baseURL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query, conversation_id: conversationId }),
      signal: controller.signal
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('Chat request failed')
        const reader = res.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // SSE messages are separated by double newlines
          const blocks = buffer.split('\n\n')
          buffer = blocks.pop() ?? ''

          for (const block of blocks) {
            if (!block.trim()) continue

            let event = 'message'
            let dataStr = ''

            for (const line of block.split('\n')) {
              if (line.startsWith('event: ')) {
                event = line.slice(7).trim()
              } else if (line.startsWith('data: ')) {
                dataStr = line.slice(6).trim()
              }
            }

            if (!dataStr) continue

            try {
              const data = JSON.parse(dataStr)

              if (event === 'token') {
                onToken(data.text)
              } else if (event === 'status') {
                onStatus(data.message)
              } else if (event === 'market_data') {
                onMarketData(data)
              } else if (event === 'conv_id') {
                onConvId(data.conv_id)
              } else if (event === 'translated') {
                // Server sent a translated full response – surface as done
                onDone(data.full_response)
              } else if (event === 'done') {
                onDone(data.full_response)
              } else if (event === 'error') {
                onError(data.message)
              }
            } catch (e) {
              console.error('Failed to parse SSE block:', e, block)
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err.message || 'Connection failed')
        }
      })

    return () => controller.abort()
  }
}

export const api = new API()
