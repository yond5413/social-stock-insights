"use client"

import { useState } from "react"
import { PenSquare, X, Loader2, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { useApi } from "@/hooks/useApi"

interface CreatePostDialogProps {
  onPostCreated: () => void
}

export function CreatePostDialog({ onPostCreated }: CreatePostDialogProps) {
  const { apiRequest } = useApi()
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState("")
  const [tickerInput, setTickerInput] = useState("")
  const [tickers, setTickers] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleAddTicker = () => {
    const trimmed = tickerInput.trim().toUpperCase()
    if (trimmed && !tickers.includes(trimmed)) {
      setTickers([...tickers, trimmed])
    }
    setTickerInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      handleAddTicker()
    }
  }

  const removeTicker = (tickerToRemove: string) => {
    setTickers(tickers.filter((t) => t !== tickerToRemove))
  }

  const handleSubmit = async () => {
    if (!content.trim()) return
    
    setLoading(true)
    try {
      await apiRequest("/posts/create", {
        method: "POST",
        body: JSON.stringify({
          content,
          tickers,
        }),
      })
      onPostCreated()
      setOpen(false)
      setContent("")
      setTickers([])
    } catch (error) {
      console.error("Failed to create post:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="w-full gap-2 sm:w-auto">
          <PenSquare className="h-4 w-4" />
          Create Insight
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Share Market Insight</DialogTitle>
          <DialogDescription>
            Post your analysis. AI will tag sectors and sentiment automatically.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="content">Insight</Label>
            <Textarea
              id="content"
              placeholder="What's your thesis? e.g., 'NVDA showing strong support at $480...'"
              className="h-32 resize-none"
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tickers">Tickers</Label>
            <div className="flex gap-2">
              <Input
                id="tickers"
                placeholder="Type ticker and press Enter (e.g. AAPL)"
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <Button
                type="button"
                variant="secondary"
                size="icon"
                onClick={handleAddTicker}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {tickers.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {tickers.map((ticker) => (
                  <Badge key={ticker} variant="secondary" className="gap-1">
                    {ticker}
                    <button
                      onClick={() => removeTicker(ticker)}
                      className="ml-1 rounded-full hover:bg-muted-foreground/20"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} disabled={loading || !content.trim()}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Post Insight
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


