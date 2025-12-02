'use client'

import { User } from '@supabase/supabase-js'

export async function syncUserWithBackend(
  user: User,
  apiRequest: <T>(path: string, options?: RequestInit) => Promise<T>
) {
  try {
    // Sync user profile with backend on login
    await apiRequest('/users/sync', {
      method: 'POST',
      body: JSON.stringify({
        email: user.email,
        user_id: user.id,
        metadata: user.user_metadata,
      }),
    })
    console.log('User synced with backend successfully')
  } catch (error) {
    console.error('Failed to sync user with backend:', error)
    // Don't throw - this is not critical enough to block login
  }
}






