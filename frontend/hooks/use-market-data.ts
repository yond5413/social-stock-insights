'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { useApi } from '@/hooks/useApi'

export interface MarketTicker {
  ticker: string
  price: number
  change_percent: number
  volume: number
  mentions?: number
}

interface WebSocketMessage {
  type: 'market_update' | 'error'
  data?: MarketTicker[]
  status?: {
    is_open: boolean
    next_event: string
    next_event_time: string
  }
  message?: string
  timestamp: string
}

const RECONNECT_INTERVAL = 5000 // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 5

export function useMarketData() {
  const { apiRequest, isAuthenticated } = useApi()
  const [wsData, setWsData] = useState<MarketTicker[] | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [wsError, setWsError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)

  // SWR for initial fetch and fallback
  const { data: swrData, error: swrError, isLoading, mutate } = useSWR<MarketTicker[]>(
    '/market/trending',
    async (path) => {
      const res = await apiRequest<MarketTicker[]>(path)
      return res
    },
    {
      refreshInterval: 60000, // Refresh every 60 seconds as fallback
      revalidateOnFocus: false,
      shouldRetryOnError: (error) => {
        if (error instanceof Error && error.message.includes('Backend server unavailable')) {
          return false
        }
        return true
      },
      errorRetryCount: 3,
    }
  )

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    // Use ws:// for localhost, wss:// for production
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    const wsBaseUrl = apiBaseUrl.replace(/^https?:\/\//, '')
    const wsUrl = `${wsProtocol}//${wsBaseUrl}/market/ws/stream`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
        setWsError(null)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          if (message.type === 'market_update' && message.data) {
            setWsData(message.data)
            // Also update SWR cache
            mutate(message.data, false)
          } else if (message.type === 'error') {
            setWsError(message.message || 'Unknown error')
          }
        } catch {
          console.error('Failed to parse WebSocket message')
        }
      }

      ws.onerror = () => {
        setWsError('WebSocket connection error')
      }

      ws.onclose = () => {
        setWsConnected(false)
        wsRef.current = null

        // Attempt to reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          reconnectTimeout.current = setTimeout(() => {
            connectWebSocket()
          }, RECONNECT_INTERVAL)
        }
      }
    } catch {
      setWsError('Failed to create WebSocket connection')
    }
  }, [mutate])

  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setWsConnected(false)
  }, [])

  // Connect WebSocket on mount
  useEffect(() => {
    connectWebSocket()
    return () => {
      disconnectWebSocket()
    }
  }, [connectWebSocket, disconnectWebSocket])

  // Use WebSocket data if available, otherwise fall back to SWR data
  const data = wsData || swrData || []

  // Check if error is a network/backend unavailable error
  const isNetworkError = swrError instanceof Error && 
    (swrError.message.includes('Backend server unavailable') || 
     swrError.message.includes('Network error'))

  return {
    data,
    isLoading: isLoading && !wsData,
    isError: swrError && !wsData,
    isNetworkError: isNetworkError && !wsData,
    errorMessage: (swrError instanceof Error ? swrError.message : undefined) || wsError,
    wsConnected,
    mutate,
    reconnect: connectWebSocket,
  }
}


