import { useState, useRef } from 'react'
import { Send, Square, Image as ImageIcon } from 'lucide-react'
import { api } from '../lib/api'

interface ChatInputProps {
  onSend: (message: string) => void
  onStop: () => void
  disabled: boolean
  isStreaming: boolean
}

export default function ChatInput({ onSend, onStop, disabled, isStreaming }: ChatInputProps) {
  const [input, setInput] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || disabled) return
    onSend(input.trim())
    setInput('')
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setAnalyzing(true)
    try {
      const analysis = await api.analyzeImage(file)
      onSend(`[Image Analysis]\n${analysis}`)
    } catch (err) {
      console.error('Image analysis failed:', err)
      alert('Failed to analyze image. Please try again.')
    } finally {
      setAnalyzing(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="border-t border-gray-200 p-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageUpload}
          accept="image/*"
          className="hidden"
        />
        
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || analyzing}
          className="p-3 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Upload crop image"
        >
          <ImageIcon className="w-5 h-5 text-gray-600" />
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={analyzing ? "Analyzing image..." : "Ask about farming, weather, market prices..."}
          disabled={disabled || analyzing}
          className="flex-1 input-field"
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            title="Stop generating"
          >
            <Square className="w-5 h-5" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim() || disabled || analyzing}
            className="p-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        )}
      </form>
    </div>
  )
}