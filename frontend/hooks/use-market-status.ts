'use client'

import useSWR from 'swr'
import { useApi } from '@/hooks/useApi'

export interface MarketStatus {
  is_open: boolean
  next_event: 'opens' | 'closes'
  next_event_time: string
  current_time: string
  timezone: string
}

export function useMarketStatus() {
  const { apiRequest } = useApi()

  const { data, error, isLoading } = useSWR<MarketStatus>(
    '/market/status',
    async (path) => {
      const res = await apiRequest<MarketStatus>(path)
      return res
    },
    {
      refreshInterval: 60000, // Refresh every minute
      revalidateOnFocus: true,
      shouldRetryOnError: (error) => {
        if (error instanceof Error && error.message.includes('Backend server unavailable')) {
          return false
        }
        return true
      },
      errorRetryCount: 3,
    }
  )

  // Format the next event time for display
  const formatNextEventTime = (isoString: string): string => {
    try {
      const date = new Date(isoString)
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      })
    } catch {
      return ''
    }
  }

  return {
    isOpen: data?.is_open ?? null,
    nextEvent: data?.next_event ?? null,
    nextEventTime: data?.next_event_time ? formatNextEventTime(data.next_event_time) : null,
    isLoading,
    isError: !!error,
    errorMessage: error instanceof Error ? error.message : undefined,
  }
}

