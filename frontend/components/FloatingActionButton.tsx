'use client'

import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'

interface FloatingActionButtonProps {
  onClick: () => void
  label?: string
}

export function FloatingActionButton({ onClick, label = 'Open Draft' }: FloatingActionButtonProps) {
  return (
    <Button
      onClick={onClick}
      className="fixed right-6 top-1/2 -translate-y-1/2 z-40
                 h-12 px-4 gap-2 shadow-lg
                 bg-primary hover:bg-primary/90
                 text-primary-foreground
                 rounded-full
                 transition-all duration-300
                 hover:scale-105
                 focus:ring-2 focus:ring-primary focus:ring-offset-2"
      aria-label={label}
      title={label}
    >
      <FileText className="h-4 w-4" />
      <span className="hidden sm:inline">{label}</span>
    </Button>
  )
}




