import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { query as runQuery } from '../api.js'
import Banner from '../components/Banner.jsx'
import VerdictBadge, { verdictBadges } from '../components/VerdictBadge.jsx'
import { ShieldIcon } from '../components/icons.jsx'

const prefersReduced =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const EXAMPLES = [
  'How long does a landlord have to refund a security deposit?',
  'What are the lawful grounds for processing personal data?',
  'What penalty applies to a repeat unfair trade practice offence?',
]

// Reveal claims one at a time so the answer reads as if it streams in.
function useReveal(count) {
  const [n, setN] = useState(prefersReduced ? count : 0)
  useEffect(() => {
    if (prefersReduced) {
      setN(count)
      return
    }
    if (n >= count) return
    const t = setTimeout(() => setN((v) => v + 1), 320)
    return () => clearTimeout(t)
  }, [n, count])
  return prefersReduced ? count : n
}

function DecisionPill({ decision, vcs }) {
  const answered = decision === 'ANSWER'
  const pct = vcs != null ? Math.round(vcs * 100) : null
  return (
    <div className="flex items-center gap-2">
      <span
        className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
          answered
            ? 'border-verified/40 bg-verified-weak text-verified'
            : 'border-caution/40 bg-caution-weak text-caution'
        }`}
      >
        {answered ? 'Answered' : 'Abstained'}
      </span>
      {pct != null && <span className="font-mono text-[11px] text-muted">VCS {pct}/100</span>}
    </div>
  )
}

function ClaimProof({ claim }) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className="overflow-hidden"
    >
      <div className="mt-2 rounded-lg border border-line bg-canvas/50 p-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {claim.supporting_chunk_ids.map((id) => (
            <span key={id} className="rounded-md border border-line bg-primary-weak/50 px-2 py-1 font-mono text-[11px] text-primary">
              {id}
            </span>
          ))}
          <span className="ml-auto font-mono text-[11px] text-faint">contributes {claim.vcs_contribution.toFixed(2)}</span>
        </div>
        {claim.quoted_span && (
          <blockquote className="border-l-2 border-primary/60 px-3 py-1 text-[13px] leading-relaxed text-ink/80">
            “{claim.quoted_span}”
          </blockquote>
        )}
        <div className="mt-2 flex flex-wrap gap-1.5">
          {verdictBadges(claim.verdicts).map((b) => (
            <VerdictBadge key={b.label} {...b} />
          ))}
        </div>
      </div>
    </motion.div>
  )
}

function ClaimLine({ claim }) {
  const [open, setOpen] = useState(false)
  const hasProof = claim.supporting_chunk_ids.length > 0 || claim.quoted_span
  return (
    <div className="py-1.5">
      <p className="text-[15px] leading-relaxed text-ink">
        {claim.claim_text}{' '}
        {claim.supporting_chunk_ids.map((id) => (
          <button
            key={id}
            onClick={() => setOpen((o) => !o)}
            className={`ml-1 inline-flex items-center rounded-md border px-1.5 py-0.5 align-middle font-mono text-[11px] transition-colors ${
              open ? 'border-primary bg-primary text-white' : 'border-primary/40 bg-primary-weak/60 text-primary hover:bg-primary-weak'
            }`}
            title="Show proof for this claim"
          >
            {id}
          </button>
        ))}
      </p>
      <AnimatePresence initial={false}>{open && hasProof && <ClaimProof claim={claim} />}</AnimatePresence>
    </div>
  )
}

function AssistantTurn({ turn }) {
  const claims = turn.data?.proof?.claims ?? []
  const revealed = useReveal(claims.length)

  if (turn.error) {
    return <Banner variant="error" title="Query failed">{turn.error}</Banner>
  }

  const data = turn.data
  const abstainedOrNoClaims = data.abstained || claims.length === 0

  return (
    <div className="rounded-2xl rounded-tl-sm border border-line bg-surface p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary-weak text-primary">
          <ShieldIcon className="h-4 w-4" />
        </span>
        <DecisionPill decision={data.decision} vcs={data.vcs} />
      </div>

      {abstainedOrNoClaims ? (
        <div className="space-y-2">
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink/90">{data.answer_text}</p>
          {data.abstained && (
            <Banner variant="info" title="Abstained">
              The answer wasn't supported by the retrieved context, so nothing was asserted.
            </Banner>
          )}
        </div>
      ) : (
        <div>
          {claims.slice(0, revealed).map((c, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
              <ClaimLine claim={c} />
            </motion.div>
          ))}
          {revealed < claims.length && (
            <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-primary/70 align-middle" aria-hidden />
          )}
          <p className="mt-2 text-[11px] text-faint">Click a citation to see the source, quote, and verification verdicts.</p>
        </div>
      )}
    </div>
  )
}

export default function Ask() {
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [turns, setTurns] = useState([])
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth' })
  }, [turns, busy])

  async function ask(text) {
    const q = text.trim()
    if (!q || busy) return
    setInput('')
    setTurns((t) => [...t, { role: 'user', text: q }])
    setBusy(true)
    try {
      const data = await runQuery({ query: q, k: 5, rerank: true, self_consistency: 0 })
      setTurns((t) => [...t, { role: 'assistant', data }])
    } catch (err) {
      setTurns((t) => [...t, { role: 'assistant', error: err.message }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-[70vh] flex-col">
      <div className="flex-1 space-y-4">
        {turns.length === 0 && (
          <div className="rounded-2xl border border-line bg-surface p-6">
            <h2 className="text-[15px] font-semibold text-ink">Ask a question about the indexed documents</h2>
            <p className="mt-1 text-sm text-muted">
              Every answer is broken into claims, each checked against its source. Click a citation in the reply to
              see the passage it came from and how it passed verification.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              {EXAMPLES.map((ex) => (
                <button
                  key={ex}
                  onClick={() => ask(ex)}
                  className="rounded-lg border border-line bg-canvas/40 px-3 py-2 text-left text-sm text-muted transition-colors hover:border-primary/50 hover:text-ink"
                >
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, i) =>
          turn.role === 'user' ? (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-end"
            >
              <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-white">
                {turn.text}
              </div>
            </motion.div>
          ) : (
            <AssistantTurn key={i} turn={turn} />
          ),
        )}

        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.2s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-primary" />
            <span className="ml-1">Retrieving, generating, and verifying…</span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          ask(input)
        }}
        className="sticky bottom-0 mt-4 flex gap-2 border-t border-line bg-canvas/80 py-4 backdrop-blur"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a statute you've indexed…"
          className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink placeholder:text-faint focus:border-primary"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-xl bg-primary px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-primary/40"
        >
          Ask
        </button>
      </form>
    </div>
  )
}
