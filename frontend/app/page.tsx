'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* Ambient depth — very subtle */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,hsl(var(--primary)/0.12),transparent)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_100%_100%,hsl(175_48%_38%/0.06),transparent)] dark:bg-[radial-gradient(ellipse_60%_40%_at_100%_100%,hsl(175_50%_45%/0.08),transparent)]" />
      </div>

      <main className="flex min-h-screen flex-col px-6 pb-8 pt-20 sm:px-10 sm:pb-10 sm:pt-28">
        <div className="flex flex-1 flex-col justify-center">
          <div className="mx-auto w-full max-w-2xl text-center">
            <p className="mb-8 text-[11px] font-medium uppercase tracking-[0.28em] text-muted-foreground sm:text-xs sm:tracking-[0.32em]">
              Decision Graph for Policy Intelligence
            </p>
            <h1 className="mb-8 text-5xl font-extralight tracking-tight text-foreground sm:text-6xl md:text-7xl md:tracking-tighter">
              NormaGraph
            </h1>
            <p className="mx-auto mb-12 max-w-lg text-base leading-relaxed text-muted-foreground sm:text-lg sm:leading-relaxed">
              Policy and regulatory text as structured{' '}
              <span className="text-foreground/90">Decision Graph</span> representations — hybrid retrieval,
              Orchestrator-mediated query paths, and source-grounded outputs.
            </p>

            <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-center sm:gap-8">
              <Button
                asChild
                size="lg"
                className="h-12 min-w-[200px] rounded-full px-10 text-base font-medium shadow-sm"
              >
                <Link href="/chat">Open analysis</Link>
              </Button>
              <Link
                href="/documentation"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                Documentation <span aria-hidden>→</span>
              </Link>
            </div>

            <div className="mx-auto mt-9 max-w-2xl border-t border-border/25 pt-6">
              <div className="grid gap-4 text-center sm:grid-cols-3 sm:gap-3">
                <div>
                  <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-foreground/45">
                    Ingestion
                  </p>
                  <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground/70">
                    Documents to structured units — pipelines and storage as configured in your environment.
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-foreground/45">
                    Decision Graph
                  </p>
                  <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground/70">
                    Clauses, authorities, and relationships as queryable structure — not flat text alone.
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-foreground/45">
                    Orchestrator
                  </p>
                  <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground/70">
                    Staged retrieval and generation with trace hooks — controlled execution over raw prompting.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <p className="mx-auto max-w-md shrink-0 pb-2 text-center text-[11px] leading-relaxed text-muted-foreground/70 sm:text-xs">
          Early-stage reference implementation. Full behavior depends on configured services and corpus; some UI paths may be simplified.
        </p>
      </main>
    </div>
  )
}
