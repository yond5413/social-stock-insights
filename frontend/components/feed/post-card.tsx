"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import {
  MessageSquare,
  Heart,
  Share2,
  MoreHorizontal,
  Sparkles,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  Eye,
  RefreshCw,
  Zap,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { FeedItem } from "@/lib/types"
import { TickerChart } from "./ticker-chart"
import { useApi } from "@/hooks/useApi"
import { useAuth } from "@/contexts/AuthContext"
import { CommentsDialog } from "./comments-dialog"

interface PostCardProps {
  post: FeedItem
}

export function PostCard({ post }: PostCardProps) {
  const [showInsight, setShowInsight] = useState(false)
  const [isLiked, setIsLiked] = useState(post.user_has_liked || false)
  const hasViewed = useRef(false)

  const qualityScore = post.quality_score || 0
  const qualityPercent = qualityScore * 100

  // Get engagement metrics with defaults
  const viewCount = post.view_count || 0
  const likeCount = post.like_count || 0
  const commentCount = post.comment_count || 0
  const engagementScore = post.engagement_score || 0
  const isProcessing = post.is_processing || false

  // Determine if this is a high-engagement post
  const isHighEngagement = engagementScore > 100

  const [likeCountState, setLikeCountState] = useState(likeCount)
  const [commentCountState, setCommentCountState] = useState(commentCount)
  const { apiRequest } = useApi()
  const { user } = useAuth()

  // Increment view count on mount
  useEffect(() => {
    if (hasViewed.current) return

    const incrementView = async () => {
      try {
        await apiRequest(`/posts/${post.id}/view`, { method: "POST" })
        hasViewed.current = true
      } catch (error) {
        console.error("Failed to increment view count:", error)
      }
    }

    // Small delay to ensure it's actually seen (optional, but good practice)
    const timer = setTimeout(incrementView, 1000)
    return () => clearTimeout(timer)
  }, [post.id, apiRequest])

  // Sync isLiked state when post data changes (e.g. after refresh)
  useEffect(() => {
    setIsLiked(post.user_has_liked || false)
    setLikeCountState(post.like_count || 0)
    setCommentCountState(post.comment_count || 0)
  }, [post.user_has_liked, post.like_count, post.comment_count])

  const handleLike = async () => {
    if (!user) return // Or show auth dialog

    // Optimistic update
    const newIsLiked = !isLiked
    setIsLiked(newIsLiked)
    setLikeCountState(prev => newIsLiked ? prev + 1 : prev - 1)

    try {
      await apiRequest(`/posts/${post.id}/like`, { method: "POST" })
    } catch (error) {
      // Revert on error
      setIsLiked(!newIsLiked)
      setLikeCountState(prev => !newIsLiked ? prev + 1 : prev - 1)
      console.error("Failed to toggle like:", error)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
    >
      <Card className="overflow-hidden border-border/50 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 glass-card">
        <CardHeader className="flex flex-row items-start justify-between space-y-0 p-4 md:p-6">
          <div className="flex items-center space-x-3">
            {/* Avatar with gradient ring for high-quality posts */}
            <Link href={`/profile/${post.user_id}`}>
              <div className={cn(
                "rounded-full p-[2px] transition-transform hover:scale-105",
                qualityScore > 0.7 && "bg-gradient-to-br from-blue-500 to-slate-500"
              )}>
                <Avatar className="h-10 w-10 md:h-12 md:w-12 border-2 border-background">
                  <AvatarImage src={`https://avatar.vercel.sh/${post.user_id}`} />
                  <AvatarFallback className="bg-gradient-to-br from-blue-500 to-slate-500 text-white font-semibold">
                    {(post.username || post.user_id).slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </div>
            </Link>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Link href={`/profile/${post.user_id}`}>
                  <p className="text-sm font-semibold leading-none hover:text-primary transition-colors">
                    {post.username || `User ${post.user_id.slice(0, 8)}`}
                  </p>
                </Link>
                {qualityScore > 0.8 && (
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-gradient-to-r from-blue-500/10 to-slate-500/10 text-primary border-primary/20">
                    <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                    Top
                  </Badge>
                )}
                {isProcessing && (
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-blue-500/10 text-blue-600 border-blue-500/30">
                    <RefreshCw className="h-2.5 w-2.5 mr-0.5 animate-spin" />
                    Processing
                  </Badge>
                )}
                {isHighEngagement && !isProcessing && (
                  <motion.div
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-amber-500/10 text-amber-600 border-amber-500/30">
                      <Zap className="h-2.5 w-2.5 mr-0.5" />
                      Hot
                    </Badge>
                  </motion.div>
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>
                  {new Date(post.created_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
                {!isProcessing && (
                  <>
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {viewCount}
                    </span>
                    {likeCountState > 0 && (
                      <span className="flex items-center gap-1">
                        <Heart className="h-3 w-3" />
                        {likeCountState}
                      </span>
                    )}
                    {commentCountState > 0 && (
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {commentCountState}
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="-mr-2 h-8 w-8 hover:bg-muted/50">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="px-4 md:px-6 pb-4">
          {/* Post Content */}
          <div className="mb-4 space-y-3">
            <p className="text-base leading-relaxed">
              {post.content}
            </p>

            {/* Tickers */}
            {post.tickers && post.tickers.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {post.tickers.map((ticker) => (
                  <motion.div
                    key={ticker}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Link href={`/stock/${ticker}`}>
                      <Badge
                        variant="outline"
                        className="gap-2 px-3 py-1.5 text-sm font-semibold bg-gradient-to-r from-blue-500/5 to-slate-500/5 border-border/50 hover:border-primary/30 hover:shadow-sm transition-all cursor-pointer"
                      >
                        <TrendingUp className="h-3 w-3 text-primary" />
                        <span>{ticker}</span>
                        <TickerChart ticker={ticker} />
                      </Badge>
                    </Link>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* AI Insight Section */}
          {post.summary && (
            <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-blue-500/5 via-slate-500/5 to-cyan-500/5 p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-slate-500">
                    <Sparkles className="h-3.5 w-3.5 text-white" />
                  </div>
                  <span className="text-sm font-semibold bg-gradient-to-r from-blue-600 to-slate-600 bg-clip-text text-transparent">
                    AI Insight
                  </span>
                  {qualityPercent > 0 && (
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-blue-500 to-slate-500"
                          initial={{ width: 0 }}
                          animate={{ width: `${qualityPercent}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                        />
                      </div>
                      <span className="text-[10px] font-medium text-muted-foreground">
                        {qualityPercent.toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs hover:bg-primary/10"
                  onClick={() => setShowInsight(!showInsight)}
                >
                  {showInsight ? (
                    <>
                      Hide <ChevronUp className="ml-1 h-3 w-3" />
                    </>
                  ) : (
                    <>
                      Explain <ChevronDown className="ml-1 h-3 w-3" />
                    </>
                  )}
                </Button>
              </div>

              <AnimatePresence>
                {showInsight && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-3 space-y-3 text-sm">
                      <div>
                        <p className="font-medium text-foreground mb-1">Summary</p>
                        <p className="text-muted-foreground leading-relaxed">{post.summary}</p>
                      </div>
                      <div className="flex gap-4 pt-2">
                        <div className="flex flex-col gap-1">
                          <span className="text-xs font-medium text-muted-foreground">Rank Score</span>
                          <span className="text-base font-semibold">{post.final_score.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-xs font-medium text-muted-foreground">Status</span>
                          <Badge variant="outline" className="capitalize w-fit">
                            {post.llm_status}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </CardContent>

        <Separator className="opacity-50" />

        <CardFooter className="p-2 md:p-3">
          <div className="flex w-full items-center justify-between text-muted-foreground">
            <motion.div whileTap={{ scale: 0.95 }} className="flex-1">
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  "flex-1 gap-2 hover:text-blue-600 hover:bg-blue-500/10 transition-colors",
                  isLiked && "text-blue-600"
                )}
                onClick={handleLike}
              >
                <motion.div
                  animate={isLiked ? { scale: [1, 1.2, 1] } : {}}
                  transition={{ duration: 0.3 }}
                >
                  <Heart className={cn("h-4 w-4", isLiked && "fill-current")} />
                </motion.div>
                <span className="text-xs font-medium">
                  {likeCountState > 0 ? likeCountState : "Like"}
                </span>
              </Button>
            </motion.div>
            <motion.div whileTap={{ scale: 0.95 }} className="flex-1">
              <CommentsDialog
                postId={post.id}
                commentCount={commentCountState}
                onCommentAdded={() => setCommentCountState(prev => prev + 1)}
              />
            </motion.div>
            <motion.div whileTap={{ scale: 0.95 }} className="flex-1">
              <Button variant="ghost" size="sm" className="flex-1 gap-2 hover:text-green-600 hover:bg-green-500/10 transition-colors">
                <Share2 className="h-4 w-4" />
                <span className="text-xs font-medium">Share</span>
              </Button>
            </motion.div>
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  )
}
