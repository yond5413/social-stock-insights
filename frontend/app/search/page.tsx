"use client"

import { SearchPosts } from "@/components/search/search-posts"
import { UserSearch } from "@/components/search/user-search"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DashboardShell } from "@/components/layout/dashboard-shell"

export default function SearchPage() {
    return (
        <DashboardShell>
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight mb-2">Search & Explore</h1>
                <p className="text-muted-foreground">
                    Discover market insights, trending posts, and connect with other investors.
                </p>
            </div>

            <Tabs defaultValue="posts" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-8">
                    <TabsTrigger value="posts">Search Posts</TabsTrigger>
                    <TabsTrigger value="users">Find People</TabsTrigger>
                </TabsList>

                <TabsContent value="posts">
                    <Card>
                        <CardHeader>
                            <CardTitle>Search Posts</CardTitle>
                            <CardDescription>
                                Find discussions about specific tickers, market trends, or sentiments.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <SearchPosts />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="users">
                    <Card>
                        <CardHeader>
                            <CardTitle>Find People</CardTitle>
                            <CardDescription>
                                Connect with other traders and analysts.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <UserSearch />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </DashboardShell>
    )
}
