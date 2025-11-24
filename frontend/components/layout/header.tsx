"use client"

import { Search, Sparkles } from "lucide-react"
import { Input } from "@/components/ui/input"
import { AuthButtons } from "@/app/auth-client"
import { GradientText } from "@/components/ui/gradient-text"

export function Header() {
  return (
    <div className="sticky top-0 z-50 glass-nav border-b">
      <div className="flex h-16 items-center px-4 md:px-6">
        {/* Logo - visible on mobile */}
        <div className="flex items-center gap-2 md:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-pink-500">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <GradientText className="text-lg font-bold">Insights</GradientText>
        </div>

        <div className="ml-auto flex items-center space-x-4">
          {/* Search */}
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
            <Input
              type="search"
              placeholder="Search tickers..."
              className="w-[200px] md:w-[300px] pl-9 bg-muted/50 border-border/50 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>
          
          {/* Auth Buttons */}
          <AuthButtons />
        </div>
      </div>
    </div>
  )
}
