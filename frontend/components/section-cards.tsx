import { TrendingDownIcon, TrendingUpIcon } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

export function SectionCards() {
  return (
    <div className="*:data-[slot=card]:shadow-xs @xl/main:grid-cols-2 @5xl/main:grid-cols-4 grid grid-cols-1 gap-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card">
      <Card className="@container/card" data-slot="card">
        <CardHeader className="relative">
          <CardDescription>Queries (7d)</CardDescription>
          <CardTitle className="@[250px]/card:text-3xl text-2xl font-semibold tabular-nums">
            1,248
          </CardTitle>
          <div className="absolute right-4 top-4">
            <Badge variant="outline" className="flex gap-1 rounded-lg text-xs">
              <TrendingUpIcon className="size-3" />
              +8.2%
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Up vs prior week <TrendingUpIcon className="size-4" />
          </div>
          <div className="text-muted-foreground">Decision Graph–backed analysis sessions (demo)</div>
        </CardFooter>
      </Card>
      <Card className="@container/card" data-slot="card">
        <CardHeader className="relative">
          <CardDescription>Citations linked</CardDescription>
          <CardTitle className="@[250px]/card:text-3xl text-2xl font-semibold tabular-nums">
            3.4
          </CardTitle>
          <div className="absolute right-4 top-4">
            <Badge variant="outline" className="flex gap-1 rounded-lg text-xs">
              <TrendingUpIcon className="size-3" />
              +0.3
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Avg. per answer <TrendingUpIcon className="size-4" />
          </div>
          <div className="text-muted-foreground">When the backend returns structured citations (demo)</div>
        </CardFooter>
      </Card>
      <Card className="@container/card" data-slot="card">
        <CardHeader className="relative">
          <CardDescription>p50 latency</CardDescription>
          <CardTitle className="@[250px]/card:text-3xl text-2xl font-semibold tabular-nums">
            1.2s
          </CardTitle>
          <div className="absolute right-4 top-4">
            <Badge variant="outline" className="flex gap-1 rounded-lg text-xs">
              <TrendingDownIcon className="size-3" />
              −0.2s
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            End-to-end query <TrendingDownIcon className="size-4" />
          </div>
          <div className="text-muted-foreground">Orchestrator path — illustrative (demo)</div>
        </CardFooter>
      </Card>
      <Card className="@container/card" data-slot="card">
        <CardHeader className="relative">
          <CardDescription>Indexed documents</CardDescription>
          <CardTitle className="@[250px]/card:text-3xl text-2xl font-semibold tabular-nums">
            482
          </CardTitle>
          <div className="absolute right-4 top-4">
            <Badge variant="outline" className="flex gap-1 rounded-lg text-xs">
              <TrendingUpIcon className="size-3" />
              +24
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Corpus size <TrendingUpIcon className="size-4" />
          </div>
          <div className="text-muted-foreground">Depends on your ingestion pipeline (demo)</div>
        </CardFooter>
      </Card>
    </div>
  )
}
