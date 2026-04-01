'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function UserGuidePage() {
  return (
    <DocShell
      title="Analysis UI"
      subtitle="How the chat and analysis views interact with the backend when services are configured."
    >
      <div className="space-y-12">
        <DocSection title="Queries">
          <p>
            Open <strong>Analysis</strong> from the app navigation. Enter questions in natural language. Responses are
            grounded in retrieved context when the backend and corpus are available; otherwise you may see placeholders or
            simplified paths.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Citations and sources">
          <p>
            When the API returns citations, the UI can surface them with the answer. PDF or document links depend on your
            storage and viewer configuration.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Feedback">
          <p>
            Thumbs and optional comments are stored <strong>in the browser</strong> (local storage) in this build — not sent
            to a dedicated feedback API by default. Treat ratings as local notes unless you wire a backend endpoint.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Authentication">
          <p>
            Sign-in flows may use a <strong>mock</strong> Firebase layer for local runs. Production-grade auth is not the
            focus of this reference implementation.
          </p>
        </DocSection>
      </div>
    </DocShell>
  )
}
