import { cn } from "@/lib/utils"
import { Card } from "@/components/ui/card"

interface GradientCardProps {
  children: React.ReactNode
  className?: string
  glassEffect?: boolean
  hoverGlow?: boolean
}

export function GradientCard({ 
  children, 
  className, 
  glassEffect = false,
  hoverGlow = false 
}: GradientCardProps) {
  return (
    <div className={cn(
      "relative rounded-xl p-[1px]",
      "bg-gradient-to-br from-violet-500 via-pink-500 to-blue-500",
      hoverGlow && "hover:shadow-[0_0_30px_rgba(124,58,237,0.5)] transition-shadow duration-300"
    )}>
      <Card className={cn(
        "bg-card",
        glassEffect && "glass-card",
        className
      )}>
        {children}
      </Card>
    </div>
  )
}




