"use client"

import { useState, useCallback } from "react"
import { useApi } from "./useApi"

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  tickersContext?: TickerContext[]
  sourcesCount?: number
}

export interface TickerContext {
  ticker: string
  price: number | null
  change_percent: number | null
  sentiment: string
  post_count: number
  recent_themes: string[]
}

interface ChatRequest {
  message: string
  conversation_history: Array<{ role: string; content: string }>
  tickers: string[]
}

interface ChatResponse {
  response: string
  tickers_context: TickerContext[]
  sources_count: number
}

export function useChat() {
  const { apiRequest, isAuthenticated } = useApi()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (content: string, explicitTickers: string[] = []) => {
    if (!content.trim()) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    }

    // Add user message immediately
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setError(null)

    try {
      // Build conversation history (last 10 messages)
      const history = messages.slice(-10).map(m => ({
        role: m.role,
        content: m.content,
      }))

      const request: ChatRequest = {
        message: content.trim(),
        conversation_history: history,
        tickers: explicitTickers,
      }

      const response = await apiRequest<ChatResponse>("/chat/ask", {
        method: "POST",
        body: JSON.stringify(request),
      })

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
        tickersContext: response.tickers_context,
        sourcesCount: response.sources_count,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to get response"
      setError(errorMessage)
      
      // Add error message to chat
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }, [apiRequest, messages])

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
    isAuthenticated,
  }
}






