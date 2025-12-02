"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TrendingTickers } from "@/components/dashboard/trending-tickers"
import { InsightFeed } from "@/components/dashboard/insight-feed"
import { Activity, BarChart3, TrendingUp, Users } from "lucide-react"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { useAuth } from "@/contexts/AuthContext"

export default function DashboardPage() {
    const { user } = useAuth()
    const [stats, setStats] = useState<any>(null)
    const [userStats, setUserStats] = useState<any>(null)

    useEffect(() => {
        // Fetch system stats
        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
        fetch(`${baseUrl}/dashboard/stats`)
            .then((res) => res.json())
            .then((data) => setStats(data))
            .catch((err) => console.error("Failed to fetch stats", err))
    }, [])

    useEffect(() => {
        // Fetch user stats including reputation
        if (!user?.id) return

        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
        fetch(`${baseUrl}/users/${user.id}/stats`)
            .then((res) => res.json())
            .then((data) => setUserStats(data))
            .catch((err) => console.error("Failed to fetch user stats", err))
    }, [user])

    return (
        <DashboardShell>
            <div className="space-y-8">
                <div className="flex flex-col gap-2">
                    <h1 className="text-3xl font-bold tracking-tight">Market Dashboard</h1>
                    <p className="text-muted-foreground">
                        Real-time AI insights, market trends, and community sentiment.
                    </p>
                </div>

                {/* Top Stats Row */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                            <Users className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.active_users || "..."}</div>
                            <p className="text-xs text-muted-foreground">
                                {stats?.active_users_change !== undefined 
                                    ? `${stats.active_users_change >= 0 ? '+' : ''}${stats.active_users_change.toFixed(1)}% from last month`
                                    : "..."}
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Insights Generated</CardTitle>
                            <Activity className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.insights_generated || "..."}</div>
                            <p className="text-xs text-muted-foreground">
                                {stats?.insights_change !== undefined 
                                    ? `${stats.insights_change >= 0 ? '+' : ''}${stats.insights_change} since last hour`
                                    : "..."}
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Avg. Accuracy</CardTitle>
                            <TrendingUp className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">
                                {stats?.avg_accuracy !== undefined && stats.avg_accuracy !== null
                                    ? `${(stats.avg_accuracy * 100).toFixed(1)}%` 
                                    : "..."}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                {stats?.accuracy_change !== undefined 
                                    ? `${stats.accuracy_change >= 0 ? '+' : ''}${stats.accuracy_change.toFixed(1)}% from last week`
                                    : "..."}
                            </p>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Top Sector</CardTitle>
                            <BarChart3 className="h-4 w-4 text-muted-foreground" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{stats?.top_sector || "..."}</div>
                            <p className="text-xs text-muted-foreground">Based on volume</p>
                        </CardContent>
                    </Card>
                </div>

                <div className="grid gap-6 md:grid-cols-7 lg:grid-cols-8">
                    {/* Main Feed Area */}
                    <div className="col-span-4 lg:col-span-5">
                        <Tabs defaultValue="balanced" className="space-y-4">
                            <div className="flex items-center justify-between">
                                <TabsList>
                                    <TabsTrigger value="balanced">Balanced</TabsTrigger>
                                    <TabsTrigger value="quality_focused">High Quality</TabsTrigger>
                                    <TabsTrigger value="timely">Real-time</TabsTrigger>
                                    <TabsTrigger value="diverse">Diverse</TabsTrigger>
                                </TabsList>
                            </div>

                            <TabsContent value="balanced" className="space-y-4">
                                <InsightFeed strategy="balanced" />
                            </TabsContent>
                            <TabsContent value="quality_focused" className="space-y-4">
                                <InsightFeed strategy="quality_focused" />
                            </TabsContent>
                            <TabsContent value="timely" className="space-y-4">
                                <InsightFeed strategy="timely" />
                            </TabsContent>
                            <TabsContent value="diverse" className="space-y-4">
                                <InsightFeed strategy="diverse" />
                            </TabsContent>
                        </Tabs>
                    </div>

                    {/* Sidebar */}
                    <div className="col-span-3 lg:col-span-3 space-y-6">
                        <TrendingTickers />

                        <Card>
                            <CardHeader>
                                <CardTitle>Your Reputation</CardTitle>
                            </CardHeader>
                            <CardContent>
                                {user && userStats ? (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm font-medium">Score</span>
                                            <span className="text-xl font-bold text-green-500">
                                                {Math.round((userStats.reputation || 0) * 1000)}
                                            </span>
                                        </div>
                                        <div className="h-2 bg-secondary rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-green-500"
                                                style={{ width: `${(userStats.reputation || 0) * 100}%` }}
                                            />
                                        </div>
                                        <p className="text-xs text-muted-foreground">
                                            {userStats.reputation >= 0.85
                                                ? "Top 5% of analysts. Keep posting high-quality insights to maintain your rank."
                                                : userStats.reputation >= 0.7
                                                    ? "Top 15% of analysts. Great work! Keep it up to reach the top tier."
                                                    : userStats.reputation >= 0.5
                                                        ? "Average performer. Post more quality insights to improve your rank."
                                                        : "New analyst. Start posting quality insights to build your reputation."
                                            }
                                        </p>
                                        <div className="pt-2 border-t border-border">
                                            <div className="grid grid-cols-2 gap-4 text-center">
                                                <div>
                                                    <div className="text-lg font-bold">{userStats.followers_count || 0}</div>
                                                    <div className="text-xs text-muted-foreground">Followers</div>
                                                </div>
                                                <div>
                                                    <div className="text-lg font-bold">{userStats.following_count || 0}</div>
                                                    <div className="text-xs text-muted-foreground">Following</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4 animate-pulse">
                                        <div className="h-4 bg-secondary rounded w-full" />
                                        <div className="h-2 bg-secondary rounded w-full" />
                                        <div className="h-4 bg-secondary rounded w-3/4" />
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </DashboardShell>
    )
}
