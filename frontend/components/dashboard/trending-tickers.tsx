"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"

interface TrendingTicker {
    ticker: string
    count: number
    price?: number
    change_percent?: number
}

export function TrendingTickers() {
    const [tickers, setTickers] = useState<TrendingTicker[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
        fetch(`${baseUrl}/dashboard/trending?limit=5`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`)
                }
                return res.json()
            })
            .then((data) => {
                if (Array.isArray(data)) {
                    setTickers(data)
                } else {
                    console.error("Expected array but got:", data)
                    setTickers([])
                }
                setLoading(false)
            })
            .catch((err) => {
                console.error("Failed to fetch trending tickers", err)
                setTickers([])
                setLoading(false)
            })
    }, [])

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Trending Tickers</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="flex items-center justify-between animate-pulse">
                                <div className="h-4 w-12 bg-secondary rounded" />
                                <div className="h-4 w-16 bg-secondary rounded" />
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Trending Tickers</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {tickers.map((item) => (
                        <div key={item.ticker} className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="font-bold">{item.ticker}</div>
                                <div className="text-xs text-muted-foreground">{item.count} mentions</div>
                            </div>
                            <div className="flex flex-col items-end">
                                <div className="font-medium">
                                    ${item.price?.toFixed(2) || "---"}
                                </div>
                                {item.change_percent !== undefined && (
                                    <div className={`text-xs flex items-center ${item.change_percent > 0 ? "text-green-500" :
                                        item.change_percent < 0 ? "text-red-500" : "text-muted-foreground"
                                        }`}>
                                        {item.change_percent > 0 ? <ArrowUpRight className="h-3 w-3 mr-1" /> :
                                            item.change_percent < 0 ? <ArrowDownRight className="h-3 w-3 mr-1" /> :
                                                <Minus className="h-3 w-3 mr-1" />}
                                        {Math.abs(item.change_percent).toFixed(2)}%
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {tickers.length === 0 && (
                        <div className="text-sm text-muted-foreground text-center py-4">
                            No trending data available
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
