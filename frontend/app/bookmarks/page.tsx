"use client"

import { motion } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { Card, CardContent } from "@/components/ui/card"
import { GradientText } from "@/components/ui/gradient-text"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { Bookmark, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function BookmarksPage() {
  return (
    <DashboardShell>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-6"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-slate-500 shadow-lg shadow-blue-500/30">
            <Bookmark className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
              <GradientText>Your Bookmarks</GradientText>
            </h1>
            <p className="text-muted-foreground">
              Saved insights for later reading
            </p>
          </div>
        </motion.div>

        {/* Empty State */}
        <motion.div variants={fadeInUp}>
          <Card className="glass-card border-border/50">
            <CardContent className="p-12">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-slate-500 opacity-50">
                  <Bookmark className="h-8 w-8 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">No bookmarks yet</h3>
                  <p className="text-muted-foreground max-w-md">
                    Start bookmarking insightful posts to build your personal collection of market intelligence.
                  </p>
                </div>
                <Button className="mt-2 bg-gradient-to-r from-blue-500 to-slate-500 hover:from-blue-600 hover:to-slate-600">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Explore Feed
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </DashboardShell>
  )
}
