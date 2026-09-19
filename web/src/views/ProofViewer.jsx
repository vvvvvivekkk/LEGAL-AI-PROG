import { useState } from 'react'
import { query as runQuery } from '../api.js'
import Banner from '../components/Banner.jsx'
import Button from '../components/Button.jsx'
import Card, { CardHeader } from '../components/Card.jsx'
import { ShieldIcon } from '../components/icons.jsx'

function VerdictBadge({ label, tone, detail }) {
  const tones = {
    ok: 'border-verified/40 bg-verified-weak text-verified',
    bad: 'border-danger/40 bg-danger-weak text-danger',
    warn: 'border-caution/40 bg-caution-weak text-caution',
    off: 'border-line bg-surface text-faint',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium ${tones[tone]}`}>
      {label}
      {detail && <span className="font-mono opacity-80">{detail}</span>}
    </span>
  )
}

function verdicts(v) {
  const badges = []
  badges.push(
    v.v1_citation.passed
      ? { label: 'V1 citation', tone: 'ok', detail: 'exists' }
      : { label: 'V1 citation', tone: 'bad', detail: 'missing' },
  )
  const e = v.v2_entailment
  badges.push({
    label: 'V2',
    tone: e.verdict === 'ENTAILS' ? 'ok' : e.verdict === 'CONTRADICTS' ? 'bad' : 'warn',
    detail: `${e.verdict.toLowerCase()}${e.score != null ? ` ${e.score.toFixed(2)}` : ''}`,
  })
  badges.push({
    label: 'V3 fidelity',
    tone: v.v3_fidelity.fidelity >= 0.99 ? 'ok' : v.v3_fidelity.fidelity > 0 ? 'warn' : 'bad',
    detail: `${Math.round(v.v3_fidelity.fidelity * 100)}%`,
  })
  const v4 = v.v4_consistency
  badges.push(
    v4
      ? { label: 'V4', tone: v4.stable ? 'ok' : 'bad', detail: `${Math.round(v4.consistency * 100)}%` }
      : { label: 'V4', tone: 'off', detail: 'skipped' },
  )
  return badges
}

function Gauge({ vcs, decision }) {
  const answered = decision === 'ANSWER'
  const pct = vcs != null ? Math.round(vcs * 100) : null
  return (
    <div className="flex items-center gap-4 rounded-lg border border-line bg-surface px-5 py-4">
      <div>
        <div className="text-xs text-muted">Verification confidence</div>
        <div className="font-mono text-3xl font-medium text-ink">{pct != null ? `${pct}` : '—'}<span className="text-lg text-faint">/100</span></div>
      </div>
      <div className="ml-auto">
        <span
          className={`rounded-full border px-3 py-1 text-xs font-semibold ${
            answered
              ? 'border-verified/40 bg-verified-weak text-verified'
              : 'border-caution/40 bg-caution-weak text-caution'
          }`}
        >
          {answered ? 'Answered' : 'Abstained'}
        </span>
      </div>
    </div>
  )
}

export default function ProofViewer() {
  const [q, setQ] = useState('')
  const [k, setK] = useState(5)
  const [rerank, setRerank] = useState(true)
  const [selfConsistency, setSelfConsistency] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  async function run(e) {
    e?.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    setError(null)
    try {
      setData(await runQuery({ query: q, k, rerank, self_consistency: selfConsistency }))
    } catch (err) {
      setError(err.message)
      setData(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card tone="input">
        <CardHeader
          icon={ShieldIcon}
          title="Ask, and see the proof"
          subtitle="Runs the full pipeline and shows every claim beside the source it was checked against and the verdict of each verification layer."
        />
        <form onSubmit={run} className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="What is the maximum security deposit a landlord can collect?"
            className="min-w-[240px] flex-1 rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm text-ink placeholder:text-faint focus:border-primary"
          />
          <label className="flex items-center gap-2 text-xs text-muted">
            top-k
            <input type="number" min="1" max="20" value={k} onChange={(e) => setK(Number(e.target.value))}
              className="w-16 rounded-lg border border-line bg-surface px-2.5 py-2 text-sm text-ink focus:border-primary" />
          </label>
          <label className="flex items-center gap-2 text-xs text-muted">
            resamples
            <input type="number" min="0" max="5" value={selfConsistency} onChange={(e) => setSelfConsistency(Number(e.target.value))}
              className="w-16 rounded-lg border border-line bg-surface px-2.5 py-2 text-sm text-ink focus:border-primary" />
          </label>
          <label className="flex items-center gap-2 text-xs text-muted">
            <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-primary)]" />
            rerank
          </label>
          <Button disabled={busy || !q.trim()}>{busy ? 'Verifying…' : 'Run verification'}</Button>
        </form>
      </Card>

      {error && <Banner variant="error" title="Query failed">{error}</Banner>}

      {data && (
        <div className="space-y-5">
          <Gauge vcs={data.vcs} decision={data.decision} />

          <Card tone="flat">
            <p className="whitespace-pre-wrap leading-relaxed text-ink/90">{data.answer_text}</p>
          </Card>

          {data.abstained && (
            <Banner variant="info" title="Abstained">
              The model declined to answer from the retrieved context — no verifiable claims were produced.
            </Banner>
          )}

          {data.proof.claims.map((c, i) => (
            <Card key={i} tone="flat">
              <div className="flex items-start justify-between gap-4">
                <p className="text-[15px] leading-relaxed text-ink">{c.claim_text}</p>
                <span className="shrink-0 font-mono text-xs text-faint">+{c.vcs_contribution.toFixed(2)}</span>
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {c.supporting_chunk_ids.map((id) => (
                  <span key={id} className="rounded-md border border-line bg-primary-weak/50 px-2 py-1 font-mono text-[11px] text-primary">
                    {id}
                  </span>
                ))}
              </div>

              {c.quoted_span && (
                <blockquote className="mt-3 border-l-2 border-primary/60 bg-canvas/60 px-4 py-2 text-[13px] leading-relaxed text-ink/80">
                  “{c.quoted_span}”
                </blockquote>
              )}

              <div className="mt-3 flex flex-wrap gap-1.5">
                {verdicts(c.verdicts).map((b) => (
                  <VerdictBadge key={b.label} {...b} />
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
