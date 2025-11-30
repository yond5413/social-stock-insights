import { cn } from "@/lib/utils"

interface GradientTextProps {
  children: React.ReactNode
  className?: string
  animate?: boolean
}

export function GradientText({ children, className, animate = true }: GradientTextProps) {
  return (
    <span 
      className={cn(
        "bg-gradient-to-r from-blue-600 via-slate-600 to-blue-500 bg-clip-text text-transparent font-bold",
        animate && "bg-[length:200%_200%] animate-gradient-shift",
        className
      )}
    >
      {children}
    </span>
  )
}




