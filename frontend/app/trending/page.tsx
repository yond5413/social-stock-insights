"use client"

import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, TrendingDown, Flame, Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import { GradientText } from "@/components/ui/gradient-text"
import { EnhancedSkeleton } from "@/components/ui/enhanced-skeleton"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { useApi } from "@/hooks/useApi"

interface TrendingTicker {
  ticker: string
  change_percent: number
  volume: number
  mentions?: number
}

export default function TrendingPage() {
  const { apiRequest } = useApi()
  const [tickers, setTickers] = useState<TrendingTicker[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isNetworkError, setIsNetworkError] = useState(false)
  const [timeframe, setTimeframe] = useState<"1H" | "1D" | "1W" | "1M">("1D")

  const fetchTrending = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      setIsNetworkError(false)
      const data = await apiRequest<TrendingTicker[]>("/market/trending")
      setTickers(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to fetch trending data"
      setIsNetworkError(errorMessage.includes("Backend server unavailable") || errorMessage.includes("Network error"))
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [apiRequest])

  useEffect(() => {
    fetchTrending()
  }, [fetchTrending])

  return (
    <DashboardShell>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="flex flex-col gap-6"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-red-500 shadow-lg shadow-orange-500/30">
              <Flame className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
                <GradientText>Trending Tickers</GradientText>
              </h1>
              <p className="text-muted-foreground">
                Most active stocks in the last 24 hours
              </p>
            </div>
          </div>
        </motion.div>

        {/* Timeframe Selector */}
        <motion.div variants={fadeInUp} className="flex gap-2 overflow-x-auto pb-2">
          {(["1H", "1D", "1W", "1M"] as const).map((tf) => (
            <Button
              key={tf}
              variant={timeframe === tf ? "default" : "outline"}
              size="sm"
              onClick={() => setTimeframe(tf)}
              className={cn(
                timeframe === tf && "bg-gradient-to-r from-violet-500 to-pink-500"
              )}
            >
              <Clock className="h-3.5 w-3.5 mr-1.5" />
              {tf}
            </Button>
          ))}
        </motion.div>

        {/* Error State */}
        {error && (
          <motion.div variants={fadeInUp}>
            <Card className={cn(
              "border-2 border-dashed",
              isNetworkError 
                ? "border-yellow-500/50 bg-yellow-500/5" 
                : "border-red-200 dark:border-red-900/30 bg-red-50 dark:bg-red-950/20"
            )}>
              <CardContent className="p-12 text-center">
                <div className="flex flex-col items-center gap-4">
                  <div className={cn(
                    "flex h-16 w-16 items-center justify-center rounded-2xl border",
                    isNetworkError
                      ? "bg-yellow-500/20 border-yellow-500/30"
                      : "bg-destructive/20 border-destructive/30"
                  )}>
                    <Flame className={cn(
                      "h-8 w-8",
                      isNetworkError ? "text-yellow-500" : "text-destructive"
                    )} />
                  </div>
                  <div>
                    <h3 className={cn(
                      "text-xl font-bold mb-2",
                      isNetworkError 
                        ? "text-yellow-600 dark:text-yellow-400" 
                        : "text-destructive"
                    )}>
                      {isNetworkError ? "Backend Server Not Running" : "Error Loading Trending Data"}
                    </h3>
                    <p className="text-muted-foreground max-w-md mb-4">
                      {isNetworkError 
                        ? "The API server is not available. Please start the backend server to view trending tickers."
                        : error}
                    </p>
                    {isNetworkError && (
                      <div className="bg-muted/50 rounded-lg p-4 text-left max-w-md mx-auto">
                        <p className="text-sm font-mono text-muted-foreground">
                          <span className="font-semibold">To start the backend:</span>
                          <br />
                          <code className="text-xs">cd backend</code>
                          <br />
                          <code className="text-xs">uvicorn app.main:app --reload --port 8000</code>
                        </p>
                      </div>
                    )}
                    {!isNetworkError && (
                      <Button 
                        onClick={fetchTrending}
                        variant="outline"
                        className="mt-2"
                      >
                        Retry
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="p-6">
                <div className="space-y-3">
                  <EnhancedSkeleton className="h-8 w-20" />
                  <EnhancedSkeleton className="h-24 w-full" />
                  <div className="flex gap-2">
                    <EnhancedSkeleton className="h-6 w-16" />
                    <EnhancedSkeleton className="h-6 w-16" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Tickers Grid */}
        {!loading && !error && (
          <motion.div
            variants={staggerContainer}
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
          >
            {tickers.map((ticker, index) => (
              <motion.div
                key={ticker.ticker}
                variants={fadeInUp}
                whileHover={{ y: -4, scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <Card className={cn(
                  "group cursor-pointer glass-card border-border/50 hover:border-primary/30 hover:shadow-lg transition-all duration-300",
                  index === 0 && "border-orange-500/50 glow"
                )}>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-2xl font-bold">${ticker.ticker}</h3>
                            {index === 0 && (
                              <Badge className="bg-gradient-to-r from-orange-500 to-red-500 text-white border-0">
                                <Flame className="h-3 w-3 mr-1" />
                                #1
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {ticker.volume.toLocaleString()} volume
                          </p>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <div className={cn(
                            "flex items-center gap-1 text-sm font-semibold",
                            ticker.change_percent >= 0
                              ? "text-green-600 dark:text-green-400"
                              : "text-red-600 dark:text-red-400"
                          )}>
                            {ticker.change_percent >= 0 ? (
                              <TrendingUp className="h-4 w-4" />
                            ) : (
                              <TrendingDown className="h-4 w-4" />
                            )}
                            {ticker.change_percent > 0 && "+"}
                            {ticker.change_percent.toFixed(2)}%
                          </div>
                        </div>
                      </div>

                      {/* Mini Chart Placeholder */}
                      <div className="h-20 rounded-lg bg-gradient-to-br from-violet-500/5 to-pink-500/5 border border-border/30 flex items-center justify-center">
                        <p className="text-xs text-muted-foreground">Chart preview</p>
                      </div>

                      {/* Footer */}
                      <div className="flex gap-2">
                        {ticker.mentions && (
                          <Badge variant="secondary" className="text-xs">
                            {ticker.mentions} mentions
                          </Badge>
                        )}
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "text-xs",
                            ticker.change_percent >= 0
                              ? "border-green-500/30 text-green-700 dark:text-green-400"
                              : "border-red-500/30 text-red-700 dark:text-red-400"
                          )}
                        >
                          {ticker.change_percent >= 0 ? "Bullish" : "Bearish"}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}
      </motion.div>
    </DashboardShell>
  )
}
