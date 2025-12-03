"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { PostCard } from "@/components/feed/post-card"
import { useAuth } from "@/contexts/AuthContext"
import { FeedSkeleton } from "@/components/ui/enhanced-skeleton"
import { Button } from "@/components/ui/button"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { Bookmark, Sparkles } from "lucide-react"
import { GradientText } from "@/components/ui/gradient-text"
import { useApi } from "@/hooks/useApi"
import { FeedItem } from "@/lib/types"
import Link from "next/link"

export default function BookmarksPage() {
  const { user, loading: authLoading } = useAuth()
  const { apiRequest } = useApi()
  const [bookmarks, setBookmarks] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchBookmarks = async () => {
      if (!user) return
      try {
        setLoading(true)
        const data = await apiRequest<FeedItem[]>("/posts/bookmarks")
        setBookmarks(data)
      } catch (err) {
        console.error("Failed to fetch bookmarks:", err)
        setError("Failed to load bookmarks")
      } finally {
        setLoading(false)
      }
    }

    if (user) {
      fetchBookmarks()
    }
  }, [user, apiRequest])

  if (authLoading) {
    return (
      <DashboardShell>
        <div className="space-y-4">
          <FeedSkeleton />
        </div>
      </DashboardShell>
    )
  }

  if (!user) {
    return (
      <DashboardShell>
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
          <h1 className="text-2xl font-bold mb-2">Sign in to view bookmarks</h1>
          <p className="text-muted-foreground mb-4">You need to be logged in to save and view bookmarks.</p>
          <Link href="/login">
            <Button>Sign In</Button>
          </Link>
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
              <GradientText>Bookmarks</GradientText>
            </h1>
            <p className="text-muted-foreground mt-1">
              Your saved insights and analysis
            </p>
          </div>
        </motion.div>

        {/* Content */}
        <div className="space-y-6">
          {loading ? (
            <FeedSkeleton />
          ) : error ? (
            <div className="text-center p-8 text-destructive">
              <p>{error}</p>
              <Button variant="outline" onClick={() => window.location.reload()} className="mt-4">
                Retry
              </Button>
            </div>
          ) : bookmarks.length === 0 ? (
            <motion.div variants={fadeInUp}>
              <div className="rounded-xl border-2 border-dashed border-border p-12 text-center glass-card">
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border border-yellow-500/30">
                    <Bookmark className="h-8 w-8 text-yellow-500" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold mb-2">No bookmarks yet</h3>
                    <p className="text-muted-foreground max-w-md">
                      Save interesting insights to read later by clicking the bookmark icon on any post.
                    </p>
                  </div>
                  <Link href="/">
                    <Button className="mt-2" variant="outline">
                      Browse Feed
                    </Button>
                  </Link>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div variants={staggerContainer} className="space-y-6">
              {bookmarks.map((post) => (
                <motion.div key={post.id} variants={fadeInUp}>
                  <PostCard post={post} />
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </motion.div>
    </DashboardShell>
  )
}
