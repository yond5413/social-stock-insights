"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Loader2, UserPlus, UserCheck } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { useApi } from "@/hooks/useApi"
import { useAuth } from "@/contexts/AuthContext"

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
    const { apiRequest } = useApi()
    const { user } = useAuth()

    useEffect(() => {
        if (initialIsFollowing !== undefined) {
            setLoading(false)
            return
        }

        const checkFollowStatus = async () => {
            if (!user) {
                setLoading(false)
                return
            }
            
            // Don't show follow button for self
            if (user.id === userId) {
                setLoading(false)
                return
            }

            try {
                const data = await apiRequest<{ is_following: boolean }>(`/users/${userId}/stats`)
                setIsFollowing(data.is_following)
            } catch (error) {
                console.error("Error checking follow status:", error)
            } finally {
                setLoading(false)
            }
        }

        checkFollowStatus()
    }, [userId, initialIsFollowing, user, apiRequest])

    const handleFollowToggle = async () => {
        if (!user) {
            toast({
                title: "Authentication required",
                description: "Please sign in to follow users.",
                variant: "destructive",
            })
            return
        }

        setActionLoading(true)
        try {
            const method = isFollowing ? "DELETE" : "POST"
            await apiRequest(`/users/${userId}/follow`, {
                method,
            })

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

    // Don't render if it's the current user
    if (user?.id === userId) {
        return null
    }

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
