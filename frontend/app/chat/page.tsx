"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { DashboardShell } from "@/components/layout/dashboard-shell"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  MessageSquare, 
  Send, 
  Sparkles, 
  TrendingUp, 
  TrendingDown,
  Trash2,
  Bot,
  User,
  Loader2,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { GradientText } from "@/components/ui/gradient-text"
import { staggerContainer, fadeInUp } from "@/lib/animations"
import { useChat, ChatMessage, TickerContext } from "@/hooks/use-chat"

// Suggested prompts for users
const SUGGESTED_PROMPTS = [
  "What's the community sentiment on NVDA?",
  "How is Tesla performing today?",
  "Compare Apple and Microsoft sentiment",
  "What are the trending stocks right now?",
  "Explain the recent movement in AMD",
]

function TickerContextCard({ context }: { context: TickerContext }) {
  const isPositive = (context.change_percent ?? 0) >= 0
  
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 border border-border/50">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-bold">${context.ticker}</span>
          {context.price && (
            <span className="text-sm text-muted-foreground">
              ${context.price.toFixed(2)}
            </span>
          )}
          {context.change_percent !== null && (
            <span className={cn(
              "text-sm font-medium flex items-center gap-0.5",
              isPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
            )}>
              {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {context.change_percent > 0 && "+"}
              {context.change_percent.toFixed(2)}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1">
          <Badge 
            variant="outline" 
            className={cn(
              "text-xs",
              context.sentiment === "bullish" ? "border-green-500/30 text-green-600" :
              context.sentiment === "bearish" ? "border-red-500/30 text-red-600" :
              "border-blue-500/30 text-blue-600"
            )}
          >
            {context.sentiment}
          </Badge>
          {context.post_count > 0 && (
            <span className="text-xs text-muted-foreground">
              {context.post_count} posts
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex gap-3 max-w-[85%]",
        isUser ? "ml-auto flex-row-reverse" : "mr-auto"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center",
        isUser 
          ? "bg-gradient-to-br from-blue-500 to-slate-500" 
          : "bg-gradient-to-br from-cyan-500 to-blue-500"
      )}>
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-white" />
        )}
      </div>
      
      {/* Message Content */}
      <div className={cn(
        "space-y-2",
        isUser ? "items-end" : "items-start"
      )}>
        <div className={cn(
          "rounded-2xl px-4 py-3",
          isUser 
            ? "bg-gradient-to-br from-blue-500 to-slate-500 text-white rounded-br-md" 
            : "bg-muted border border-border/50 rounded-bl-md"
        )}>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>
        
        {/* Ticker Context Cards */}
        {message.tickersContext && message.tickersContext.length > 0 && (
          <div className="space-y-2 w-full">
            {message.tickersContext.map(ctx => (
              <TickerContextCard key={ctx.ticker} context={ctx} />
            ))}
          </div>
        )}
        
        {/* Sources info */}
        {message.sourcesCount !== undefined && message.sourcesCount > 0 && (
          <p className="text-xs text-muted-foreground px-1">
            Based on {message.sourcesCount} community posts
          </p>
        )}
        
        {/* Timestamp */}
        <p className="text-xs text-muted-foreground px-1">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </motion.div>
  )
}

function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex gap-3 max-w-[85%] mr-auto"
    >
      <div className="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center bg-gradient-to-br from-cyan-500 to-blue-500">
        <Bot className="h-4 w-4 text-white" />
      </div>
      <div className="bg-muted border border-border/50 rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex gap-1">
          <motion.span
            className="w-2 h-2 bg-muted-foreground/50 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ repeat: Infinity, duration: 0.6, delay: 0 }}
          />
          <motion.span
            className="w-2 h-2 bg-muted-foreground/50 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ repeat: Infinity, duration: 0.6, delay: 0.15 }}
          />
          <motion.span
            className="w-2 h-2 bg-muted-foreground/50 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ repeat: Infinity, duration: 0.6, delay: 0.3 }}
          />
        </div>
      </div>
    </motion.div>
  )
}

export default function ChatPage() {
  const { messages, isLoading, error, sendMessage, clearChat, isAuthenticated } = useChat()
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    
    sendMessage(input)
    setInput("")
  }

  const handleSuggestedPrompt = (prompt: string) => {
    sendMessage(prompt)
  }

  return (
    <DashboardShell>
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="flex flex-col h-[calc(100vh-8rem)] max-h-[800px]"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 shadow-lg shadow-cyan-500/30">
              <MessageSquare className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                <GradientText>Stock Assistant</GradientText>
              </h1>
              <p className="text-sm text-muted-foreground">
                AI-powered insights with real-time data & community sentiment
              </p>
            </div>
          </div>
          
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-muted-foreground hover:text-foreground"
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </motion.div>

        {/* Chat Area */}
        <motion.div variants={fadeInUp} className="flex-1 min-h-0">
          <Card className="h-full glass-card border-border/50 flex flex-col">
            {/* Messages */}
            <ScrollArea className="flex-1 p-4" ref={scrollRef}>
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-8">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 mb-4">
                    <Sparkles className="h-8 w-8 text-cyan-500" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Ask me anything about stocks</h3>
                  <p className="text-sm text-muted-foreground mb-6 max-w-md">
                    I can provide real-time price data, community sentiment analysis, and help you understand market trends.
                  </p>
                  
                  {/* Suggested Prompts */}
                  <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                    {SUGGESTED_PROMPTS.map((prompt, i) => (
                      <Button
                        key={i}
                        variant="outline"
                        size="sm"
                        className="text-xs hover:bg-muted/50"
                        onClick={() => handleSuggestedPrompt(prompt)}
                      >
                        {prompt}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <AnimatePresence mode="popLayout">
                    {messages.map(message => (
                      <ChatBubble key={message.id} message={message} />
                    ))}
                  </AnimatePresence>
                  
                  <AnimatePresence>
                    {isLoading && <TypingIndicator />}
                  </AnimatePresence>
                </div>
              )}
            </ScrollArea>

            {/* Input Area */}
            <div className="p-4 border-t border-border/50">
              {error && (
                <div className="flex items-center gap-2 text-sm text-destructive mb-3 p-2 rounded-lg bg-destructive/10">
                  <AlertCircle className="h-4 w-4" />
                  {error}
                </div>
              )}
              
              <form onSubmit={handleSubmit} className="flex gap-2">
                <Input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about any stock... (e.g., What's the sentiment on $AAPL?)"
                  className="flex-1 bg-muted/50 border-border/50 focus-visible:ring-cyan-500/50"
                  disabled={isLoading}
                />
                <Button 
                  type="submit" 
                  disabled={!input.trim() || isLoading}
                  className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </form>
              
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Responses include real-time market data and community sentiment analysis
              </p>
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </DashboardShell>
  )
}



