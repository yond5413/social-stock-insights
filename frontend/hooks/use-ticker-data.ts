'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { useApi } from '@/hooks/useApi'

export interface TickerPost {
  id: string
  user_id: string
  username: string
  content: string
  tickers: string[]
  llm_status: string
  created_at: string
  view_count: number
  like_count: number
  comment_count: number
  engagement_score: number
  user_has_liked: boolean
  summary?: string
  explanation?: string
  sentiment?: string
  quality_score?: number
  insight_type?: string
  sector?: string
  author_reputation: number
  is_processing: boolean
}

export interface TickerPostsData {
  ticker: string
  posts: TickerPost[]
  total: number
  sentiment_summary: {
    bullish: number
    bearish: number
    neutral: number
  }
  has_more: boolean
  from_cache?: boolean
}

export interface TickerSentiment {
  ticker: string
  total_posts: number
  processed_posts: number
  pending_posts: number
  sentiment_summary: {
    bullish: number
    bearish: number
    neutral: number
  }
  weighted_sentiment: {
    bullish: number
    bearish: number
    neutral: number
  }
  confidence_level: 'high' | 'medium' | 'low' | 'pending'
  avg_engagement: number
  top_themes: string[]
  from_cache?: boolean
}

interface WebSocketMessage {
  type: 'connected' | 'new_post' | 'post_processed' | 'keepalive' | 'pong'
  ticker?: string
  post_id?: string
  message?: string
  timestamp: string
}

const RECONNECT_INTERVAL = 5000 // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 5

export function useTickerData(ticker: string) {
  const { apiRequest, isAuthenticated } = useApi()
  const [wsConnected, setWsConnected] = useState(false)
  const [hasNewPosts, setHasNewPosts] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null)

  // Fetch posts with SWR
  const {
    data: postsData,
    error: postsError,
    isLoading: postsLoading,
    mutate: mutatePosts
  } = useSWR<TickerPostsData>(
    ticker ? `/posts/by-ticker/${ticker}?limit=20` : null,
    async (path) => {
      const res = await apiRequest<TickerPostsData>(path)
      return res
    },
    {
      refreshInterval: 60000, // Refresh every 60 seconds as fallback
      revalidateOnFocus: true,
      shouldRetryOnError: true,
      errorRetryCount: 3,
    }
  )

  // Fetch sentiment with SWR
  const {
    data: sentimentData,
    error: sentimentError,
    isLoading: sentimentLoading,
    mutate: mutateSentiment
  } = useSWR<TickerSentiment>(
    ticker ? `/insights/ticker/${ticker}/sentiment` : null,
    async (path) => {
      const res = await apiRequest<TickerSentiment>(path)
      return res
    },
    {
      refreshInterval: 300000, // Refresh every 5 minutes
      revalidateOnFocus: true,
      shouldRetryOnError: true,
      errorRetryCount: 3,
    }
  )

  const connectWebSocket = useCallback(() => {
    if (!ticker || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    // Use ws:// for localhost, wss:// for production
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    const wsBaseUrl = apiBaseUrl.replace(/^https?:\/\//, '')
    const wsUrl = `${wsProtocol}//${wsBaseUrl}/posts/ws/ticker/${ticker}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
        reconnectAttempts.current = 0
        console.log(`WebSocket connected for ticker: ${ticker}`)
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)

          if (message.type === 'new_post' || message.type === 'post_processed') {
            // Mark that new posts are available
            setHasNewPosts(true)

            // Optionally auto-refresh if user preference
            // For now, we'll just notify
          } else if (message.type === 'connected') {
            console.log(`Connected to ticker updates: ${message.message}`)
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        setWsConnected(false)
        wsRef.current = null

        // Attempt to reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1
          reconnectTimeout.current = setTimeout(() => {
            console.log(`Reconnecting WebSocket (attempt ${reconnectAttempts.current})...`)
            connectWebSocket()
          }, RECONNECT_INTERVAL)
        }
      }

      // Send periodic pings to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 25000) // Every 25 seconds

      // Clean up ping interval when socket closes
      ws.addEventListener('close', () => {
        clearInterval(pingInterval)
      })

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }, [ticker])

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
    if (ticker) {
      connectWebSocket()
    }
    return () => {
      disconnectWebSocket()
    }
  }, [ticker, connectWebSocket, disconnectWebSocket])

  // Refresh data when user acknowledges new posts
  const refresh = useCallback(() => {
    setHasNewPosts(false)
    mutatePosts()
    mutateSentiment()
  }, [mutatePosts, mutateSentiment])

  // Mark a post as viewed (could update view count via API)
  const markAsViewed = useCallback(async (postId: string) => {
    // Implement view tracking if needed
    // For now, this is a placeholder
    console.log(`Post ${postId} viewed`)
  }, [])

  return {
    // Posts data
    posts: postsData?.posts || [],
    totalPosts: postsData?.total || 0,
    sentimentSummary: postsData?.sentiment_summary || { bullish: 0, bearish: 0, neutral: 0 },
    hasMore: postsData?.has_more || false,

    // Sentiment data
    sentiment: sentimentData,
    confidenceLevel: sentimentData?.confidence_level || 'low',
    weightedSentiment: sentimentData?.weighted_sentiment || { bullish: 0, bearish: 0, neutral: 0 },
    topThemes: sentimentData?.top_themes || [],

    // Loading states
    isLoading: postsLoading || sentimentLoading,
    isError: !!postsError || !!sentimentError,
    error: postsError || sentimentError,

    // WebSocket state
    wsConnected,
    hasNewPosts,

    // Methods
    refresh,
    markAsViewed,
    reconnect: connectWebSocket,
  }
}



