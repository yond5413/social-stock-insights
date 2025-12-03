"use client"

import { Search, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AuthButtons } from "@/app/auth-client"
import { GradientText } from "@/components/ui/gradient-text"
import { TickerSearch } from "@/components/search/ticker-search"
import Link from "next/link"

export function Header() {

  return (
    <div className="sticky top-0 z-50 glass-nav border-b">
      <div className="flex h-16 items-center px-4 md:px-6">
        {/* Logo - visible on mobile */}
        <div className="flex items-center gap-2 md:hidden">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <GradientText className="text-lg font-bold">Insights</GradientText>
        </div>

        <div className="ml-auto flex items-center space-x-4">
          {/* Search */}
          <div className="hidden md:block">
            <TickerSearch />
          </div>

          <Button variant="ghost" size="icon" asChild className="md:hidden">
            <Link href="/search">
              <Search className="h-5 w-5" />
              <span className="sr-only">Search</span>
            </Link>
          </Button>

          <Button variant="ghost" asChild className="hidden md:flex">
            <Link href="/search">
              Explore
            </Link>
          </Button>

          {/* Auth Buttons */}
          <AuthButtons />
        </div>
      </div>
    </div>
  )
}
