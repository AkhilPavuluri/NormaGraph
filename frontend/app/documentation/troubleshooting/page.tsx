'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function TroubleshootingPage() {
  return (
    <DocShell
      title="Troubleshooting"
      subtitle="Common checks when something does not connect or return data."
    >
      <div className="space-y-12">
        <DocSection title="Backend">
          <ul>
            <li>
              Confirm the process is listening (e.g. <code>python -m backend</code> or <code>normagraph-api</code>) and{' '}
              <code>GET /health</code> responds.
            </li>
            <li>
              <code>ModuleNotFoundError: backend</code> — run commands from the <strong>repository root</strong>, or use{' '}
              <code>pip install -e .</code>.
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Frontend">
          <ul>
            <li>
              <code>npm run dev</code> should serve <code>localhost:3000</code>. If the UI cannot reach the API, verify{' '}
              <code>NEXT_PUBLIC_API_URL</code> matches your backend URL.
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Retrieval and cloud">
          <ul>
            <li>
              Empty or error responses often indicate missing Qdrant, BigQuery, or credentials — check logs and{' '}
              <code>.env</code>.
            </li>
            <li>
              Timeouts: the API may enforce limits on long-running queries; see server logs.
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Local models (Ollama)">
          <p>
            Optional local models appear in the UI when Ollama is reachable. If not installed, those entries stay
            unavailable — cloud models depend on keys in settings and <code>.env</code>.
          </p>
        </DocSection>
      </div>
    </DocShell>
  )
}
