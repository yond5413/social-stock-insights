"use client"

import { useState, useCallback, useRef, useEffect, KeyboardEvent } from "react"
import { useRouter } from "next/navigation"
import { Search, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { apiRequest } from "@/lib/api"

interface TickerResult {
    symbol: string
    name: string
    logo_url: string | null
    similarity: number
}

export function TickerSearch() {
    const router = useRouter()
    const [query, setQuery] = useState("")
    const [results, setResults] = useState<TickerResult[]>([])
    const [loading, setLoading] = useState(false)
    const [showDropdown, setShowDropdown] = useState(false)
    const [selectedIndex, setSelectedIndex] = useState(-1)
    const dropdownRef = useRef<HTMLDivElement>(null)
    const debounceRef = useRef<NodeJS.Timeout | undefined>(undefined)

    // Fetch search results
    const fetchResults = useCallback(async (searchQuery: string) => {
        if (!searchQuery || searchQuery.trim().length === 0) {
            setResults([])
            setShowDropdown(false)
            return
        }

        setLoading(true)
        try {
            const data = await apiRequest<TickerResult[]>(
                `/market/search?q=${encodeURIComponent(searchQuery)}`
            )
            setResults(data || [])
            setShowDropdown((data || []).length > 0)
        } catch (error) {
            console.error("Search error:", error)
            setResults([])
            setShowDropdown(false)
        } finally {
            setLoading(false)
        }
    }, [])

    // Debounced search
    const handleInputChange = useCallback((value: string) => {
        setQuery(value)
        setSelectedIndex(-1)

        // Clear previous timeout
        if (debounceRef.current) {
            clearTimeout(debounceRef.current)
        }

        // Set new timeout
        debounceRef.current = setTimeout(() => {
            fetchResults(value)
        }, 300)
    }, [fetchResults])

    // Navigate to ticker
    const navigateToTicker = useCallback((symbol: string) => {
        router.push(`/stock/${symbol}`)
        setQuery("")
        setResults([])
        setShowDropdown(false)
        setSelectedIndex(-1)
    }, [router])

    // Handle keyboard navigation
    const handleKeyDown = useCallback((e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "ArrowDown") {
            e.preventDefault()
            setSelectedIndex(prev => (prev < results.length - 1 ? prev + 1 : prev))
        } else if (e.key === "ArrowUp") {
            e.preventDefault()
            setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1))
        } else if (e.key === "Enter") {
            e.preventDefault()
            if (selectedIndex >= 0 && selectedIndex < results.length) {
                navigateToTicker(results[selectedIndex].symbol)
            } else if (results.length > 0) {
                // Navigate to first result
                navigateToTicker(results[0].symbol)
            }
        } else if (e.key === "Escape") {
            setShowDropdown(false)
            setSelectedIndex(-1)
        }
    }, [results, selectedIndex, navigateToTicker])

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowDropdown(false)
                setSelectedIndex(-1)
            }
        }

        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    return (
        <div className="relative" ref={dropdownRef}>
            <div className="relative group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                <Input
                    type="search"
                    value={query}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => {
                        if (results.length > 0) setShowDropdown(true)
                    }}
                    placeholder="Search tickers... (e.g., AAPL or Apple)"
                    className="w-[200px] md:w-[300px] pl-9 pr-9 bg-muted/50 border-border/50 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
                />
                {loading && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
            </div>

            {/* Dropdown */}
            {showDropdown && results.length > 0 && (
                <div className="absolute top-full mt-2 w-full bg-popover border border-border rounded-md shadow-lg z-50 max-h-[400px] overflow-y-auto">
                    {results.map((result, index) => (
                        <button
                            key={result.symbol}
                            onClick={() => navigateToTicker(result.symbol)}
                            className={`w-full px-3 py-2.5 flex items-center gap-3 hover:bg-accent transition-colors text-left ${index === selectedIndex ? "bg-accent" : ""
                                }`}
                        >
                            {/* Logo */}
                            {result.logo_url ? (
                                <img
                                    src={result.logo_url}
                                    alt={result.name}
                                    className="w-8 h-8 rounded-md object-contain bg-white"
                                    onError={(e) => {
                                        // Fallback to placeholder on error
                                        e.currentTarget.style.display = "none"
                                    }}
                                />
                            ) : (
                                <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center">
                                    <span className="text-xs font-bold text-muted-foreground">
                                        {result.symbol.charAt(0)}
                                    </span>
                                </div>
                            )}

                            {/* Symbol and Name */}
                            <div className="flex-1 min-w-0">
                                <div className="font-semibold text-sm">{result.symbol}</div>
                                <div className="text-xs text-muted-foreground truncate">
                                    {result.name}
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}
