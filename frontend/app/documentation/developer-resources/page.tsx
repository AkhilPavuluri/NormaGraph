'use client'

import { DocShell, DocSection, DocRule } from '@/components/documentation/doc-shell'

export default function DeveloperResourcesPage() {
  return (
    <DocShell
      title="Developer resources"
      subtitle="Repository layout, packaging, and validation commands."
    >
      <div className="space-y-12">
        <DocSection title="Layout">
          <ul>
            <li>
              <code>backend/</code> — FastAPI standard API, ingestion, retrieval, answering
            </li>
            <li>
              <code>normagraph_core/</code> — Orchestrator-oriented streaming API
            </li>
            <li>
              <code>frontend/</code> — Next.js UI
            </li>
            <li>
              <code>docs/</code> — design notes (e.g. runtime profiles)
            </li>
            <li>
              <code>data/</code> — optional document inventory metadata
            </li>
          </ul>
        </DocSection>

        <DocRule />

        <DocSection title="Python package">
          <p>
            <code>pyproject.toml</code> defines the <code>normagraph</code> package and the <code>normagraph-api</code>{' '}
            console script. Editable install: <code>pip install -e .</code>
          </p>
        </DocSection>

        <DocRule />

        <DocSection title="Scripts">
          <pre>{`# Frontend
cd frontend && npm run lint && npm run type-check && npm run build

# Tests (may skip without cloud)
pip install -r requirements.txt pytest
pytest normagraph_core/tests/ -q`}</pre>
        </DocSection>

        <DocRule />

        <DocSection title="CI">
          <p>
            GitHub Actions installs the package with <code>pip install -e .</code>, imports <code>backend</code> and{' '}
            <code>normagraph_core</code>, runs <code>compileall</code>, and builds the frontend — not full integration
            tests against live services.
          </p>
        </DocSection>
      </div>
    </DocShell>
  )
}
