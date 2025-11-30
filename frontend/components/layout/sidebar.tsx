"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, TrendingUp, Bookmark, User, Settings, Sparkles, MessageSquare } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { GradientText } from "@/components/ui/gradient-text"

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname()

  const routes = [
    {
      label: "Feed",
      icon: Home,
      href: "/",
      active: pathname === "/",
    },
    {
      label: "Trending",
      icon: TrendingUp,
      href: "/trending",
      active: pathname === "/trending",
    },
    {
      label: "Chat",
      icon: MessageSquare,
      href: "/chat",
      active: pathname === "/chat",
    },
    {
      label: "Bookmarks",
      icon: Bookmark,
      href: "/bookmarks",
      active: pathname === "/bookmarks",
    },
    {
      label: "Profile",
      icon: User,
      href: "/profile",
      active: pathname === "/profile",
    },
    {
      label: "Settings",
      icon: Settings,
      href: "/settings",
      active: pathname === "/settings",
    },
  ]

  return (
    <div className={cn("pb-12", className)}>
      <div className="space-y-4 py-4">
        {/* Brand Logo */}
        <div className="px-3 py-2">
          <div className="flex items-center gap-2 px-4 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 via-slate-500 to-blue-600 shadow-lg shadow-blue-500/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <GradientText className="text-lg font-bold">
                Stock Insights
              </GradientText>
              <p className="text-[10px] text-muted-foreground">AI-Powered Analysis</p>
            </div>
          </div>

          {/* Navigation */}
          <div className="space-y-1">
            {routes.map((route) => (
              <Button
                key={route.href}
                variant="ghost"
                asChild
                className={cn(
                  "w-full justify-start gap-3 h-12 text-base font-medium transition-all hover:scale-[1.02]",
                  route.active 
                    ? "bg-gradient-to-r from-blue-500/10 to-slate-500/10 text-primary border-l-4 border-primary shadow-sm" 
                    : "hover:bg-muted/50 border-l-4 border-transparent"
                )}
              >
                <Link href={route.href}>
                  <route.icon className={cn(
                    "h-5 w-5",
                    route.active && "text-primary"
                  )} />
                  <span>{route.label}</span>
                </Link>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
