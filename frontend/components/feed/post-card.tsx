"use client"

import { useState } from "react"
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

interface PostCardProps {
  post: FeedItem
}

export function PostCard({ post }: PostCardProps) {
  const [showInsight, setShowInsight] = useState(false)
  const [isLiked, setIsLiked] = useState(false)

  const qualityScore = post.quality_score || 0
  const qualityPercent = qualityScore * 100

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
            <div className={cn(
              "rounded-full p-[2px]",
              qualityScore > 0.7 && "bg-gradient-to-br from-violet-500 to-pink-500"
            )}>
              <Avatar className="h-10 w-10 md:h-12 md:w-12 border-2 border-background">
                <AvatarImage src={`https://avatar.vercel.sh/${post.user_id}`} />
                <AvatarFallback className="bg-gradient-to-br from-violet-500 to-pink-500 text-white font-semibold">
                  {post.user_id.slice(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold leading-none">
                  User {post.user_id.slice(0, 8)}
                </p>
                {qualityScore > 0.8 && (
                  <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-gradient-to-r from-violet-500/10 to-pink-500/10 text-primary border-primary/20">
                    <Sparkles className="h-2.5 w-2.5 mr-0.5" />
                    Top
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {new Date(post.created_at).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </p>
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
                    <Badge 
                      variant="outline"
                      className="gap-2 px-3 py-1.5 text-sm font-semibold bg-gradient-to-r from-violet-500/5 to-pink-500/5 border-border/50 hover:border-primary/30 hover:shadow-sm transition-all cursor-pointer"
                    >
                      <TrendingUp className="h-3 w-3 text-primary" />
                      <span>{ticker}</span>
                      <TickerChart ticker={ticker} />
                    </Badge>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* AI Insight Section */}
          {post.summary && (
            <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-violet-500/5 via-pink-500/5 to-blue-500/5 p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-violet-500 to-pink-500">
                    <Sparkles className="h-3.5 w-3.5 text-white" />
                  </div>
                  <span className="text-sm font-semibold bg-gradient-to-r from-violet-600 to-pink-600 bg-clip-text text-transparent">
                    AI Insight
                  </span>
                  {qualityPercent > 0 && (
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-violet-500 to-pink-500"
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
                  "flex-1 gap-2 hover:text-pink-600 hover:bg-pink-500/10 transition-colors",
                  isLiked && "text-pink-600"
                )}
                onClick={() => setIsLiked(!isLiked)}
              >
                <motion.div
                  animate={isLiked ? { scale: [1, 1.2, 1] } : {}}
                  transition={{ duration: 0.3 }}
                >
                  <Heart className={cn("h-4 w-4", isLiked && "fill-current")} />
                </motion.div>
                <span className="text-xs font-medium">Like</span>
              </Button>
            </motion.div>
            <motion.div whileTap={{ scale: 0.95 }} className="flex-1">
              <Button variant="ghost" size="sm" className="flex-1 gap-2 hover:text-blue-600 hover:bg-blue-500/10 transition-colors">
                <MessageSquare className="h-4 w-4" />
                <span className="text-xs font-medium">Comment</span>
              </Button>
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
