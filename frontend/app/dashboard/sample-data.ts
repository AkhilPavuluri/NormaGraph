import type { z } from 'zod'

import { schema } from '@/components/data-table'

/** Illustrative table rows for the analytics dashboard (replace with API data later). */
export const dashboardSampleData: z.infer<typeof schema>[] = [
  {
    id: 1,
    header: 'Sample policy review',
    type: 'Document',
    status: 'Done',
    target: '18',
    limit: '24',
    reviewer: 'Demo',
  },
  {
    id: 2,
    header: 'Cross-domain check',
    type: 'Query',
    status: 'In Progress',
    target: '12',
    limit: '18',
    reviewer: 'Demo',
  },
]
