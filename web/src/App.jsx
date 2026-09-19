import { useState } from 'react'
import Ingestion from './views/Ingestion.jsx'
import Retrieval from './views/Retrieval.jsx'
import Evaluation from './views/Evaluation.jsx'
import ProofViewer from './views/ProofViewer.jsx'
import { ScaleCheckIcon } from './components/icons.jsx'

const TABS = [
  { id: 'ingestion', label: 'Ingestion', render: () => <Ingestion /> },
  { id: 'retrieval', label: 'Retrieval', render: () => <Retrieval /> },
  { id: 'proof', label: 'Proof viewer', render: () => <ProofViewer /> },
  { id: 'evaluation', label: 'Evaluation', render: () => <Evaluation /> },
]

export default function App() {
  const [active, setActive] = useState('ingestion')
  const tab = TABS.find((t) => t.id === active)

  return (
    <div className="canvas-grid min-h-screen">
      <header className="border-b border-line bg-canvas/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 pt-6">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-weak text-primary">
            <ScaleCheckIcon className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold leading-tight tracking-tight">Legal-RAG</h1>
            <p className="text-xs text-muted">Answers checked against their source before you see them</p>
          </div>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-6 pt-4">
          {TABS.map((t) => {
            const on = t.id === active
            return (
              <button
                key={t.id}
                onClick={() => setActive(t.id)}
                className={`relative px-3 py-2.5 text-sm font-medium transition-colors ${
                  on ? 'text-ink' : 'text-muted hover:text-ink'
                }`}
              >
                {t.label}
                <span
                  className={`absolute inset-x-2 -bottom-px h-0.5 rounded-full transition-colors ${
                    on ? 'bg-primary' : 'bg-transparent'
                  }`}
                />
              </button>
            )
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">{tab.render()}</main>
    </div>
  )
}
