"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { useAuth } from "@/contexts/AuthContext"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StatCard } from "@/components/ui/stat-card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { MessageSquare, TrendingUp, Award, Star, Sparkles, Loader2, Share2, Users } from "lucide-react"
import { cn } from "@/lib/utils"
import { apiRequest } from "@/lib/api"
import { FeedItem } from "@/lib/types"
import { PostCard } from "@/components/feed/post-card"
import { FollowButton } from "@/components/users/follow-button"

interface UserProfile {
  id: string
  username: string
  email?: string
  created_at: string
}

interface UserStats {
    followers_count: number
    following_count: number
    is_following: boolean
    reputation: number
}

export default function UserProfilePage() {
  const params = useParams()
  const userId = params.userId as string
  const { user: currentUser } = useAuth()
  
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [stats, setStats] = useState<UserStats>({
    followers_count: 0,
    following_count: 0,
    is_following: false,
    reputation: 0
  })
  const [posts, setPosts] = useState<FeedItem[]>([])
  const [followers, setFollowers] = useState<any[]>([])
  const [following, setFollowing] = useState<any[]>([])
  
  const [loading, setLoading] = useState(true)
  const [loadingPosts, setLoadingPosts] = useState(true)

  const isOwnProfile = currentUser?.id === userId

  useEffect(() => {
    const fetchData = async () => {
      if (!userId) return
      try {
        const [profileData, statsData] = await Promise.all([
            apiRequest<UserProfile>(`/users/${userId}`),
            apiRequest<UserStats>(`/users/${userId}/stats`)
        ])
        setProfile(profileData)
        setStats(statsData)
      } catch (error) {
        console.error("Failed to fetch user data:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [userId])

  useEffect(() => {
    const fetchPosts = async () => {
      if (!userId) return
      try {
        const data = await apiRequest<FeedItem[]>(`/posts/user/${userId}?limit=10`)
        setPosts(data)
      } catch (error) {
        console.error("Failed to fetch user posts:", error)
      } finally {
        setLoadingPosts(false)
      }
    }

    fetchPosts()
  }, [userId])

  useEffect(() => {
      if (!userId) return
      const fetchSocials = async () => {
          try {
              const [followersData, followingData] = await Promise.all([
                  apiRequest<any[]>(`/users/${userId}/followers`),
                  apiRequest<any[]>(`/users/${userId}/following`)
              ])
              setFollowers(followersData || [])
              setFollowing(followingData || [])
          } catch (e) {
              console.error("Error fetching social connections", e)
          }
      }
      fetchSocials()
  }, [userId])

  if (loading) {
    return (
      <DashboardShell>
        <div className="flex h-[50vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardShell>
    )
  }

  if (!profile) {
    return (
      <DashboardShell>
        <div className="flex flex-col gap-4 p-4">
          <h1 className="text-2xl font-bold">User Not Found</h1>
          <p>The user you are looking for does not exist.</p>
        </div>
      </DashboardShell>
    )
  }

  const achievements = [
    { id: 1, name: "First Post", icon: "🎯", unlocked: posts.length > 0 },
    { id: 2, name: "10 Posts", icon: "🔥", unlocked: posts.length >= 10 },
    { id: 3, name: "Top Contributor", icon: "⭐", unlocked: stats.reputation > 0.8 },
    { id: 4, name: "Expert Analyst", icon: "🏆", unlocked: stats.reputation > 0.9 },
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
          {/* Cover Photo */}
          <div className="h-32 md:h-48 rounded-xl bg-gradient-to-br from-blue-500 via-slate-500 to-blue-700 relative overflow-hidden">
            <div className="absolute inset-0 bg-grid opacity-10"></div>
          </div>

          {/* Avatar & Basic Info */}
          <div className="relative px-4 md:px-6 pb-6">
            <div className="flex flex-col md:flex-row gap-4 md:gap-6 -mt-12 md:-mt-16">
              {/* Avatar */}
              <div className="relative">
                <div className="p-1 rounded-2xl bg-gradient-to-br from-blue-500 to-slate-500">
                  <Avatar className="h-24 w-24 md:h-32 md:w-32 border-4 border-background">
                    <AvatarImage src={`https://avatar.vercel.sh/${profile.id}`} />
                    <AvatarFallback className="text-2xl md:text-4xl font-bold bg-gradient-to-br from-blue-500 to-slate-500 text-white">
                      {profile.username.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 flex flex-col justify-end space-y-2">
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl md:text-3xl font-bold">
                    {profile.username}
                  </h1>
                  <Badge className="bg-gradient-to-r from-blue-500 to-slate-500 text-white border-0">
                    <Sparkles className="h-3 w-3 mr-1" />
                    Analyst
                  </Badge>
                </div>
                <p className="text-muted-foreground">Joined {new Date(profile.created_at).toLocaleDateString()}</p>
                
                <div className="flex gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                        <span className="font-bold text-foreground">{stats.followers_count}</span> Followers
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="font-bold text-foreground">{stats.following_count}</span> Following
                    </div>
                </div>

                <div className="flex gap-2 mt-2">
                  {!isOwnProfile && currentUser && (
                    <FollowButton 
                        userId={profile.id} 
                        initialIsFollowing={stats.is_following}
                        onFollowChange={(isFollowing) => {
                            setStats(prev => ({
                                ...prev,
                                is_following: isFollowing,
                                followers_count: prev.followers_count + (isFollowing ? 1 : -1)
                            }))
                        }}
                    />
                  )}
                  <Button size="sm" variant="outline">
                    <Share2 className="h-4 w-4 mr-2" />
                    Share Profile
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Stats Grid */}
        <motion.div variants={fadeInUp} className="grid gap-4 md:grid-cols-3">
          <StatCard
            title="Total Posts"
            value={posts.length} 
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
            title="Followers"
            value={stats.followers_count}
            icon={Users}
            change={0}
          />
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

        {/* Tabs for Activity/Followers/Following */}
        <motion.div variants={fadeInUp}>
            <Tabs defaultValue="activity" className="w-full">
                <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
                    <TabsTrigger value="activity">Activity</TabsTrigger>
                    <TabsTrigger value="followers">Followers</TabsTrigger>
                    <TabsTrigger value="following">Following</TabsTrigger>
                </TabsList>
                
                <TabsContent value="activity" className="mt-6">
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
                          <p>This user hasn't posted anything yet.</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
                
                <TabsContent value="followers" className="mt-6">
                    <Card className="glass-card border-border/50">
                        <CardContent className="p-6">
                            {followers.length > 0 ? (
                                <div className="grid gap-4 md:grid-cols-2">
                                    {followers.map((f: any) => (
                                        <div key={f.follower_id} className="flex items-center justify-between p-3 rounded-lg border bg-card/50">
                                            <div className="flex items-center gap-3">
                                                <Avatar>
                                                    <AvatarImage src={`https://avatar.vercel.sh/${f.follower_id}`} />
                                                    <AvatarFallback>{f.username?.charAt(0).toUpperCase() || 'U'}</AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <p className="font-medium">{f.username}</p>
                                                </div>
                                            </div>
                                            {currentUser?.id !== f.follower_id && (
                                                <FollowButton userId={f.follower_id} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-center text-muted-foreground py-8">No followers yet.</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
                
                <TabsContent value="following" className="mt-6">
                    <Card className="glass-card border-border/50">
                        <CardContent className="p-6">
                            {following.length > 0 ? (
                                <div className="grid gap-4 md:grid-cols-2">
                                    {following.map((f: any) => (
                                        <div key={f.following_id} className="flex items-center justify-between p-3 rounded-lg border bg-card/50">
                                            <div className="flex items-center gap-3">
                                                <Avatar>
                                                    <AvatarImage src={`https://avatar.vercel.sh/${f.following_id}`} />
                                                    <AvatarFallback>{f.username?.charAt(0).toUpperCase() || 'U'}</AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <p className="font-medium">{f.username}</p>
                                                </div>
                                            </div>
                                            {currentUser?.id !== f.following_id && (
                                                <FollowButton userId={f.following_id} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-center text-muted-foreground py-8">Not following anyone yet.</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </motion.div>
      </motion.div>
    </DashboardShell>
  )
}
