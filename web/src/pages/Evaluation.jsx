import { useEffect, useState } from 'react'
import { evaluation, embeddingMap } from '../api.js'
import Banner from '../components/Banner.jsx'
import Card, { CardHeader, PageHeader } from '../components/Card.jsx'
import EmbeddingScatter from '../components/EmbeddingScatter.jsx'
import { FileIcon } from '../components/icons.jsx'

function pct(x) {
  return x == null ? '—' : `${(x * 100).toFixed(1)}%`
}

// Four different measures, so four different hues rather than four cards in
// the page accent — colour here distinguishes *which metric*, and carrying one
// hue per metric down a long list of runs makes a column scannable. Drawn from
// the categorical data palette, not the status colors: a low precision is not
// a "warning". The hue marks the tile (top rule + dot); the number itself
// stays ink, since some data hues are below 4.5:1 as text on white.
const METRICS = [
  ['precision', 'Precision', 'var(--color-data-1)'],
  ['recall', 'Recall', 'var(--color-data-6)'],
  ['f1', 'F1', 'var(--color-data-4)'],
  ['retrieval_rate', 'Retrieval rate', 'var(--color-data-5)'],
]

function RunCard({ run }) {
  const agg = run.results?.aggregate
  const cfg = run.config || {}
  return (
    <Card tone="flat">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-sm text-accent">{run.name}</h3>
        <span className="text-xs text-muted">
          {cfg.mode ?? '?'} · rerank {String(cfg.use_reranker ?? '?')} · k{cfg.k ?? '?'}/N{cfg.n ?? '?'}
        </span>
      </div>
      {agg ? (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {METRICS.map(([key, label, hue]) => (
            <div
              key={key}
              style={{ borderTopColor: hue }}
              className="rounded-lg border-t-2 bg-surface px-3 py-2.5"
            >
              <div className="font-mono text-xl text-ink">{pct(agg[key])}</div>
              <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted">
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: hue }}
                  aria-hidden
                />
                {label}
              </div>
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
      <PageHeader
        title="Evaluation"
        subtitle="The embedding space the retriever searches, and metrics from logged evaluation runs."
      />
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
              Log one with <span className="font-mono text-ink">python -m src.evaluation.run_retrieval_eval</span>, then reload.
            </p>
          </div>
        )}
      </Card>

      {state.data && state.data.runs.map((run) => <RunCard key={run.name} run={run} />)}
    </div>
  )
}
