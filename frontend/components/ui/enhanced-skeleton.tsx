import { cn } from "@/lib/utils"

interface EnhancedSkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  shimmer?: boolean
}

export function EnhancedSkeleton({ 
  className, 
  shimmer = true,
  ...props 
}: EnhancedSkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-md bg-muted",
        shimmer && "shimmer",
        className
      )}
      {...props}
    />
  )
}

export function PostSkeleton() {
  return (
    <div className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex items-center space-x-3">
        <EnhancedSkeleton className="h-12 w-12 rounded-full" />
        <div className="space-y-2">
          <EnhancedSkeleton className="h-4 w-[200px]" />
          <EnhancedSkeleton className="h-3 w-[150px]" />
        </div>
      </div>
      <EnhancedSkeleton className="h-[120px] w-full" />
      <div className="flex gap-2">
        <EnhancedSkeleton className="h-8 w-16 rounded-full" />
        <EnhancedSkeleton className="h-8 w-16 rounded-full" />
      </div>
    </div>
  )
}

export function FeedSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 3 }).map((_, i) => (
        <PostSkeleton key={i} />
      ))}
    </div>
  )
}



