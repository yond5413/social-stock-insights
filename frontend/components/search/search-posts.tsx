"use client"

import { useState } from "react"
import { Search, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { createClient } from "@/lib/supabase/client"
import Link from "next/link"

interface Post {
    id: string
    content: string
    tickers: string[]
    created_at: string
    similarity: number
    user_id: string
}

export function SearchPosts() {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState<Post[]>([])
    const [loading, setLoading] = useState(false)
    const [hasSearched, setHasSearched] = useState(false)

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!query.trim()) return

        setLoading(true)
        setHasSearched(true)

        try {
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()

            if (!session) return

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/posts/search?query=${encodeURIComponent(query)}&limit=10`, {
                headers: {
                    Authorization: `Bearer ${session.access_token}`
                }
            })

            if (!response.ok) throw new Error("Search failed")

            const data = await response.json()
            setResults(data)
        } catch (error) {
            console.error("Search error:", error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search posts (e.g., 'bullish on tech', 'market crash')..."
                        className="pl-9"
                    />
                </div>
                <Button type="submit" disabled={loading}>
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
                </Button>
            </form>

            <div className="space-y-4">
                {hasSearched && results.length === 0 && !loading && (
                    <div className="text-center text-muted-foreground py-8">
                        No posts found matching your query.
                    </div>
                )}

                {results.map((post) => (
                    <Card key={post.id}>
                        <CardContent className="pt-6">
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex gap-2">
                                    {post.tickers.map((ticker) => (
                                        <Link
                                            key={ticker}
                                            href={`/stock/${ticker}`}
                                            className="text-xs font-medium bg-secondary px-2 py-1 rounded hover:bg-secondary/80 transition-colors"
                                        >
                                            ${ticker}
                                        </Link>
                                    ))}
                                </div>
                                <span className="text-xs text-muted-foreground">
                                    {new Date(post.created_at).toLocaleDateString()}
                                </span>
                            </div>
                            <p className="whitespace-pre-wrap mb-2">{post.content}</p>
                            <div className="text-xs text-muted-foreground">
                                Relevance: {(post.similarity * 100).toFixed(1)}%
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
