"use client"

import { useMemo } from "react"
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"

interface PricePoint {
  date: string
  close: number
  volume?: number
}

interface SentimentPoint {
  date: string
  score: number
  post_count: number
}

interface SentimentPriceChartProps {
  prices: PricePoint[]
  sentiment: SentimentPoint[]
  overallSentiment: "bullish" | "bearish" | "neutral" | "mixed"
  className?: string
  showTooltip?: boolean
  height?: number
  compact?: boolean
}

// Merge price and sentiment data by date
function mergeData(prices: PricePoint[], sentiment: SentimentPoint[]) {
  const sentimentMap = new Map(sentiment.map(s => [s.date.split("T")[0], s]))
  
  return prices.map(p => {
    const dateKey = p.date.split("T")[0]
    const sentimentData = sentimentMap.get(dateKey)
    
    return {
      date: dateKey,
      close: p.close,
      volume: p.volume,
      sentimentScore: sentimentData?.score ?? 0,
      postCount: sentimentData?.post_count ?? 0,
    }
  })
}

// Get gradient colors based on sentiment
function getSentimentGradient(sentiment: string) {
  switch (sentiment) {
    case "bullish":
      return {
        stroke: "#16a34a", // green-600
        gradientStart: "#22c55e", // green-500
        gradientEnd: "#16a34a",
      }
    case "bearish":
      return {
        stroke: "#dc2626", // red-600
        gradientStart: "#ef4444", // red-500
        gradientEnd: "#dc2626",
      }
    case "mixed":
      return {
        stroke: "#f59e0b", // amber-500
        gradientStart: "#fbbf24", // amber-400
        gradientEnd: "#f59e0b",
      }
    default:
      return {
        stroke: "#8b5cf6", // violet-500
        gradientStart: "#a78bfa", // violet-400
        gradientEnd: "#8b5cf6",
      }
  }
}

// Custom tooltip component
function CustomTooltip({ active, payload, compact }: any) {
  if (!active || !payload || !payload.length) return null
  
  const data = payload[0].payload
  const priceChange = payload.length > 1 ? 
    ((data.close - payload[0].payload.close) / payload[0].payload.close * 100).toFixed(2) : null
  
  if (compact) {
    return (
      <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg px-2 py-1 shadow-lg">
        <p className="text-xs font-medium">${data.close?.toFixed(2)}</p>
      </div>
    )
  }
  
  return (
    <div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg px-3 py-2 shadow-lg">
      <p className="text-xs text-muted-foreground mb-1">{data.date}</p>
      <p className="text-sm font-semibold">${data.close?.toFixed(2)}</p>
      {data.postCount > 0 && (
        <p className="text-xs text-muted-foreground mt-1">
          {data.postCount} posts • Sentiment: {data.sentimentScore > 0 ? "+" : ""}{(data.sentimentScore * 100).toFixed(0)}%
        </p>
      )}
    </div>
  )
}

export function SentimentPriceChart({
  prices,
  sentiment,
  overallSentiment,
  className,
  showTooltip = true,
  height = 80,
  compact = false,
}: SentimentPriceChartProps) {
  const data = useMemo(() => mergeData(prices, sentiment), [prices, sentiment])
  const colors = useMemo(() => getSentimentGradient(overallSentiment), [overallSentiment])
  
  const gradientId = useMemo(() => `sentiment-gradient-${Math.random().toString(36).slice(2)}`, [])
  
  if (!data.length) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-xs", className)} style={{ height }}>
        No data
      </div>
    )
  }

  // Calculate domain with padding
  const minPrice = Math.min(...data.map(d => d.close))
  const maxPrice = Math.max(...data.map(d => d.close))
  const padding = (maxPrice - minPrice) * 0.1
  
  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colors.gradientStart} stopOpacity={0.4} />
              <stop offset="50%" stopColor={colors.gradientStart} stopOpacity={0.15} />
              <stop offset="100%" stopColor={colors.gradientEnd} stopOpacity={0} />
            </linearGradient>
          </defs>
          
          {!compact && (
            <XAxis 
              dataKey="date" 
              hide 
              axisLine={false}
              tickLine={false}
            />
          )}
          
          <YAxis 
            hide 
            domain={[minPrice - padding, maxPrice + padding]}
            axisLine={false}
            tickLine={false}
          />
          
          {showTooltip && (
            <Tooltip 
              content={<CustomTooltip compact={compact} />}
              cursor={{ stroke: colors.stroke, strokeWidth: 1, strokeDasharray: "3 3" }}
            />
          )}
          
          <Area
            type="monotone"
            dataKey="close"
            stroke={colors.stroke}
            strokeWidth={compact ? 1.5 : 2}
            fill={`url(#${gradientId})`}
            animationDuration={750}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// Mini version for card previews
export function MiniSentimentChart({
  prices,
  sentiment,
  overallSentiment,
  className,
}: Omit<SentimentPriceChartProps, "height" | "showTooltip" | "compact">) {
  return (
    <SentimentPriceChart
      prices={prices}
      sentiment={sentiment}
      overallSentiment={overallSentiment}
      className={className}
      height={60}
      showTooltip={true}
      compact={true}
    />
  )
}

// Loading skeleton for the chart
export function SentimentChartSkeleton({ height = 80 }: { height?: number }) {
  return (
    <div 
      className="w-full bg-gradient-to-br from-muted/50 to-muted/30 rounded-lg animate-pulse"
      style={{ height }}
    />
  )
}


