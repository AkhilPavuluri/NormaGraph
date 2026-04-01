'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function ApiReferencePage() {
  return (
    <DocShell
      title="API reference"
      subtitle="Standard FastAPI application: backend.api.main. Interactive schema at /docs when the server is running."
    >
      <div className="space-y-12">
        <DocSection title="Base URL">
          <p>
            Default: <code>http://localhost:8000</code> (no <code>/api/v1</code> prefix). CORS and port follow your{' '}
            <code>.env</code>.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Routes">
          <ul>
            <li>
              <code>GET /</code> — service JSON (name, version, status)
            </li>
            <li>
              <code>GET /health</code> — liveness; Orchestrator and component flags
            </li>
            <li>
              <code>GET /status</code> — version and advertised route map (lightweight metadata)
            </li>
            <li>
              <code>POST /query</code> — non-streaming query; body matches <code>QueryRequest</code>
            </li>
            <li>
              <code>POST /query/stream</code> — streaming query (SSE-style events)
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Request body (POST /query and POST /query/stream)">
          <pre>{`{
  "query": "string (required, 1–1000 chars)",
  "conversation_history": [ { "role": "...", "content": "..." } ] | null,
  "filters": { } | null
}`}</pre>
          <p>
            <code>POST /query</code> returns a complete JSON response. <code>POST /query/stream</code> uses the same body and
            returns a text/event-stream (SSE) of status and token events.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Orchestrator API (separate process)">
          <p>
            <code>normagraph_core.api.main</code> is typically run on another port (e.g. <code>8001</code>). Use that
            service&apos;s own OpenAPI or module docs for streaming orchestration endpoints.
          </p>
        </DocSection>
      </div>
    </DocShell>
  )
}
