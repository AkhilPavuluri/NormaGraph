'use client'

import Link from 'next/link'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { ChevronLeft } from 'lucide-react'

export function DocShell({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false}>
        <SidebarInset className="bg-background">
          <SiteHeader />
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-y-contain">
            <header className="shrink-0 border-b border-border/60 bg-muted/15">
              <div className="mx-auto max-w-3xl px-6 py-8 sm:py-10">
                <Link
                  href="/documentation"
                  className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
                >
                  <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
                  Documentation
                </Link>
                <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{title}</h1>
                {subtitle ? (
                  <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
                ) : null}
              </div>
            </header>
            <div className="mx-auto w-full max-w-3xl shrink-0 px-6 py-10 sm:py-14">{children}</div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  )
}

export function DocSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground/70">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-muted-foreground [&_strong]:font-medium [&_strong]:text-foreground/90 [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:space-y-1.5 [&_ol]:pl-5 [&_code]:rounded-md [&_code]:border [&_code]:border-border/60 [&_code]:bg-muted/50 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-border/60 [&_pre]:bg-muted/40 [&_pre]:p-4 [&_pre]:font-mono [&_pre]:text-xs">
        {children}
      </div>
    </section>
  )
}

export function DocRule() {
  return <div className="h-px w-full bg-border/70" role="separator" />
}
