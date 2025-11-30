"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Clock,
  Users,
  Calendar,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Wifi,
  WifiOff,
  AlertCircle,
  Eye,
  Heart,
  MessageCircle,
} from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { StockDetailChart, StockDetailChartSkeleton } from "@/components/charts/stock-detail-chart"
import { PostCard } from "@/components/feed/post-card"
import { FeedItem } from "@/lib/types"
import { useTickerData } from "@/hooks/use-ticker-data"

// Period options for the chart
const PERIODS = [
  { label: "1D", value: "1D" },
  { label: "1W", value: "1W" },
  { label: "1M", value: "1M" },
  { label: "3M", value: "3M" },
] as const

type Period = typeof PERIODS[number]["value"]

interface MarketSnapshot {
  ticker: string
  price: number
  previous_close: number
  change: number
  change_percent: number
  volume: number
  market_cap: number | null
  fifty_two_week_high: number | null
  fifty_two_week_low: number | null
  currency: string
}

interface HistoryData {
  ticker: string
  period: string
  prices: Array<{
    date: string
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
  sentiment: Array<{
    date: string
    score: number
    bullish_count: number
    bearish_count: number
    neutral_count: number
    post_count: number
  }>
  overall_sentiment: string
  total_posts: number
  price_change_percent: number
}

interface PostsData {
  ticker: string
  posts: Array<FeedItem & {
    summary?: string
    explanation?: string
    sentiment?: string
    quality_score?: number
    insight_type?: string
    sector?: string
  }>
  total_count: number
  sentiment_summary: {
    bullish: number
    bearish: number
    neutral: number
  }
  has_more: boolean
}

export default function StockDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = (params.ticker as string)?.toUpperCase()

