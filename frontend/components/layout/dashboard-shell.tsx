import { Header } from "./header"
import { Sidebar } from "./sidebar"
import { MarketSidebar } from "./market-sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"

interface DashboardShellProps {
  children: React.ReactNode
}

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <div className="flex min-h-screen flex-col relative">
      {/* Subtle animated background */}
      <div className="fixed inset-0 -z-10 bg-background">
        <div className="absolute inset-0 bg-grid opacity-[0.02]"></div>
      </div>
      
      <Header />
      <div className="container flex-1 items-start md:grid md:grid-cols-[220px_minmax(0,1fr)_240px] md:gap-6 lg:grid-cols-[240px_minmax(0,1fr)_280px] lg:gap-10">
        <aside className="fixed top-14 z-30 -ml-2 hidden h-[calc(100vh-3.5rem)] w-full shrink-0 md:sticky md:block">
          <ScrollArea className="h-full py-6 pr-6 lg:py-8">
            <Sidebar />
          </ScrollArea>
        </aside>
        <main className="flex w-full flex-col overflow-hidden py-6 lg:py-8">
          {children}
        </main>
        <aside className="fixed top-14 z-30 hidden h-[calc(100vh-3.5rem)] w-full shrink-0 md:sticky md:block">
          <ScrollArea className="h-full py-6 pl-6 lg:py-8">
            <MarketSidebar />
          </ScrollArea>
        </aside>
      </div>
    </div>
  )
}
