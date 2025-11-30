"use client"

import { useState, useMemo } from "react"
import {
  ComposedChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { BarChart3, TrendingUp } from "lucide-react"

interface PricePoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface SentimentPoint {
  date: string
  score: number
  bullish_count: number
  bearish_count: number
  neutral_count: number
  post_count: number
}

interface StockDetailChartProps {
  prices: PricePoint[]
  sentiment: SentimentPoint[]
  ticker: string
  className?: string
}

type ChartType = "candlestick" | "line"

// Custom candlestick shape component
function CandlestickBar(props: any) {
  const { x, y, width, height, payload } = props
  
  if (!payload) return null
  
  const { open, close, high, low } = payload
  const isUp = close >= open
  const color = isUp ? "#22c55e" : "#ef4444"
  
  // Calculate positions
  const bodyTop = Math.min(open, close)
  const bodyBottom = Math.max(open, close)
  const bodyHeight = Math.abs(close - open)
  
  // Scale values for display
  const yScale = props.yScale || ((v: number) => v)
  const scaledHigh = yScale(high)
  const scaledLow = yScale(low)
  const scaledBodyTop = yScale(bodyTop)
  const scaledBodyBottom = yScale(bodyBottom)
  
  const candleWidth = Math.max(width * 0.6, 3)
  const wickWidth = 1
  const candleX = x + (width - candleWidth) / 2
  const wickX = x + width / 2
  
  return (
    <g>
      {/* Wick (high to low) */}
      <line
        x1={wickX}
        y1={scaledHigh}
        x2={wickX}
        y2={scaledLow}
        stroke={color}
        strokeWidth={wickWidth}
      />
      {/* Body */}
      <rect
        x={candleX}
        y={scaledBodyTop}
        width={candleWidth}
        height={Math.max(scaledBodyBottom - scaledBodyTop, 1)}
        fill={isUp ? color : color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  )
}

// Custom tooltip component
function CustomTooltip({ active, payload, chartType }: any) {
  if (!active || !payload || !payload.length) return null
  
  const data = payload[0].payload
  
  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-xl px-4 py-3 shadow-xl">
      <p className="text-xs text-muted-foreground mb-2 font-medium">
        {new Date(data.date).toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric',
          year: 'numeric'
        })}
      </p>
      
      {chartType === "candlestick" && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <span className="text-muted-foreground">Open</span>
          <span className="font-semibold text-right">${data.open?.toFixed(2)}</span>
          <span className="text-muted-foreground">High</span>
          <span className="font-semibold text-right text-green-500">${data.high?.toFixed(2)}</span>
          <span className="text-muted-foreground">Low</span>
          <span className="font-semibold text-right text-red-500">${data.low?.toFixed(2)}</span>
          <span className="text-muted-foreground">Close</span>
          <span className={cn(
            "font-semibold text-right",
            data.close >= data.open ? "text-green-500" : "text-red-500"
          )}>
            ${data.close?.toFixed(2)}
          </span>
        </div>
      )}
      
      {chartType === "line" && (
        <div className="space-y-1">
          <p className="text-lg font-bold">${data.close?.toFixed(2)}</p>
          {data.sentimentScore !== undefined && data.postCount > 0 && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className={cn(
                "px-1.5 py-0.5 rounded",
                data.sentimentScore > 0 ? "bg-green-500/10 text-green-600" :
                data.sentimentScore < 0 ? "bg-red-500/10 text-red-600" :
                "bg-gray-500/10 text-gray-600"
              )}>
                {data.sentimentScore > 0 ? "+" : ""}{(data.sentimentScore * 100).toFixed(0)}%
              </span>
              <span>{data.postCount} posts</span>
            </div>
          )}
        </div>
      )}
      
      {data.volume && (
        <div className="mt-2 pt-2 border-t border-border">
          <span className="text-xs text-muted-foreground">
            Vol: {(data.volume / 1000000).toFixed(2)}M
          </span>
        </div>
      )}
    </div>
  )
}

