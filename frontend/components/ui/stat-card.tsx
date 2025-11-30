'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: number
  icon: LucideIcon
  change?: number
  className?: string
  animate?: boolean
}

export function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  change,
  className,
  animate = true 
}: StatCardProps) {
  const [displayValue, setDisplayValue] = useState(animate ? 0 : value)

  useEffect(() => {
    if (!animate) return

    const duration = 1500
    const steps = 60
    const increment = value / steps
    let current = 0

    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplayValue(value)
        clearInterval(timer)
      } else {
        setDisplayValue(Math.floor(current))
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [value, animate])

  return (
    <Card className={cn("card-hover", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-2">{displayValue.toLocaleString()}</p>
            {change !== undefined && (
              <p className={cn(
                "text-sm mt-1 font-medium",
                change >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
              )}>
                {change >= 0 ? '+' : ''}{change}%
              </p>
            )}
          </div>
          <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-slate-500">
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}




