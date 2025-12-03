'use client'

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

export interface UserProfile {
  id: string
  username: string
  email?: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  userProfile: UserProfile | null
  loadingProfile: boolean
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  userProfile: null,
  loadingProfile: false,
  signOut: async () => { },
  refreshProfile: async () => { },
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const router = useRouter()
  const supabase = createClient()

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

  const fetchProfile = useCallback(async () => {
    if (!user?.id || !session?.access_token) {
      setUserProfile(null)
      return
    }

    setLoadingProfile(true)
    try {
      const response = await fetch(`${API_BASE_URL}/users/me`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        cache: 'no-store',
      })

      if (response.ok) {
        const data = await response.json()
        setUserProfile(data)
      } else if (response.status === 401) {
        // User not authenticated or token expired
        setUserProfile(null)
      } else {
        console.error('Failed to fetch user profile:', response.status)
        setUserProfile(null)
      }
    } catch (error) {
      console.error('Error fetching user profile:', error)
      setUserProfile(null)
    } finally {
      setLoadingProfile(false)
    }
  }, [user?.id, session?.access_token, API_BASE_URL])

  const refreshProfile = useCallback(async () => {
    await fetchProfile()
  }, [fetchProfile])

  useEffect(() => {
    // Get initial session
    const getSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        setSession(session)
        setUser(session?.user ?? null)
      } catch (error) {
        console.error('Error fetching session:', error)
      } finally {
        setLoading(false)
      }
    }

    getSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('Auth state changed:', event)
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)

        // Clear profile on sign out
        if (event === 'SIGNED_OUT') {
          setUserProfile(null)
        }

        // Refresh the page to update server components
        if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
          router.refresh()
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [supabase, router])

  // Fetch profile when user is authenticated
  useEffect(() => {
    if (user && session && !loading) {
      fetchProfile()
    } else if (!user) {
      setUserProfile(null)
    }
  }, [user, session, loading, fetchProfile])


  const signOut = async () => {
    try {
      // Optimistic update - clear state and redirect immediately
      setUser(null)
      setSession(null)
      setUserProfile(null)
      router.push('/login')
      router.refresh()
      
      // Perform actual sign out in background
      await supabase.auth.signOut()
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }


  return (
    <AuthContext.Provider value={{ user, session, loading, userProfile, loadingProfile, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

