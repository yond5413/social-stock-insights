'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown, Flame } from "lucide-react"
import { cn } from "@/lib/utils"

export function MarketSidebar() {
  // Mock data for now
  const topMovers = [
    { ticker: "NVDA", change: 2.5, price: "485.00", type: "up" as const },
    { ticker: "TSLA", change: -1.2, price: "240.50", type: "down" as const },
    { ticker: "AAPL", change: 0.8, price: "192.30", type: "up" as const },
    { ticker: "AMD", change: 3.1, price: "145.20", type: "up" as const },
    { ticker: "MSFT", change: -0.5, price: "370.10", type: "down" as const },
  ]

  const trending = ["PLTR", "COIN", "HOOD", "AMZN"]

  return (
    <div className="space-y-4">
      {/* Market Status */}
      <Card className="glass-card border-border/50">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Market Status</p>
              <p className="text-xs text-muted-foreground">NYSE & NASDAQ</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
              <Badge variant="outline" className="bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20">
                Open
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Top Movers */}
      <Card className="glass-card border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Market Pulse
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {topMovers.map((item) => (
            <div
              key={item.ticker}
              className="group flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 transition-all cursor-pointer"
            >
              <div className="flex flex-col">
                <span className="text-sm font-semibold">{item.ticker}</span>
                <span className="text-xs text-muted-foreground">
                  ${item.price}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {item.type === "up" ? (
                  <TrendingUp className="h-3 w-3 text-green-600 dark:text-green-400" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-600 dark:text-red-400" />
                )}
                <span
                  className={cn(
                    "text-xs font-semibold",
                    item.type === "up" 
                      ? "text-green-600 dark:text-green-400" 
                      : "text-red-600 dark:text-red-400"
                  )}
                >
                  {item.change > 0 && '+'}{item.change}%
                </span>
              </div>
            </div>
          ))}
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
          <div className="flex flex-wrap gap-2">
            {trending.map((ticker, index) => (
              <Badge 
                key={ticker} 
                variant="secondary" 
                className={cn(
                  "cursor-pointer hover:bg-primary/10 hover:text-primary hover:scale-105 transition-all",
                  index === 0 && "glow border-primary/30"
                )}
              >
                ${ticker}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
