"use client"

import { useState } from "react"
import { Search, Loader2, User as UserIcon } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { createClient } from "@/lib/supabase/client"
import { apiRequest } from "@/lib/api"
import { FollowButton } from "@/components/users/follow-button"
import Link from "next/link"

interface UserResult {
    id: string
    username: string
    similarity: number
}

export function UserSearch() {
    const [query, setQuery] = useState("")
    const [results, setResults] = useState<UserResult[]>([])
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

            const data = await apiRequest<UserResult[]>(
                `/users/search?query=${encodeURIComponent(query)}&limit=10`,
                {
                    token: session.access_token
                }
            )
            
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
                        placeholder="Search users by username..."
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
                        No users found matching your query.
                    </div>
                )}

                {results.map((user) => (
                    <Card key={user.id}>
                        <CardContent className="flex items-center justify-between p-4">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-full bg-secondary flex items-center justify-center">
                                    <UserIcon className="h-5 w-5 text-muted-foreground" />
                                </div>
                                <div>
                                    <Link href={`/profile/${user.id}`} className="font-medium hover:underline">
                                        {user.username}
                                    </Link>
                                </div>
                            </div>
                            <FollowButton userId={user.id} />
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
