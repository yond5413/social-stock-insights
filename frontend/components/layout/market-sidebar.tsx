'use client'

import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, TrendingDown, Flame, Wifi, WifiOff, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { useMarketData, MarketTicker } from "@/hooks/use-market-data"
import { useMarketStatus } from "@/hooks/use-market-status"

function MarketStatusCard() {
  const { isOpen, nextEvent, nextEventTime, isLoading } = useMarketStatus()

  if (isLoading || isOpen === null) {
    return (
      <Card className="glass-card border-border/50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="glass-card border-border/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Market Status</p>
            <p className="text-xs text-muted-foreground">
              {nextEvent && nextEventTime 
                ? `${nextEvent === 'opens' ? 'Opens' : 'Closes'} ${nextEventTime}`
                : 'NYSE & NASDAQ'
              }
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn(
              "h-2 w-2 rounded-full",
              isOpen ? "bg-green-500 animate-pulse" : "bg-red-500"
            )}></div>
            <Badge 
              variant="outline" 
              className={cn(
                isOpen 
                  ? "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20"
                  : "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20"
              )}
            >
              {isOpen ? 'Open' : 'Closed'}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function TickerSkeleton() {
  return (
    <div className="flex items-center justify-between p-2">
      <div className="space-y-2">
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-3 w-16" />
      </div>
      <Skeleton className="h-4 w-14" />
    </div>
  )
}

function TickerRow({ ticker }: { ticker: MarketTicker }) {
  const isUp = ticker.change_percent >= 0
  
  return (
    <Link href={`/stock/${ticker.ticker}`}>
      <div className="group flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-all cursor-pointer">
        <div className="flex flex-col">
          <span className="text-sm font-semibold">{ticker.ticker}</span>
          <span className="text-xs text-muted-foreground">
            ${ticker.price.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isUp ? (
            <TrendingUp className="h-3 w-3 text-green-600 dark:text-green-400" />
          ) : (
            <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />
          )}
          <span
            className={cn(
              "text-xs font-semibold",
              isUp 
                ? "text-green-600 dark:text-green-400" 
                : "text-red-600 dark:text-red-400"
            )}
          >
            {isUp && '+'}{ticker.change_percent.toFixed(2)}%
          </span>
        </div>
      </div>
    </Link>
  )
}

export function MarketSidebar() {
  const { data, isLoading, isError, wsConnected, reconnect } = useMarketData()

  // Get top 5 movers (sorted by absolute change)
  const topMovers = [...data]
    .sort((a, b) => Math.abs(b.change_percent) - Math.abs(a.change_percent))
    .slice(0, 5)

  // Get trending tickers (sorted by mentions, fallback to first 4)
  const trending = [...data]
    .sort((a, b) => (b.mentions || 0) - (a.mentions || 0))
    .slice(0, 4)

  return (
    <div className="space-y-4">
      {/* Market Status */}
      <MarketStatusCard />

      {/* Top Movers */}
      <Card className="glass-card border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              Market Pulse
            </CardTitle>
            <div className="flex items-center gap-1">
              {wsConnected ? (
                <Wifi className="h-3 w-3 text-green-500" />
              ) : (
                <button 
                  onClick={reconnect}
                  className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
                  title="Reconnect to live feed"
                >
                  <WifiOff className="h-3 w-3 text-yellow-500" />
                  <RefreshCw className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          {isLoading ? (
            <>
              <TickerSkeleton />
              <TickerSkeleton />
              <TickerSkeleton />
              <TickerSkeleton />
              <TickerSkeleton />
            </>
          ) : isError ? (
            <div className="text-center py-4 text-sm text-muted-foreground">
              <p>Unable to load market data</p>
              <button 
                onClick={reconnect}
                className="mt-2 text-primary hover:underline"
              >
                Try again
              </button>
            </div>
          ) : topMovers.length === 0 ? (
            <p className="text-center py-4 text-sm text-muted-foreground">
              No market data available
            </p>
          ) : (
            topMovers.map((ticker) => (
              <TickerRow key={ticker.ticker} ticker={ticker} />
            ))
          )}
        </CardContent>
      </Card>

      {/* Trending Now */}
      <Card className="glass-card border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Flame className="h-4 w-4 text-orange-500" />
            Trending Now
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-6 w-14 rounded-full" />
              <Skeleton className="h-6 w-12 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-14 rounded-full" />
            </div>
          ) : trending.length === 0 ? (
            <p className="text-sm text-muted-foreground">No trending tickers</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {trending.map((ticker, index) => (
                <Link key={ticker.ticker} href={`/stock/${ticker.ticker}`}>
                  <Badge 
                    variant="secondary" 
                    className={cn(
                      "cursor-pointer hover:bg-primary/10 hover:text-primary hover:scale-105 transition-all",
                      index === 0 && "glow border-primary/30"
                    )}
                  >
                    ${ticker.ticker}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
