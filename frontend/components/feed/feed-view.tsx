"use client"

import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { PostCard } from "@/components/feed/post-card"
import { CreatePostDialog } from "@/components/feed/create-post-dialog"
import { useFeed } from "@/hooks/use-feed"
import { useAuth } from "@/contexts/AuthContext"
import { FeedSkeleton } from "@/components/ui/enhanced-skeleton"
import { Button } from "@/components/ui/button"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { Sparkles, TrendingUp, Users } from "lucide-react"
import { GradientText } from "@/components/ui/gradient-text"

export function FeedView() {
  const { user, loading: authLoading } = useAuth()
  const { feed, isLoading: feedLoading, isError, isNetworkError, errorMessage, mutate, filter, setFilter } = useFeed()

  if (authLoading) {
    return (
      <DashboardShell>
        <div className="space-y-4">
          <FeedSkeleton />
        </div>
      </DashboardShell>
    )
  }

  return (
    <DashboardShell>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="flex flex-col space-y-6"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              <GradientText>Your Feed</GradientText>
            </h1>
            <p className="text-muted-foreground mt-1">
              AI-powered insights from the market's top voices
            </p>
          </div>
          {user && (
            <CreatePostDialog onPostCreated={() => mutate()} />
          )}
        </motion.div>

        {/* Filter Pills */}
        {user && (
          <motion.div variants={fadeInUp} className="flex gap-2 overflow-x-auto pb-2">
            <Button 
              variant={filter === "all" ? "default" : "outline"} 
              size="sm" 
              onClick={() => setFilter("all")}
              className={filter === "all" ? "bg-gradient-to-r from-blue-500 to-slate-500 hover:from-blue-600 hover:to-slate-600" : "hover:bg-muted/50"}
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              All
            </Button>
            <Button 
              variant={filter === "following" ? "default" : "outline"} 
              size="sm" 
              onClick={() => setFilter("following")}
              className={filter === "following" ? "bg-gradient-to-r from-blue-500 to-slate-500" : "hover:bg-muted/50"}
            >
              <Users className="h-3.5 w-3.5 mr-1.5" />
              Following
            </Button>
            <Button 
              variant={filter === "trending" ? "default" : "outline"} 
              size="sm" 
              onClick={() => setFilter("trending")}
              className={filter === "trending" ? "bg-gradient-to-r from-blue-500 to-slate-500" : "hover:bg-muted/50"}
            >
              <TrendingUp className="h-3.5 w-3.5 mr-1.5" />
              Trending
            </Button>
          </motion.div>
        )}

        {/* Feed Content */}
        <div className="space-y-6">
          {!user ? (
            <motion.div variants={fadeInUp}>
              <div className="rounded-xl border-2 border-dashed border-border p-12 text-center glass-card">
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-slate-500 shadow-lg shadow-blue-500/30">
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold mb-2">
                      <GradientText>Welcome to Stock Insights</GradientText>
                    </h3>
                    <p className="text-muted-foreground max-w-md">
                      Sign in to view your personalized feed of AI-powered stock insights and market analysis.
                    </p>
                  </div>
                  <Button size="lg" className="mt-2 bg-gradient-to-r from-blue-500 to-slate-500 hover:from-blue-600 hover:to-slate-600">
                    Get Started
                  </Button>
                </div>
              </div>
            </motion.div>
          ) : feedLoading ? (
            <FeedSkeleton />
          ) : isNetworkError ? (
            <motion.div variants={fadeInUp}>
              <div className="rounded-xl border-2 border-dashed border-yellow-500/50 bg-yellow-500/5 p-12 text-center glass-card">
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-yellow-500/20 border border-yellow-500/30">
                    <Sparkles className="h-8 w-8 text-yellow-500" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold mb-2 text-yellow-600 dark:text-yellow-400">
                      Backend Server Not Running
                    </h3>
                    <p className="text-muted-foreground max-w-md mb-4">
                      The API server is not available. Please start the backend server to view your feed.
                    </p>
                    <div className="bg-muted/50 rounded-lg p-4 text-left max-w-md">
                      <p className="text-sm font-mono text-muted-foreground">
                        <span className="font-semibold">To start the backend:</span>
                        <br />
                        <code className="text-xs">cd backend</code>
                        <br />
                        <code className="text-xs">uvicorn app.main:app --reload --port 8000</code>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ) : isError ? (
            <motion.div variants={fadeInUp}>
              <div className="rounded-xl border-2 border-dashed border-destructive/50 bg-destructive/5 p-12 text-center glass-card">
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/20 border border-destructive/30">
                    <Sparkles className="h-8 w-8 text-destructive" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold mb-2 text-destructive">
                      Error Loading Feed
                    </h3>
                    <p className="text-muted-foreground max-w-md">
                      {errorMessage || 'Unable to load your feed. Please try again later.'}
                    </p>
                  </div>
                  <Button 
                    onClick={() => mutate()} 
                    variant="outline"
                    className="mt-2"
                  >
                    Retry
                  </Button>
                </div>
              </div>
            </motion.div>
          ) : feed.length === 0 ? (
            <motion.div variants={fadeInUp}>
              <div className="rounded-xl border-2 border-dashed border-border p-12 text-center glass-card">
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-slate-500 shadow-lg shadow-blue-500/30 opacity-50">
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold mb-2">No insights yet</h3>
                    <p className="text-muted-foreground max-w-md">
                      Be the first to share your market analysis and help the community make better investment decisions!
                    </p>
                  </div>
                  <div className="mt-2">
                    <CreatePostDialog onPostCreated={() => mutate()} />
                  </div>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div variants={staggerContainer} className="space-y-6">
              {feed.map((post) => (
                <motion.div key={post.id} variants={fadeInUp}>
                  <PostCard post={post} />
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>

        {/* Load More (placeholder for future) */}
        {feed.length > 0 && user && (
          <motion.div variants={fadeInUp} className="flex justify-center pt-4">
            <Button variant="outline" size="lg" className="hover:bg-muted/50">
              Load More Insights
            </Button>
          </motion.div>
        )}
      </motion.div>
    </DashboardShell>
  )
}
