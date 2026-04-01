'use client'

import { Network } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Icon-only mark (no raster logo) — NormaGraph / graph intelligence. */
export function BrandMark({ className, iconClassName }: { className?: string; iconClassName?: string }) {
  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-lg border border-border bg-primary/10 text-primary',
        className
      )}
      aria-label="NormaGraph"
    >
      <Network className={cn('h-6 w-6 sm:h-7 sm:w-7 md:h-8 md:w-8', iconClassName)} strokeWidth={1.75} aria-hidden />
    </div>
  )
}
