"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { useAuth } from "@/contexts/AuthContext"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { GradientText } from "@/components/ui/gradient-text"
import { StatCard } from "@/components/ui/stat-card"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { Edit, MessageSquare, TrendingUp, Award, Star, Sparkles, Loader2 } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"
import { useApi } from "@/hooks/useApi"
import { FeedItem } from "@/lib/types"
import { PostCard } from "@/components/feed/post-card"
import { EditUsernameDialog } from "./edit-username-dialog"

interface UserStats {
  followers_count: number
  following_count: number
  reputation: number
}

export default function ProfilePage() {
  const { user, userProfile, refreshProfile } = useAuth()
  const { apiRequest } = useApi()
  const [posts, setPosts] = useState<FeedItem[]>([])
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [loadingPosts, setLoadingPosts] = useState(true)
  const [loadingStats, setLoadingStats] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    const fetchPosts = async () => {
      if (!user?.id) return
      try {
        const data = await apiRequest<FeedItem[]>(`/posts/user/${user.id}?limit=10`)
        setPosts(data)
      } catch (error) {
        console.error("Failed to fetch user posts:", error)
      } finally {
        setLoadingPosts(false)
      }
    }

    fetchPosts()
  }, [user?.id, apiRequest])

  useEffect(() => {
    const fetchStats = async () => {
      if (!user?.id) return
      try {
        const data = await apiRequest<UserStats>(`/users/${user.id}/stats`)
        setUserStats(data)
      } catch (error) {
        console.error("Failed to fetch user stats:", error)
      } finally {
        setLoadingStats(false)
      }
    }

    fetchStats()
  }, [user?.id, apiRequest])

  const handleUpdateProfile = async (newUsername: string) => {
    if (!user?.id || !newUsername.trim()) return

    await apiRequest("/users/profile", {
      method: "PUT",
      body: JSON.stringify({ username: newUsername }),
    })

    // Refresh profile in context to sync across all components
    await refreshProfile()

    toast({
      title: "Profile updated",
      description: "Your username has been updated successfully.",
    })
  }

  if (!user) {
    return (
      <DashboardShell>
        <div className="flex flex-col gap-4 p-4">
          <h1 className="text-2xl font-bold">Profile</h1>
          <p>Please sign in to view your profile.</p>
        </div>
      </DashboardShell>
    )
  }

  // Calculate stats from real data
  const stats = {
    posts: posts.length,
    reputation: userStats ? Math.round((userStats.reputation || 0) * 1000) : 0,
    accuracy: userStats ? Math.round((userStats.reputation || 0) * 100) : 0, // Using reputation as accuracy proxy
  }

  const achievements = [
    { id: 1, name: "First Post", icon: "🎯", unlocked: posts.length > 0 },
    { id: 2, name: "10 Posts", icon: "🔥", unlocked: posts.length >= 10 },
    { id: 3, name: "Top Contributor", icon: "⭐", unlocked: (userStats?.reputation || 0) > 0.7 },
    { id: 4, name: "Expert Analyst", icon: "🏆", unlocked: (userStats?.reputation || 0) > 0.9 },
  ]

  return (
    <DashboardShell>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-6"
      >
        {/* Cover & Avatar */}
        <motion.div variants={fadeInUp} className="relative">
          {/* Premium Cover Photo */}
          <div className="h-32 md:h-48 rounded-xl relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
            {/* Animated gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-purple-500/10 to-slate-500/20 animate-pulse" />

            {/* Geometric pattern */}
            <div className="absolute inset-0" style={{
              backgroundImage: `radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                               radial-gradient(circle at 75% 75%, rgba(147, 51, 234, 0.1) 0%, transparent 50%),
                               linear-gradient(45deg, transparent 48%, rgba(59, 130, 246, 0.05) 50%, transparent 52%),
                               linear-gradient(-45deg, transparent 48%, rgba(147, 51, 234, 0.05) 50%, transparent 52%)`,
              backgroundSize: '100% 100%, 100% 100%, 20px 20px, 20px 20px'
            }} />

            {/* Glass effect overlay */}
            <div className="absolute inset-0 backdrop-blur-[1px] bg-gradient-to-t from-background/80 via-transparent to-transparent" />

            {/* Floating orbs */}
            <div className="absolute top-4 left-[20%] w-32 h-32 bg-blue-500/10 rounded-full blur-2xl animate-pulse" />
            <div className="absolute bottom-4 right-[30%] w-40 h-40 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
          </div>

          {/* Avatar & Basic Info */}
          <div className="relative px-4 md:px-6 pb-6">
            <div className="flex flex-col md:flex-row gap-4 md:gap-6 -mt-12 md:-mt-16">
              {/* Avatar */}
              <div className="relative">
                <div className="p-1 rounded-2xl bg-gradient-to-br from-blue-500 to-slate-500">
                  <Avatar className="h-24 w-24 md:h-32 md:w-32 border-4 border-background">
                    <AvatarImage src={`https://avatar.vercel.sh/${user.id}`} />
                    <AvatarFallback className="text-2xl md:text-4xl font-bold bg-gradient-to-br from-blue-500 to-slate-500 text-white">
                      {user.email?.charAt(0).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                </div>
                <Button
                  size="icon"
                  variant="secondary"
                  className="absolute bottom-0 right-0 h-8 w-8 rounded-full shadow-lg"
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </div>

              {/* Info */}
              <div className="flex-1 flex flex-col justify-end space-y-2">
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl md:text-3xl font-bold">
                    {userProfile?.username || user.email?.split('@')[0] || 'User'}
                  </h1>
                  <Badge className="bg-gradient-to-r from-blue-500 to-slate-500 text-white border-0">
                    <Sparkles className="h-3 w-3 mr-1" />
                    Pro
                  </Badge>
                </div>
                <div className="flex gap-2 mt-2">
                  <Button
                    size="sm"
                    className="bg-gradient-to-r from-blue-500 to-slate-500 hover:from-blue-600 hover:to-slate-600"
                    onClick={() => setDialogOpen(true)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit Profile
                  </Button>
                  <Button size="sm" variant="outline">
                    Share Profile
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div variants={fadeInUp} className="grid gap-4 md:grid-cols-3">
          {loadingStats ? (
            <>
              <Card className="animate-pulse">
                <CardContent className="h-24" />
              </Card>
              <Card className="animate-pulse">
                <CardContent className="h-24" />
              </Card>
              <Card className="animate-pulse">
                <CardContent className="h-24" />
              </Card>
            </>
          ) : (
            <>
              <StatCard
                title="Total Posts"
                value={stats.posts}
                icon={MessageSquare}
                change={0}
              />
              <StatCard
                title="Reputation Score"
                value={stats.reputation}
                icon={TrendingUp}
                change={0}
              />
              <StatCard
                title="Accuracy Rate"
                value={stats.accuracy}
                icon={Award}
                change={0}
              />
            </>
          )}
        </motion.div>

        {/* Achievements */}
        <motion.div variants={fadeInUp}>
          <Card className="glass-card border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5 text-primary" />
                Achievements
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {achievements.map((achievement) => (
                  <motion.div
                    key={achievement.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Card
                      className={cn(
                        "cursor-pointer transition-all",
                        achievement.unlocked
                          ? "border-primary/30 bg-gradient-to-br from-blue-500/5 to-slate-500/5 hover:shadow-lg"
                          : "opacity-50 grayscale"
                      )}
                    >
                      <CardContent className="p-4 text-center space-y-2">
                        <div className="text-4xl">{achievement.icon}</div>
                        <p className="text-sm font-medium">{achievement.name}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Recent Activity */}
        <motion.div variants={fadeInUp}>
          <Card className="glass-card border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingPosts ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : posts.length > 0 ? (
                <div className="space-y-4">
                  {posts.map((post) => (
                    <PostCard key={post.id} post={post} />
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
                  <p>Your recent posts and insights will appear here</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Username Edit Dialog */}
      <EditUsernameDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        currentUsername={userProfile?.username || user.email?.split('@')[0] || ''}
        onUpdate={handleUpdateProfile}
      />
    </DashboardShell>
  )
}
