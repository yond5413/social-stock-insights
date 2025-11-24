'use client'

import { useAuth } from '@/contexts/AuthContext'
import { useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'

export function useApi() {
  const { session, signOut } = useAuth()
  const router = useRouter()
  const API_BASE_URL = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    []
  )

  const apiRequest = useCallback(async <T,>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> => {
    const token = session?.access_token

    const headers = new Headers(options.headers)
    headers.set('Content-Type', 'application/json')
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const url = `${API_BASE_URL}${path}`
    
    try {
      const res = await fetch(url, {
        ...options,
        headers,
        cache: 'no-store',
      })

      // Handle 401 - token expired or invalid
      if (res.status === 401) {
        console.warn('Authentication failed, signing out...')
        await signOut()
        throw new Error('Session expired. Please login again.')
      }

      if (!res.ok) {
        const text = await res.text()
        let errorMessage = `Request failed with status ${res.status}`
        try {
          const errorJson = JSON.parse(text)
          errorMessage = errorJson.detail || errorJson.message || text
        } catch {
          errorMessage = text || errorMessage
        }
        throw new Error(errorMessage)
      }

      return await res.json() as T
    } catch (error) {
      // Handle network errors (Failed to fetch)
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        const networkError = new Error(
          `Backend server unavailable at ${API_BASE_URL}`
        )
        // Only log once per session to reduce console noise
        if (!(window as any).__backendErrorLogged) {
          console.warn(
            `⚠️ Backend server not running. ` +
            `Start it with: cd backend && uvicorn app.main:app --reload --port 8000`
          )
          ;(window as any).__backendErrorLogged = true
        }
        throw networkError
      }
      
      // Handle other fetch errors
      if (error instanceof Error && error.name === 'TypeError' && error.message.includes('fetch')) {
        const networkError = new Error(
          `Network error: Unable to reach ${url}`
        )
        console.warn('Network error:', networkError.message)
        throw networkError
      }
      
      // Re-throw other errors as-is
      throw error
    }
  }, [session, signOut, router, API_BASE_URL])

  return { 
    apiRequest, 
    isAuthenticated: !!session,
    token: session?.access_token 
  }
}

