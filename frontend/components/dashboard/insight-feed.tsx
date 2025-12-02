"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Info, ThumbsUp, MessageSquare, Share2 } from "lucide-react"

interface FeedItem {
    id: string
    content: string
    username: string
    created_at: string
    insight_type?: string
    sector?: string
    ranking_explanation?: string
    quality_score?: number
    sentiment?: string
}

export function InsightFeed({ strategy }: { strategy: string }) {
    const [posts, setPosts] = useState<FeedItem[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
        fetch(`${baseUrl}/dashboard/insights?strategy=${strategy}&limit=10`)
            .then((res) => {
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`)
                }
                return res.json()
            })
            .then((data) => {
                if (Array.isArray(data)) {
                    setPosts(data)
                } else {
                    console.error("Received invalid data format:", data)
                    setPosts([])
                }
                setLoading(false)
            })
            .catch((err) => {
                console.error("Failed to fetch insights", err)
                setLoading(false)
            })
    }, [strategy])

    if (loading) {
        return <div className="space-y-4">
            {[1, 2].map((i) => (
                <Card key={i} className="animate-pulse">
                    <CardHeader className="h-20 bg-secondary/50" />
                    <CardContent className="h-32 bg-secondary/30" />
                </Card>
            ))}
        </div>
    }

    return (
        <div className="space-y-4">
            {posts.map((post) => (
                <Card key={post.id} className="overflow-hidden">
                    <CardHeader className="flex flex-row items-start gap-4 p-4 pb-2">
                        <Avatar>
                            <AvatarImage src={`https://avatar.vercel.sh/${post.username}`} />
                            <AvatarFallback>{post.username[0]}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 space-y-1">
                            <div className="flex items-center justify-between">
                                <div className="font-semibold">{post.username}</div>
                                <div className="text-xs text-muted-foreground">
                                    {new Date(post.created_at).toLocaleDateString()}
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {post.insight_type && (
                                    <Badge variant="secondary" className="text-xs">
                                        {post.insight_type.replace("_", " ")}
                                    </Badge>
                                )}
                                {post.sector && (
                                    <Badge variant="outline" className="text-xs">
                                        {post.sector}
                                    </Badge>
                                )}
                            </div>
                        </div>
                    </CardHeader>

                    <CardContent className="p-4 pt-2">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                            {post.content}
                        </p>

                        {/* Transparency Section */}
                        {post.ranking_explanation && (
                            <div className="mt-4 p-3 bg-secondary/20 rounded-lg border border-secondary flex items-start gap-3">
                                <Info className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                                <div className="space-y-1">
                                    <div className="text-xs font-semibold text-blue-500 uppercase tracking-wider">
                                        Why this post?
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                        {post.ranking_explanation}
                                    </p>
                                </div>
                            </div>
                        )}
                    </CardContent>

                    <CardFooter className="p-4 pt-0 flex justify-between items-center text-muted-foreground">
                        <div className="flex gap-4">
                            <Button variant="ghost" size="sm" className="gap-2">
                                <ThumbsUp className="h-4 w-4" />
                                <span className="text-xs">Like</span>
                            </Button>
                            <Button variant="ghost" size="sm" className="gap-2">
                                <MessageSquare className="h-4 w-4" />
                                <span className="text-xs">Comment</span>
                            </Button>
                        </div>

                        {post.quality_score && (
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger>
                                        <Badge variant={post.quality_score > 0.7 ? "default" : "secondary"}>
                                            Quality: {(post.quality_score * 100).toFixed(0)}%
                                        </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p>AI-assessed quality score based on depth and reasoning.</p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        )}
                    </CardFooter>
                </Card>
            ))}

            {posts.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    No insights found for this strategy.
                </div>
            )}
        </div>
    )
}
