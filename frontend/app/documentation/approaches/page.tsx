'use client'

import Link from 'next/link'
import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'
import { Button } from '@/components/ui/button'

export default function ApproachesPage() {
  return (
    <DocShell
      title="Architecture notes"
      subtitle="How ingestion, the Decision Graph, and the Orchestrator fit together — at a high level."
    >
      <div className="space-y-12">
        <DocSection title="Pipeline">
          <p>
            Documents move through <strong>ingestion</strong> into structured units, then into a <strong>Decision Graph</strong>{' '}
            representation (clauses, authorities, relationships). Queries run through an <strong>Orchestrator</strong> that
            combines retrieval, ranking, generation, and optional risk or citation stages — not a single opaque prompt over
            raw text.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Retrieval">
          <p>
            Hybrid retrieval (lexical + dense) and metadata filters are used where configured. Quality depends on embedding
            choice, indexing, and corpus coverage — not only on the chat model.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Runtime profiles">
          <p>
            Cloud-backed services (GCP, Qdrant) are the primary integration path in this tree. Broader local or hybrid
            provider profiles are described as forward architecture in the repo&apos;s <code>docs/runtime_profiles.md</code>.
          </p>
        </DocSection>

        <DocRule />

        <div className="flex flex-wrap gap-3">
          <Button asChild variant="outline" size="sm">
            <Link href="/architecture">Interactive architecture</Link>
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link href="/documentation">Documentation home</Link>
          </Button>
        </div>
      </div>
    </DocShell>
  )
}
