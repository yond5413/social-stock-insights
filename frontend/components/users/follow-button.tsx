"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { createClient } from "@/lib/supabase/client"
import { Loader2, UserPlus, UserCheck } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface FollowButtonProps {
    userId: string
    initialIsFollowing?: boolean
    onFollowChange?: (isFollowing: boolean) => void
}

export function FollowButton({ userId, initialIsFollowing, onFollowChange }: FollowButtonProps) {
    const [isFollowing, setIsFollowing] = useState(initialIsFollowing || false)
    const [loading, setLoading] = useState(true)
    const [actionLoading, setActionLoading] = useState(false)
    const { toast } = useToast()
    const supabase = createClient()

    useEffect(() => {
        if (initialIsFollowing !== undefined) {
            setLoading(false)
            return
        }

        const checkFollowStatus = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession()
                if (!session) return

                // Don't show follow button for self
                if (session.user.id === userId) {
                    setLoading(false)
                    return
                }

                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/${userId}/stats`, {
                    headers: {
                        Authorization: `Bearer ${session.access_token}`
                    }
                })

                if (response.ok) {
                    const data = await response.json()
                    setIsFollowing(data.is_following)
                }
            } catch (error) {
                console.error("Error checking follow status:", error)
            } finally {
                setLoading(false)
            }
        }

        checkFollowStatus()
    }, [userId, initialIsFollowing, supabase])

    const handleFollowToggle = async () => {
        setActionLoading(true)
        try {
            const { data: { session } } = await supabase.auth.getSession()
            if (!session) {
                toast({
                    title: "Authentication required",
                    description: "Please sign in to follow users.",
                    variant: "destructive",
                })
                return
            }

            const method = isFollowing ? "DELETE" : "POST"
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/${userId}/follow`, {
                method,
                headers: {
                    Authorization: `Bearer ${session.access_token}`
                }
            })

            if (!response.ok) throw new Error("Failed to update follow status")

            const newStatus = !isFollowing
            setIsFollowing(newStatus)
            onFollowChange?.(newStatus)

            toast({
                title: newStatus ? "Following" : "Unfollowed",
                description: newStatus ? "You are now following this user." : "You have unfollowed this user.",
            })
        } catch (error) {
            console.error("Error updating follow status:", error)
            toast({
                title: "Error",
                description: "Failed to update follow status. Please try again.",
                variant: "destructive",
            })
        } finally {
            setActionLoading(false)
        }
    }

    if (loading) {
        return (
            <Button variant="ghost" size="sm" disabled>
                <Loader2 className="h-4 w-4 animate-spin" />
            </Button>
        )
    }

    // Don't render anything if it's the current user (handled by logic above but safe to return null)
    // We need to check current user ID to be sure, but for now we rely on the effect.
    // Ideally we'd pass currentUserId as prop or get from context, but fetching session in effect handles it.

    return (
        <Button
            variant={isFollowing ? "secondary" : "default"}
            size="sm"
            onClick={handleFollowToggle}
            disabled={actionLoading}
            className={isFollowing ? "bg-muted text-muted-foreground hover:bg-muted/80" : ""}
        >
            {actionLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : isFollowing ? (
                <UserCheck className="h-4 w-4 mr-2" />
            ) : (
                <UserPlus className="h-4 w-4 mr-2" />
            )}
            {isFollowing ? "Following" : "Follow"}
        </Button>
    )
}
