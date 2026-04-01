'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function AdministrationPage() {
  return (
    <DocShell
      title="Configuration"
      subtitle="Environment variables and integration boundaries for this repository."
    >
      <div className="space-y-12">
        <DocSection title="Environment file">
          <p>
            Use <code>.env.example</code> at the repository root as the template. Copy to <code>.env</code> and fill in
            GCP project, credentials path, <code>QDRANT_URL</code>, model keys, and frontend <code>NEXT_PUBLIC_*</code>{' '}
            values as required.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Groups (summary)">
          <ul>
            <li>
              <strong>Core API</strong> — <code>PORT</code>, <code>CORS_ORIGINS</code>
            </li>
            <li>
              <strong>Google Cloud</strong> — project, location, <code>GOOGLE_APPLICATION_CREDENTIALS</code>
            </li>
            <li>
              <strong>Gemini / Vertex</strong> — model names, API keys as applicable
            </li>
            <li>
              <strong>Qdrant</strong> — URL and API key
            </li>
            <li>
              <strong>NormaGraph core</strong> — orchestration flags, observability log path
            </li>
            <li>
              <strong>Frontend</strong> — <code>NEXT_PUBLIC_API_URL</code> and optional public keys for client-side model
              helpers
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Scope">
          <p>
            This build does not ship a full multi-tenant admin console or role system in the UI. Operational hardening
            (secrets management, SLAs, audit trails) is out of scope for the reference implementation.
          </p>
        </DocSection>
      </div>
    </DocShell>
  )
}
