import { useState } from 'react'
import { retrieve } from '../api.js'

const BASE_VARIANTS = ['dense', 'fts', 'hybrid']
const LABELS = {
  dense: 'Dense (vector)',
  fts: 'FTS (keyword)',
  hybrid: 'Hybrid (RRF)',
  hybrid_reranked: 'Hybrid + rerank',
}

function Column({ label, rows }) {
  return (
    <div className="column">
      <h3>{label}</h3>
      {(!rows || rows.length === 0) && <p className="muted">No results.</p>}
      {rows &&
        rows.map((r, i) => (
          <div className="hit" key={`${r.chunk_id}-${i}`}>
            <div className="hit-head">
              <span className="mono">{r.metadata?.section_ref || r.chunk_id}</span>
              {r.score != null && <span className="score">{r.score.toFixed(3)}</span>}
            </div>
            <div className="hit-act">{r.metadata?.act || ''}</div>
            <div className="hit-text">{r.text}</div>
          </div>
        ))}
    </div>
  )
}

export default function Retrieval() {
  const [q, setQ] = useState('')
  const [k, setK] = useState(5)
  const [rerank, setRerank] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  async function run(e) {
    e?.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    setError(null)
    try {
      setData(await retrieve(q, k, rerank))
    } catch (err) {
      setError(err.message)
      setData(null)
    } finally {
      setBusy(false)
    }
  }

  const columns = data ? [...BASE_VARIANTS, ...(data.variants.hybrid_reranked ? ['hybrid_reranked'] : [])] : []

  return (
    <div className="panel">
      <h2>Retrieval</h2>
      <p className="muted">Compare dense, keyword (FTS), and hybrid retrieval for the same query.</p>

      <form className="query-bar" onSubmit={run}>
        <input
          type="text"
          value={q}
          placeholder="e.g. how long does a landlord have to refund a deposit?"
          onChange={(e) => setQ(e.target.value)}
        />
        <label className="k-field">
          top-k
          <input type="number" min="1" max="20" value={k} onChange={(e) => setK(Number(e.target.value))} />
        </label>
        <label className="rerank-field">
          <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
          rerank
        </label>
        <button className="primary" disabled={busy || !q.trim()}>
          {busy ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {data && (
        <div className="columns">
          {columns.map((key) => (
            <Column key={key} label={LABELS[key]} rows={data.variants[key]} />
          ))}
        </div>
      )}
    </div>
  )
}
