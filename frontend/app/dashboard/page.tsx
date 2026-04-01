'use client'

import { AppSidebar } from '@/components/app-sidebar'
import { ChartAreaInteractive } from '@/components/chart-area-interactive'
import { DataTable } from '@/components/data-table'
import { SectionCards } from '@/components/section-cards'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'

import { dashboardSampleData } from './sample-data'

export default function Page() {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <AppSidebar variant="inset" />
        <SidebarInset>
          <SiteHeader />
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-y-contain">
              <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                <header className="mb-8 border-b border-border/60 pb-8">
                  <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">NormaGraph</p>
                  <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Analytics</h1>
                  <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
                    Illustrative metrics and sample tables — replace with real telemetry when you connect observability and
                    product analytics.
                  </p>
                </header>

                <div className="flex flex-col gap-6 md:gap-8">
                  <SectionCards />
                  <ChartAreaInteractive />
                  <DataTable data={dashboardSampleData} />
                </div>
              </div>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  )
}
