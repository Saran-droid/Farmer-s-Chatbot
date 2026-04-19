import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import type { Conversation, Message, MarketData } from '../lib/api'
import Sidebar from '../components/Sidebar'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import MarketCard from '../components/MarketCard'
import { Sprout, Menu, X } from 'lucide-react'

export default function Chat() {
  const { user, logout } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streamingMessage, setStreamingMessage] = useState('')
  const [status, setStatus] = useState('')
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  useEffect(() => {
    if (currentConvId) {
      loadMessages(currentConvId)
    }
  }, [currentConvId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  const loadConversations = async () => {
    try {
      const convs = await api.getConversations()
      setConversations(convs)
      if (convs.length > 0 && !currentConvId) {
        setCurrentConvId(convs[0].id)
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
  }

  const loadMessages = async (convId: number) => {
    try {
      const msgs = await api.getMessages(convId)
      setMessages(msgs)
      setStreamingMessage('')
      setMarketData(null)
    } catch (err) {
      console.error('Failed to load messages:', err)
    }
  }

  const handleNewChat = async () => {
    try {
      const conv = await api.createConversation()
      setConversations([conv, ...conversations])
      setCurrentConvId(conv.id)
      setMessages([])
      setStreamingMessage('')
      setMarketData(null)
    } catch (err) {
      console.error('Failed to create conversation:', err)
    }
  }

  const handleDeleteConversation = async (id: number) => {
    try {
      await api.deleteConversation(id)
      setConversations(conversations.filter(c => c.id !== id))
      if (currentConvId === id) {
        const remaining = conversations.filter(c => c.id !== id)
        setCurrentConvId(remaining.length > 0 ? remaining[0].id : null)
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err)
    }
  }

  const handleSendMessage = (query: string) => {
    if (isStreaming) return

    setIsStreaming(true)
    setStreamingMessage('')
    setStatus('Processing...')
    setMarketData(null)

    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])

    abortRef.current = api.streamChat(
      query,
      currentConvId,
      (token) => {
        setStreamingMessage(prev => prev + token)
      },
      (statusMsg) => {
        setStatus(statusMsg)
      },
      (data) => {
        setMarketData(data)
      },
      (convId) => {
        if (!currentConvId) {
          setCurrentConvId(convId)
          loadConversations()
        }
      },
      (fullResponse) => {
        const assistantMsg: Message = {
          id: Date.now() + 1,
          role: 'assistant',
          content: fullResponse,
          created_at: new Date().toISOString()
        }
        setMessages(prev => [...prev, assistantMsg])
        setStreamingMessage('')
        setStatus('')
        setIsStreaming(false)
        loadConversations()
      },
      (error) => {
        console.error('Chat error:', error)
        setStatus('')
        setStreamingMessage('')
        setIsStreaming(false)
      }
    )
  }

  const handleStopStreaming = () => {
    if (abortRef.current) {
      abortRef.current()
      abortRef.current = null
    }
    setIsStreaming(false)
    setStreamingMessage('')
    setStatus('')
  }

  return (
    <div className="h-screen flex overflow-hidden">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div
        className={`fixed lg:static inset-y-0 left-0 z-50 w-80 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar
          conversations={conversations}
          currentConvId={currentConvId}
          onSelectConversation={(id) => {
            setCurrentConvId(id)
            setSidebarOpen(false)
          }}
          onNewChat={handleNewChat}
          onDeleteConversation={handleDeleteConversation}
          onLogout={logout}
          user={user!}
        />
      </div>

      <div className="flex-1 flex flex-col bg-white">
        <div className="border-b border-gray-200 px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          <div className="flex items-center gap-2">
            <Sprout className="w-6 h-6 text-primary-600" />
            <h1 className="text-xl font-bold text-gray-800">AgriConnect</h1>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !streamingMessage && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="bg-primary-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Sprout className="w-8 h-8 text-primary-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">
                  Welcome to AgriConnect
                </h2>
                <p className="text-gray-600">
                  Ask me anything about farming, weather, market prices, pest control, or crop recommendations!
                </p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {streamingMessage && (
            <ChatMessage
              message={{
                id: -1,
                role: 'assistant',
                content: streamingMessage,
                created_at: new Date().toISOString()
              }}
              isStreaming
            />
          )}

          {status && (
            <div className="flex justify-center">
              <div className="bg-primary-50 text-primary-700 px-4 py-2 rounded-full text-sm">
                {status}
              </div>
            </div>
          )}

          {marketData && <MarketCard data={marketData} />}

          <div ref={messagesEndRef} />
        </div>

        <ChatInput
          onSend={handleSendMessage}
          onStop={handleStopStreaming}
          disabled={isStreaming}
          isStreaming={isStreaming}
        />
      </div>
    </div>
  )
}