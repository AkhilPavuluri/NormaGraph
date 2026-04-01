'use client'

import Link from 'next/link'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'

const SECTIONS = [
  {
    href: '/documentation/getting-started',
    title: 'Getting started',
    description: 'Python and Node setup, run commands, environment file.',
  },
  {
    href: '/documentation/user-guide',
    title: 'Analysis UI',
    description: 'Query flow, citations, and feedback behavior.',
  },
  {
    href: '/documentation/approaches',
    title: 'Architecture notes',
    description: 'Ingestion, Decision Graph, Orchestrator, and retrieval posture.',
  },
  {
    href: '/documentation/api-reference',
    title: 'API reference',
    description: 'Standard backend routes, OpenAPI, streaming.',
  },
  {
    href: '/documentation/administration',
    title: 'Configuration',
    description: 'Environment variables and integration scope.',
  },
  {
    href: '/documentation/troubleshooting',
    title: 'Troubleshooting',
    description: 'Connectivity, models, and retrieval checks.',
  },
  {
    href: '/documentation/developer-resources',
    title: 'Developer resources',
    description: 'Repository layout, CLI, and CI expectations.',
  },
] as const

export default function DocumentationPage() {
  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false}>
        <SidebarInset className="bg-background">
          <SiteHeader />
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-y-contain">
            <div className="border-b border-border/60 bg-muted/10">
              <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8 sm:py-16 lg:px-10">
                <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.22em] text-muted-foreground">
                  NormaGraph
                </p>
                <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                  Documentation
                </h1>
                <p className="mt-4 max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-[15px]">
                  Decision Graph for Policy Intelligence — how to run the stack, what the API exposes, and how the
                  analysis UI relates to the backend.
                </p>
              </div>
            </div>

            <div className="mx-auto w-full max-w-5xl shrink-0 px-6 py-10 sm:px-8 sm:py-12 lg:px-10">
              <nav
                aria-label="Documentation sections"
                className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 xl:grid-cols-3"
              >
                {SECTIONS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group flex min-h-[7.5rem] flex-col rounded-xl border border-border/70 bg-card/45 p-5 transition-colors hover:border-primary/25 hover:bg-muted/35 sm:min-h-[8rem] sm:p-6"
                  >
                    <span className="text-sm font-semibold tracking-tight text-foreground group-hover:text-primary">
                      {item.title}
                    </span>
                    <p className="mt-2 flex-1 text-xs leading-relaxed text-muted-foreground sm:text-[13px]">
                      {item.description}
                    </p>
                    <span className="mt-4 text-[11px] font-medium text-muted-foreground/80 transition-colors group-hover:text-primary">
                      View →
                    </span>
                  </Link>
                ))}
              </nav>

              <div className="mt-10 rounded-xl border border-border/60 bg-muted/20 p-5 sm:p-6 lg:p-8">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-foreground/70">Run modes</p>
                <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-muted-foreground sm:text-xs">
                  {`# Standard API (repo root)
python -m backend
# or: normagraph-api  (after pip install -e .)

# Streaming / orchestrator API
uvicorn normagraph_core.api.main:app --port 8001 --reload

# Frontend
cd frontend && npm install && npm run dev`}
                </pre>
                <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                  Interactive HTTP docs for the standard API: <code className="rounded border border-border/60 bg-background px-1.5 py-0.5 font-mono text-[11px]">GET /docs</code> when the backend is running (default port <code className="rounded border border-border/60 bg-background px-1.5 py-0.5 font-mono text-[11px]">8000</code>).
                </p>
              </div>

              <p className="mt-10 max-w-3xl text-center text-[11px] leading-relaxed text-muted-foreground/80 sm:mx-auto">
                Early-stage reference implementation. Full behavior depends on configured services and corpus.
              </p>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  )
}
