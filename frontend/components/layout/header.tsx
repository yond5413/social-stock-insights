"use client"

import { useState, useCallback, KeyboardEvent, ChangeEvent } from "react"
import { useRouter } from "next/navigation"
import { Search, Sparkles } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { AuthButtons } from "@/app/auth-client"
import { GradientText } from "@/components/ui/gradient-text"
import Link from "next/link"

export function Header() {
  const router = useRouter()
  const [searchValue, setSearchValue] = useState("")

  const handleSearch = useCallback(() => {
    const ticker = searchValue.trim().toUpperCase()
    // Basic ticker validation: 1-5 uppercase letters
    if (ticker && /^[A-Z]{1,5}$/.test(ticker)) {
      router.push(`/stock/${ticker}`)
      setSearchValue("")
    }
  }, [searchValue, router])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSearch()
    }
  }, [handleSearch])

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    // Allow typing but convert to uppercase for display
    setSearchValue(e.target.value.toUpperCase())
  }, [])

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
          <form
            onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            className="relative group hidden md:block"
          >
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
            <Input
              type="search"
              value={searchValue}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="Search tickers... (e.g., AAPL)"
              className="w-[200px] md:w-[300px] pl-9 bg-muted/50 border-border/50 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
              maxLength={5}
            />
          </form>

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
