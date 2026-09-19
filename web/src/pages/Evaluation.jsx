import { useEffect, useState } from 'react'
import { evaluation, embeddingMap } from '../api.js'
import Banner from '../components/Banner.jsx'
import Card, { CardHeader } from '../components/Card.jsx'
import EmbeddingScatter from '../components/EmbeddingScatter.jsx'
import { FileIcon } from '../components/icons.jsx'

function pct(x) {
  return x == null ? '—' : `${(x * 100).toFixed(1)}%`
}

const METRICS = [
  ['precision', 'Precision'],
  ['recall', 'Recall'],
  ['f1', 'F1'],
  ['retrieval_rate', 'Retrieval rate'],
]

function RunCard({ run }) {
  const agg = run.results?.aggregate
  const cfg = run.config || {}
  return (
    <Card tone="flat">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-sm text-ink">{run.name}</h3>
        <span className="text-xs text-muted">
          {cfg.mode ?? '?'} · rerank {String(cfg.use_reranker ?? '?')} · k{cfg.k ?? '?'}/N{cfg.n ?? '?'}
        </span>
      </div>
      {agg ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {METRICS.map(([key, label]) => (
            <div key={key} className="rounded-lg border border-line-soft bg-raised px-3 py-2.5">
              <div className="font-mono text-xl text-ink">{pct(agg[key])}</div>
              <div className="mt-0.5 text-[11px] text-muted">{label}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted">No aggregate metrics recorded for this run.</p>
      )}
      {agg?.n_queries != null && (
        <p className="mt-3 text-xs text-faint">Over {agg.n_queries} labeled queries.</p>
      )}
    </Card>
  )
}

export default function Evaluation() {
  const [state, setState] = useState({ loading: true, error: null, data: null })
  const [map, setMap] = useState(null)

  useEffect(() => {
    let alive = true
    evaluation()
      .then((data) => alive && setState({ loading: false, error: null, data }))
      .catch((err) => alive && setState({ loading: false, error: err.message, data: null }))
    embeddingMap()
      .then((m) => alive && setMap(m))
      .catch(() => alive && setMap({ points: [], sources: [] }))
    return () => {
      alive = false
    }
  }, [])

  const empty = state.data && state.data.runs.length === 0

  return (
    <div className="space-y-6">
      <Card tone="input">
        <CardHeader
          icon={FileIcon}
          title="Embedding space"
          subtitle="Every indexed chunk projected to 2D with PCA, colored by source document — the vector space the retriever searches, made visible."
        />
        {map ? (
          <EmbeddingScatter points={map.points} sources={map.sources} />
        ) : (
          <p className="text-sm text-muted">Loading embedding map…</p>
        )}
      </Card>

      <Card tone="input">
        <CardHeader
          icon={FileIcon}
          title="Retrieval evaluation"
          subtitle="Precision, recall, F1, and retrieval rate from logged runs under /experiments."
        />
        {state.loading && <p className="text-sm text-muted">Loading runs…</p>}
        {state.error && <Banner variant="error" title="Could not load runs">{state.error}</Banner>}
        {empty && (
          <div className="rounded-lg border border-dashed border-line px-5 py-8 text-center">
            <p className="text-sm text-ink">{state.data.message || 'No evaluation runs yet.'}</p>
            <p className="mx-auto mt-2 max-w-md text-xs text-muted">
              Log one with <span className="font-mono text-faint">python -m src.evaluation.run_retrieval_eval</span>, then reload.
            </p>
          </div>
        )}
      </Card>

      {state.data && state.data.runs.map((run) => <RunCard key={run.name} run={run} />)}
    </div>
  )
}
