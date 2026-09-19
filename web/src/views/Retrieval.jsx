import { useState } from 'react'
import { retrieve } from '../api.js'
import Banner from '../components/Banner.jsx'
import Button from '../components/Button.jsx'
import Card, { CardHeader } from '../components/Card.jsx'
import { SearchIcon } from '../components/icons.jsx'

const BASE_VARIANTS = ['dense', 'fts', 'hybrid']
const LABELS = {
  dense: 'Dense · vector',
  fts: 'Lexical · keyword',
  hybrid: 'Hybrid · fused',
  hybrid_reranked: 'Hybrid · reranked',
}

function Hit({ row }) {
  return (
    <li className="border-t border-line-soft py-3 first:border-0 first:pt-0">
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-mono text-xs text-primary">{row.metadata?.section_ref || row.chunk_id}</span>
        {row.score != null && <span className="font-mono text-xs text-faint">{row.score.toFixed(3)}</span>}
      </div>
      {row.metadata?.act && <div className="mt-0.5 truncate text-xs text-muted">{row.metadata.act}</div>}
      <p className="mt-1 text-[13px] leading-relaxed text-ink/90">{row.text}</p>
    </li>
  )
}

function Column({ label, rows, highlight }) {
  return (
    <div className={`rounded-lg border p-4 ${highlight ? 'border-primary/40 bg-primary-weak/30' : 'border-line-soft bg-surface'}`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-ink">{label}</h3>
        <span className="font-mono text-[11px] text-faint">{rows?.length ?? 0}</span>
      </div>
      {!rows || rows.length === 0 ? (
        <p className="text-xs text-muted">No results.</p>
      ) : (
        <ul>{rows.map((r, i) => <Hit key={`${r.chunk_id}-${i}`} row={r} />)}</ul>
      )}
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

  const columns = data
    ? [...BASE_VARIANTS, ...(data.variants.hybrid_reranked ? ['hybrid_reranked'] : [])]
    : []

  return (
    <div className="space-y-6">
      <Card tone="input">
        <CardHeader
          icon={SearchIcon}
          title="Compare retrieval strategies"
          subtitle="The same query run three ways — vector, keyword, and fused hybrid — so you can see where each finds the right passage."
        />
        <form onSubmit={run} className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="How long does a landlord have to refund a deposit?"
            className="min-w-[240px] flex-1 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-faint focus:border-primary"
          />
          <label className="flex items-center gap-2 text-xs text-muted">
            top-k
            <input
              type="number"
              min="1"
              max="20"
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-16 rounded-lg border border-line bg-surface px-2.5 py-2 text-sm text-ink focus:border-primary"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={rerank}
              onChange={(e) => setRerank(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-primary)]"
            />
            rerank
          </label>
          <Button disabled={busy || !q.trim()}>{busy ? 'Searching…' : 'Search'}</Button>
        </form>
      </Card>

      {error && <Banner variant="error" title="Search failed">{error}</Banner>}

      {data && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {columns.map((key) => (
            <Column
              key={key}
              label={LABELS[key]}
              rows={data.variants[key]}
              highlight={key === 'hybrid_reranked'}
            />
          ))}
        </div>
      )}
    </div>
  )
}
