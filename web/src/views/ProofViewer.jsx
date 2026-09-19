import { useState } from 'react'
import { query as runQuery } from '../api.js'

function Verdicts({ verdicts }) {
  const v1 = verdicts.v1_citation
  const v2 = verdicts.v2_entailment
  const v3 = verdicts.v3_fidelity
  const v4 = verdicts.v4_consistency
  return (
    <div className="verdicts">
      <span className={v1.passed ? 'badge ok' : 'badge bad'}>
        V1 citation {v1.passed ? 'exists' : 'missing'}
      </span>
      <span className={v2.verdict === 'ENTAILS' ? 'badge ok' : v2.verdict === 'CONTRADICTS' ? 'badge bad' : 'badge neutral'}>
        V2 {v2.verdict} {v2.score != null ? `(${v2.score.toFixed(2)})` : ''}
      </span>
      <span className="badge neutral">V3 fidelity {(v3.fidelity * 100).toFixed(0)}%</span>
      {v4 ? (
        <span className={v4.stable ? 'badge ok' : 'badge bad'}>
          V4 consistency {(v4.consistency * 100).toFixed(0)}%
        </span>
      ) : (
        <span className="badge muted-badge">V4 not run</span>
      )}
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
    <div className="panel">
      <h2>Proof viewer</h2>
      <p className="muted">
        Runs the full pipeline (retrieval → generation → verification) and shows the answer with its
        Proof Object: each claim, its supporting source, the quoted span, and the V1–V4 verdicts.
      </p>

      <form className="query-bar" onSubmit={run}>
        <input
          type="text"
          value={q}
          placeholder="e.g. what is the maximum security deposit a landlord can collect?"
          onChange={(e) => setQ(e.target.value)}
        />
        <label className="k-field">
          top-k
          <input type="number" min="1" max="20" value={k} onChange={(e) => setK(Number(e.target.value))} />
        </label>
        <label className="k-field">
          self-consistency
          <input
            type="number"
            min="0"
            max="5"
            value={selfConsistency}
            onChange={(e) => setSelfConsistency(Number(e.target.value))}
          />
        </label>
        <label className="rerank-field">
          <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
          rerank
        </label>
        <button className="primary" disabled={busy || !q.trim()}>
          {busy ? 'Running…' : 'Run'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {data && (
        <div className="proof">
          <div className="proof-head">
            <span className={data.decision === 'ANSWER' ? 'decision answer' : 'decision abstain'}>
              {data.decision}
            </span>
            <span className="vcs">VCS: {data.vcs != null ? data.vcs.toFixed(3) : 'n/a'}</span>
          </div>

          <div className="answer-text">{data.answer_text}</div>

          {data.abstained && (
            <p className="muted">The model abstained — no verifiable claims were produced.</p>
          )}

          {data.proof.claims.map((c, i) => (
            <div className="claim-card" key={i}>
              <div className="claim-top">
                <div className="claim-text">{c.claim_text}</div>
                <div className="contribution">contrib {c.vcs_contribution.toFixed(2)}</div>
              </div>
              <div className="cited">
                {c.supporting_chunk_ids.map((id) => (
                  <span className="mono chip" key={id}>{id}</span>
                ))}
              </div>
              {c.quoted_span && <blockquote className="span">“{c.quoted_span}”</blockquote>}
              <Verdicts verdicts={c.verdicts} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
