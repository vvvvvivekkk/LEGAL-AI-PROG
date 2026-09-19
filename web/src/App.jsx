import { useState } from 'react'
import Ingestion from './views/Ingestion.jsx'
import Retrieval from './views/Retrieval.jsx'
import Evaluation from './views/Evaluation.jsx'
import ProofViewer from './views/ProofViewer.jsx'

const TABS = [
  { id: 'ingestion', label: 'Ingestion', render: () => <Ingestion /> },
  { id: 'retrieval', label: 'Retrieval', render: () => <Retrieval /> },
  { id: 'evaluation', label: 'Evaluation', render: () => <Evaluation /> },
  { id: 'proof', label: 'Proof viewer', render: () => <ProofViewer /> },
]

export default function App() {
  const [active, setActive] = useState('ingestion')
  const tab = TABS.find((t) => t.id === active)

  return (
    <div className="app">
      <header className="topbar">
        <h1>Legal-RAG</h1>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={t.id === active ? 'tab active' : 'tab'}
              onClick={() => setActive(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="content">{tab.render()}</main>
    </div>
  )
}