  const [period, setPeriod] = useState<Period>("1M")
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null)
  const [history, setHistory] = useState<HistoryData | null>(null)

  const [loadingSnapshot, setLoadingSnapshot] = useState(true)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

  // Use ticker data hook for posts and sentiment
  const {
    posts,
    totalPosts,
    sentimentSummary,
    sentiment: sentimentData,
    confidenceLevel,
    weightedSentiment,
    topThemes,
    isLoading: loadingPosts,
    wsConnected,
    hasNewPosts,
    refresh: refreshPosts,
  } = useTickerData(ticker)


  // Fetch market snapshot
  useEffect(() => {
    if (!ticker) return

    setLoadingSnapshot(true)
    fetch(`${apiBase}/market/snapshot/${ticker}`)
      .then(async res => {
        if (!res.ok) {
          // Try to parse error details from backend
          const errorData = await res.json().catch(() => ({}));
          throw new Error(errorData.detail || `Failed to fetch data (${res.status})`);
        }
        return res.json()
      })
      .then(data => {
        setSnapshot(data)
        setError(null)
      })
      .catch(err => {
        console.error("Error fetching snapshot:", err)
        setError(err.message)
      })
      .finally(() => setLoadingSnapshot(false))
  }, [ticker, apiBase])

  // Fetch price history when period changes
  useEffect(() => {
    if (!ticker) return

    setLoadingHistory(true)
    fetch(`${apiBase}/market/history/${ticker}?period=${period}`)
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error("Error fetching history:", err))
      .finally(() => setLoadingHistory(false))
  }, [ticker, period, apiBase])

  // Calculate sentiment totals
  const sentimentTotal = useMemo(() => {
    if (!sentimentSummary) return 0
    const { bullish, bearish, neutral } = sentimentSummary
    return bullish + bearish + neutral
  }, [sentimentSummary])

  if (error) {
    return (
      <div className="container max-w-7xl mx-auto px-4 py-8">
        <Button variant="ghost" onClick={() => router.back()} className="mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Card className="glass-card">
          <CardContent className="py-16 text-center">
            <h2 className="text-2xl font-bold mb-2">Unable to Load Market Data</h2>
            <p className="text-muted-foreground mb-4">
              {error === "Ticker not found" || error.includes("not found")
                ? `We couldn't find market data for "${ticker}". Please check the ticker symbol and try again.`
                : `There was an error loading data for "${ticker}": ${error}`
              }
            </p>
            <div className="flex justify-center gap-4">
              <Button variant="outline" onClick={() => window.location.reload()}>
                Try Again
              </Button>
              <Button onClick={() => router.push("/")}>
                Return Home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isUp = snapshot ? snapshot.change_percent >= 0 : true

  return (
    <div className="container max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
          </Button>

          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{ticker}</h1>
              {!loadingSnapshot && snapshot && (
                <Badge
                  variant="outline"
                  className={cn(
                    "text-sm font-semibold",
                    isUp
                      ? "bg-green-500/10 text-green-600 border-green-500/30"
                      : "bg-red-500/10 text-red-600 border-red-500/30"
                  )}
                >
                  {isUp ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                  {isUp ? "+" : ""}{snapshot.change_percent.toFixed(2)}%
                </Badge>
              )}
            </div>
            {snapshot && (
              <p className="text-muted-foreground text-sm">
                {snapshot.currency} • Real-time data
              </p>
            )}
          </div>
        </div>

        <Button variant="outline" size="sm" asChild>
          <a
            href={`https://finance.yahoo.com/quote/${ticker}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Yahoo Finance
            <ExternalLink className="h-3 w-3 ml-2" />
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Chart and Stats */}
        <div className="lg:col-span-2 space-y-6">
          {/* Price Card */}
          <Card className="glass-card border-border/50">
            <CardContent className="pt-6">
              {loadingSnapshot ? (
                <div className="space-y-2">
                  <Skeleton className="h-10 w-32" />
                  <Skeleton className="h-4 w-24" />
                </div>
              ) : snapshot && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div className="flex items-baseline gap-4">
                    <span className="text-4xl font-bold">
                      ${snapshot.price.toFixed(2)}
                    </span>
                    <span className={cn(
                      "text-lg font-semibold",
                      isUp ? "text-green-500" : "text-red-500"
                    )}>
                      {isUp ? "+" : ""}{snapshot.change.toFixed(2)} ({isUp ? "+" : ""}{snapshot.change_percent.toFixed(2)}%)
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Previous close: ${snapshot.previous_close.toFixed(2)}
                  </p>
                </motion.div>
              )}
            </CardContent>
          </Card>

          {/* Chart Card */}
          <Card className="glass-card border-border/50">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  Price History
                </CardTitle>

                {/* Period Selector */}
                <div className="flex rounded-lg border border-border overflow-hidden">
                  {PERIODS.map((p) => (
                    <Button
                      key={p.value}
                      variant="ghost"
                      size="sm"
                      className={cn(
                        "rounded-none px-3 h-8 text-xs font-medium",
                        period === p.value && "bg-primary/10 text-primary",
                        p.value !== "1D" && "border-l border-border"
                      )}
                      onClick={() => setPeriod(p.value)}
                    >
                      {p.label}
                    </Button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loadingHistory ? (
                <StockDetailChartSkeleton />
              ) : history && history.prices?.length > 0 ? (
                <StockDetailChart
                  prices={history.prices}
                  sentiment={history.sentiment || []}
                  ticker={ticker}
                />
              ) : (
                <div className="h-[350px] flex items-center justify-center text-muted-foreground">
                  No price data available for this period
                </div>
              )}
            </CardContent>
          </Card>

          {/* Key Stats */}
          <Card className="glass-card border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Key Statistics
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingSnapshot ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="space-y-2">
                      <Skeleton className="h-3 w-16" />
                      <Skeleton className="h-5 w-20" />
                    </div>
                  ))}
                </div>
              ) : snapshot && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">Volume</p>
                    <p className="text-lg font-semibold">
                      {snapshot.volume ? (snapshot.volume / 1000000).toFixed(2) + "M" : "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">Market Cap</p>
                    <p className="text-lg font-semibold">
                      {snapshot.market_cap
                        ? (snapshot.market_cap / 1000000000).toFixed(2) + "B"
                        : "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">52W High</p>
                    <p className="text-lg font-semibold text-green-500">
                      {snapshot.fifty_two_week_high
                        ? "$" + snapshot.fifty_two_week_high.toFixed(2)
                        : "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">52W Low</p>
                    <p className="text-lg font-semibold text-red-500">
                      {snapshot.fifty_two_week_low
                        ? "$" + snapshot.fifty_two_week_low.toFixed(2)
                        : "N/A"}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - Sentiment and Posts */}
        <div className="space-y-6">
          {/* Community Sentiment */}
          <Card className="glass-card border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  Community Sentiment
                </CardTitle>
                {wsConnected && (
                  <Badge variant="outline" className="text-xs gap-1">
                    <Wifi className="h-3 w-3" />
                    Live
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loadingPosts ? (
                <div className="space-y-4">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                </div>
              ) : totalPosts > 0 ? (
                <div className="space-y-4">
                  {/* Confidence Badge */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-xs",
                        confidenceLevel === "high" && "bg-green-500/10 text-green-600 border-green-500/30",
                        confidenceLevel === "medium" && "bg-yellow-500/10 text-yellow-600 border-yellow-500/30",
                        confidenceLevel === "low" && "bg-orange-500/10 text-orange-600 border-orange-500/30",
                        confidenceLevel === "pending" && "bg-gray-500/10 text-gray-600 border-gray-500/30"
                      )}
                    >
                      {confidenceLevel === "high" && "High Confidence"}
                      {confidenceLevel === "medium" && "Medium Confidence"}
                      {confidenceLevel === "low" && "Low Confidence"}
                      {confidenceLevel === "pending" && "Calculating..."}
                    </Badge>
                    {sentimentData && (
                      <span className="text-xs text-muted-foreground">
                        {sentimentData.processed_posts} analyzed
                      </span>
                    )}
                  </div>

                  {/* Sentiment Bars - Use weighted sentiment for display */}
                  {sentimentTotal > 0 && (
                    <div className="space-y-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-green-600 font-medium">Bullish</span>
                          <span className="text-muted-foreground">
                            {sentimentSummary.bullish} ({weightedSentiment.bullish.toFixed(0)}%)
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-gradient-to-r from-green-500 to-green-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${weightedSentiment.bullish}%` }}
                            transition={{ duration: 0.5 }}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-red-600 font-medium">Bearish</span>
                          <span className="text-muted-foreground">
                            {sentimentSummary.bearish} ({weightedSentiment.bearish.toFixed(0)}%)
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-gradient-to-r from-red-500 to-red-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${weightedSentiment.bearish}%` }}
                            transition={{ duration: 0.5, delay: 0.1 }}
                          />
                        </div>
                      </div>

                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600 font-medium">Neutral</span>
                          <span className="text-muted-foreground">
                            {sentimentSummary.neutral} ({weightedSentiment.neutral.toFixed(0)}%)
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-gradient-to-r from-gray-500 to-gray-400"
                            initial={{ width: 0 }}
                            animate={{ width: `${weightedSentiment.neutral}%` }}
                            transition={{ duration: 0.5, delay: 0.2 }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="pt-2 border-t border-border space-y-2">
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      Based on {totalPosts} community {totalPosts === 1 ? 'post' : 'posts'}
                      {sentimentData && sentimentData.avg_engagement > 0 && (
                        <span className="text-xs">
                          • Avg engagement: {sentimentData.avg_engagement.toFixed(0)}
                        </span>
                      )}
                    </p>
                    {confidenceLevel === "low" && totalPosts < 3 && (
                      <p className="text-xs text-orange-600 flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        Limited data - more posts needed for accurate sentiment
                      </p>
                    )}
                    {confidenceLevel === "pending" && (
                      <p className="text-xs text-gray-600">
                        Posts are being processed...
                      </p>
                    )}
                  </div>

                  {/* Top Themes */}
                  {topThemes.length > 0 && (
                    <div className="pt-2 border-t border-border">
                      <p className="text-xs font-medium mb-2">Key Themes:</p>
                      <div className="flex flex-wrap gap-1">
                        {topThemes.map((theme, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            {theme}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No community posts yet for {ticker}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Period Sentiment from History */}
          {history && history.overall_sentiment && (
            <Card className="glass-card border-border/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">{period} Sentiment</span>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      history.overall_sentiment === "bullish" && "bg-green-500/10 text-green-600 border-green-500/30",
                      history.overall_sentiment === "bearish" && "bg-red-500/10 text-red-600 border-red-500/30",
                      history.overall_sentiment === "neutral" && "bg-gray-500/10 text-gray-600 border-gray-500/30"
                    )}
                  >
                    {history.overall_sentiment}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Recent Posts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Recent Posts about {ticker}
          </h2>
          <div className="flex items-center gap-2">
            {totalPosts > 0 && (
              <Badge variant="secondary">
                {totalPosts} {totalPosts === 1 ? 'post' : 'posts'}
              </Badge>
            )}
            {wsConnected && (
              <Badge variant="outline" className="text-xs gap-1">
                <Wifi className="h-3 w-3 text-green-500" />
                Live
              </Badge>
            )}
          </div>
        </div>

        {/* New Posts Banner */}
        <AnimatePresence>
          {hasNewPosts && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <Card className="bg-primary/10 border-primary/30">
                <CardContent className="py-3 px-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span>New posts are available for {ticker}</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={refreshPosts}>
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Refresh
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {loadingPosts ? (
          <div className="grid gap-4">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="glass-card">
                <CardContent className="p-6">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-10 w-10 rounded-full" />
                      <div className="space-y-2">
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-3 w-16" />
                      </div>
                    </div>
                    <Skeleton className="h-16 w-full" />
                    <div className="flex gap-2">
                      <Skeleton className="h-6 w-16" />
                      <Skeleton className="h-6 w-16" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : posts.length > 0 ? (
          <div className="grid gap-4">
            {posts.map((post) => (
              <PostCard
                key={post.id}
                post={{
                  id: post.id,
                  user_id: post.user_id,
                  content: post.content,
                  tickers: post.tickers,
                  llm_status: post.llm_status,
                  created_at: post.created_at,
                  view_count: post.view_count,
                  like_count: post.like_count,
                  comment_count: post.comment_count,
                  engagement_score: post.engagement_score,
                  summary: post.summary,
                  sentiment: post.sentiment,
                  final_score: post.quality_score || 0.5,
                  quality_score: post.quality_score,
                  is_processing: post.is_processing,
                }}
              />
            ))}

            {/* Show processing posts indicator if any */}
            {posts.some(p => p.is_processing) && (
              <Card className="glass-card border-dashed">
                <CardContent className="py-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Some posts are still being processed...</span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        ) : (
          <Card className="glass-card">
            <CardContent className="py-12 text-center">
              <Sparkles className="h-12 w-12 text-muted-foreground/50 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No posts yet</h3>
              <p className="text-muted-foreground mb-4">
                Be the first to share insights about {ticker}!
              </p>
              <Button onClick={() => router.push("/")}>
                Create a Post
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