export function StockDetailChart({
  prices,
  sentiment,
  ticker,
  className,
}: StockDetailChartProps) {
  const [chartType, setChartType] = useState<ChartType>("line")
  
  // Merge price and sentiment data
  const data = useMemo(() => {
    const sentimentMap = new Map(
      sentiment.map(s => [s.date.split("T")[0], s])
    )
    
    return prices.map(p => {
      const dateKey = p.date.split("T")[0]
      const sentimentData = sentimentMap.get(dateKey)
      
      return {
        ...p,
        date: dateKey,
        sentimentScore: sentimentData?.score ?? 0,
        postCount: sentimentData?.post_count ?? 0,
        bullish: sentimentData?.bullish_count ?? 0,
        bearish: sentimentData?.bearish_count ?? 0,
        neutral: sentimentData?.neutral_count ?? 0,
      }
    })
  }, [prices, sentiment])
  
  // Calculate price stats
  const stats = useMemo(() => {
    if (data.length === 0) return null
    
    const closes = data.map(d => d.close)
    const highs = data.map(d => d.high)
    const lows = data.map(d => d.low)
    
    return {
      min: Math.min(...lows),
      max: Math.max(...highs),
      avg: closes.reduce((a, b) => a + b, 0) / closes.length,
      first: data[0]?.close ?? 0,
      last: data[data.length - 1]?.close ?? 0,
    }
  }, [data])
  
  if (!data.length || !stats) {
    return (
      <div className={cn("flex items-center justify-center h-[400px] text-muted-foreground", className)}>
        No price data available
      </div>
    )
  }
  
  const priceChange = ((stats.last - stats.first) / stats.first) * 100
  const isUp = priceChange >= 0
  
  // Calculate Y domain with padding
  const yPadding = (stats.max - stats.min) * 0.1
  const yDomain = [stats.min - yPadding, stats.max + yPadding]
  
  return (
    <div className={cn("space-y-4", className)}>
      {/* Chart Type Toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Chart Type</span>
          <div className="flex rounded-lg border border-border overflow-hidden">
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "rounded-none px-3 h-8",
                chartType === "line" && "bg-primary/10 text-primary"
              )}
              onClick={() => setChartType("line")}
            >
              <TrendingUp className="h-4 w-4 mr-1" />
              Line
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                "rounded-none px-3 h-8 border-l border-border",
                chartType === "candlestick" && "bg-primary/10 text-primary"
              )}
              onClick={() => setChartType("candlestick")}
            >
              <BarChart3 className="h-4 w-4 mr-1" />
              OHLC
            </Button>
          </div>
        </div>
        
        <div className={cn(
          "text-sm font-semibold px-2 py-1 rounded",
          isUp ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-600"
        )}>
          {isUp ? "+" : ""}{priceChange.toFixed(2)}%
        </div>
      </div>
      
      {/* Main Chart */}
      <div className="h-[350px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop 
                  offset="0%" 
                  stopColor={isUp ? "#22c55e" : "#ef4444"} 
                  stopOpacity={0.3} 
                />
                <stop 
                  offset="100%" 
                  stopColor={isUp ? "#22c55e" : "#ef4444"} 
                  stopOpacity={0} 
                />
              </linearGradient>
              <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="hsl(var(--border))" 
              opacity={0.3}
              vertical={false}
            />
            
            <XAxis 
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickFormatter={(value) => {
                const date = new Date(value)
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              }}
              minTickGap={50}
            />
            
            <YAxis
              domain={yDomain}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
              width={60}
            />
            
            <Tooltip content={<CustomTooltip chartType={chartType} />} />
            
            {/* Average price reference line */}
            <ReferenceLine 
              y={stats.avg} 
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="3 3"
              strokeOpacity={0.5}
            />
            
            {chartType === "line" ? (
              <>
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke={isUp ? "#22c55e" : "#ef4444"}
                  strokeWidth={2}
                  fill="url(#priceGradient)"
                  animationDuration={750}
                />
              </>
            ) : (
              <>
                {/* Candlestick bars - using Bar component with custom shape */}
                <Bar
                  dataKey="high"
                  shape={(props: any) => {
                    const { x, width, payload, yAxisMap } = props
                    if (!payload || !yAxisMap) return <g />
                    
                    const yAxis = Object.values(yAxisMap)[0] as any
                    const yScale = yAxis?.scale
                    if (!yScale) return <g />
                    
                    const { open, close, high, low } = payload
                    const isUp = close >= open
                    const color = isUp ? "#22c55e" : "#ef4444"
                    
                    const scaledHigh = yScale(high)
                    const scaledLow = yScale(low)
                    const scaledOpen = yScale(open)
                    const scaledClose = yScale(close)
                    
                    const candleWidth = Math.max(width * 0.6, 4)
                    const wickWidth = 1.5
                    const candleX = x + (width - candleWidth) / 2
                    const wickX = x + width / 2
                    
                    const bodyTop = Math.min(scaledOpen, scaledClose)
                    const bodyHeight = Math.max(Math.abs(scaledClose - scaledOpen), 1)
                    
                    return (
                      <g>
                        <line
                          x1={wickX}
                          y1={scaledHigh}
                          x2={wickX}
                          y2={scaledLow}
                          stroke={color}
                          strokeWidth={wickWidth}
                        />
                        <rect
                          x={candleX}
                          y={bodyTop}
                          width={candleWidth}
                          height={bodyHeight}
                          fill={color}
                          stroke={color}
                          strokeWidth={1}
                        />
                      </g>
                    )
                  }}
                  isAnimationActive={false}
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      
      {/* Sentiment overlay bar */}
      {sentiment.length > 0 && chartType === "line" && (
        <div className="h-[60px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <XAxis 
                dataKey="date" 
                hide 
              />
              <YAxis 
                domain={[-1, 1]}
                hide
              />
              <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1} />
              <Area
                type="monotone"
                dataKey="sentimentScore"
                stroke="#8b5cf6"
                strokeWidth={1.5}
                fill="url(#sentimentGradient)"
              />
              <Tooltip 
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null
                  const d = payload[0].payload
                  if (d.postCount === 0) return null
                  return (
                    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
                      <div className="font-medium mb-1">Community Sentiment</div>
                      <div className="flex gap-3">
                        <span className="text-green-500">{d.bullish} bullish</span>
                        <span className="text-red-500">{d.bearish} bearish</span>
                        <span className="text-gray-500">{d.neutral} neutral</span>
                      </div>
                    </div>
                  )
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// Loading skeleton
export function StockDetailChartSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-4 w-20 bg-muted rounded animate-pulse" />
          <div className="h-8 w-32 bg-muted rounded animate-pulse" />
        </div>
        <div className="h-6 w-16 bg-muted rounded animate-pulse" />
      </div>
      <div className="h-[350px] w-full bg-gradient-to-b from-muted/50 to-muted/20 rounded-xl animate-pulse" />
    </div>
  )
}


