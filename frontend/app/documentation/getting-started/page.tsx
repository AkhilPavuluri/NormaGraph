'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function GettingStartedPage() {
  return (
    <DocShell
      title="Getting started"
      subtitle="Install dependencies, configure environment variables, and run the backend, streaming API, and frontend from the repository root."
    >
      <div className="space-y-12">
        <DocSection title="Prerequisites">
          <ul>
            <li>
              <strong>Python</strong> 3.10+ (3.11 recommended for parity with CI)
            </li>
            <li>
              <strong>Node.js</strong> 18+ and npm
            </li>
            <li>
              <strong>Services</strong> for full query behavior: Google Cloud (as configured), Qdrant, and valid API keys — see <code>.env.example</code>
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Backend (standard API)">
          <p>From the repository root, with a virtual environment activated:</p>
          <pre>{`pip install -r requirements.txt
# or: pip install -e .

python -m backend`}</pre>
          <p>
            Equivalent: <code>uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload</code>. Port follows{' '}
            <code>PORT</code> in <code>.env</code>.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Streaming API (Orchestrator)">
          <pre>{`uvicorn normagraph_core.api.main:app --host 0.0.0.0 --port 8001 --reload`}</pre>
          <p>Use another port if needed. Point the frontend at the API you run via <code>NEXT_PUBLIC_API_URL</code>.</p>
        </DocSection>

        <DocRule />

        <DocSection title="Frontend">
          <pre>{`cd frontend
npm install
cp ../.env.example .env.local   # optional

npm run dev`}</pre>
          <p>
            App: <code>http://localhost:3000</code>. PDF.js worker may load from a CDN (see <code>frontend/components/PdfViewer</code>).
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Environment">
          <p>
            Copy <code>.env.example</code> to <code>.env</code> at the repo root. Grouped variables cover GCP, Qdrant, models, and{' '}
            <code>NEXT_PUBLIC_*</code> for the browser. Never commit secrets.
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="First checks">
          <ul>
            <li>
              <code>GET http://localhost:8000/health</code> — liveness; Orchestrator initialization
            </li>
            <li>
              <code>GET http://localhost:8000/docs</code> — OpenAPI (Swagger) for the standard API
            </li>
            <li>
              <code>GET http://localhost:8000/status</code> — lightweight service metadata
            </li>
          </ul>
        </DocSection>
      </div>
    </DocShell>
  )
}
