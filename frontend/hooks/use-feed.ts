'use client'

import useSWR from "swr"
import { useApi } from "@/hooks/useApi"
import { FeedItem } from "@/lib/types"

export function useFeed() {
  const { apiRequest, isAuthenticated } = useApi()
  
  const { data, error, isLoading, mutate } = useSWR<FeedItem[]>(
    isAuthenticated ? "/feed" : null,
    async (path) => {
      try {
        const res = await apiRequest<FeedItem[]>(path)
        return res
      } catch (err) {
        // SWR will handle the error and set error state
        // We don't need to log here as useApi already handles logging
        throw err
      }
    },
    {
      // Retry configuration for network errors
      shouldRetryOnError: (error) => {
        // Don't retry on network errors (backend not running)
        if (error instanceof Error && error.message.includes('Backend server unavailable')) {
          return false
        }
        // Retry other errors up to 3 times
        return true
      },
      errorRetryCount: 3,
      errorRetryInterval: 1000,
    }
  )

  // Check if error is a network/backend unavailable error
  const isNetworkError = error instanceof Error && 
    (error.message.includes('Backend server unavailable') || 
     error.message.includes('Network error'))

  return {
    feed: data || [],
    isLoading,
    isError: error,
    isNetworkError,
    errorMessage: error instanceof Error ? error.message : undefined,
    mutate,
  }
}
