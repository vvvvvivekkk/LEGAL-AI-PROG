import { useEffect, useState } from 'react'
import { evaluation } from '../api.js'

function pct(x) {
  return x == null ? '—' : `${(x * 100).toFixed(1)}%`
}

function RunCard({ run }) {
  const agg = run.results?.aggregate
  const cfg = run.config || {}
  return (
    <div className="run-card">
      <h3 className="mono">{run.name}</h3>
      <div className="run-config muted">
        mode: {cfg.mode ?? '?'} · rerank: {String(cfg.use_reranker ?? '?')} · k: {cfg.k ?? '?'} · N: {cfg.n ?? '?'}
      </div>
      {agg ? (
        <table className="metrics">
          <thead>
            <tr>
              <th>Precision</th>
              <th>Recall</th>
              <th>F1</th>
              <th>Retrieval rate</th>
              <th>Queries</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{pct(agg.precision)}</td>
              <td>{pct(agg.recall)}</td>
              <td>{pct(agg.f1)}</td>
              <td>{pct(agg.retrieval_rate)}</td>
              <td>{agg.n_queries ?? '—'}</td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p className="muted">No aggregate metrics in this run.</p>
      )}
    </div>
  )
}

export default function Evaluation() {
  const [state, setState] = useState({ loading: true, error: null, data: null })

  useEffect(() => {
    let alive = true
    evaluation()
      .then((data) => alive && setState({ loading: false, error: null, data }))
      .catch((err) => alive && setState({ loading: false, error: err.message, data: null }))
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="panel">
      <h2>Evaluation</h2>
      <p className="muted">Retrieval-quality metrics from logged runs under /experiments.</p>

      {state.loading && <p className="muted">Loading…</p>}
      {state.error && <div className="error">{state.error}</div>}

      {state.data && state.data.runs.length === 0 && (
        <p className="muted">{state.data.message || 'No evaluation runs yet.'}</p>
      )}

      {state.data && state.data.runs.map((run) => <RunCard key={run.name} run={run} />)}
    </div>
  )
}
