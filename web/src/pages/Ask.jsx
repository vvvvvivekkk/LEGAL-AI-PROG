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

// Always-visible verification result for an answer. This is the first thing
// a reader sees on every reply — the per-claim proof below is the drill-down,
// not the only evidence that verification happened.
function VerificationBadge({ decision, vcs, claimCount, mode }) {
  // A general-knowledge answer is not on the verified/abstained axis at all —
  // it was never checked against the documents, so it gets its own badge.
  if (mode === 'general_knowledge') {
    return (
      <div
        className="inline-flex items-center gap-2 rounded-full border border-unsourced/40 bg-unsourced-weak py-1 pl-1.5 pr-3 text-[12px] font-medium text-unsourced shadow-[0_0_20px_-6px_var(--color-unsourced)]"
        title="Answered from the model's general legal knowledge. Nothing here was retrieved from or checked against your documents."
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-unsourced text-canvas" aria-hidden>
          <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 8.5v-2" />
            <path d="M6 4h.01" />
            <circle cx="6" cy="6" r="4.5" />
          </svg>
        </span>
        <span>General knowledge — not verified against your documents</span>
      </div>
    )
  }
  const verified = decision === 'ANSWER'
  const score = vcs != null ? vcs.toFixed(2) : '—'
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border py-1 pl-1.5 pr-3 text-[12px] font-medium ${
        verified
          ? 'border-verified/40 bg-verified-weak text-verified shadow-[0_0_20px_-6px_var(--color-verified)]'
          : 'border-caution/40 bg-caution-weak text-caution shadow-[0_0_20px_-6px_var(--color-caution)]'
      }`}
      title={
        verified
          ? `Every claim passed the verification chain. Verification confidence score ${score}.`
          : `Verification confidence ${score} was below the answer threshold, so nothing was asserted.`
      }
    >
      <span
        className={`flex h-5 w-5 items-center justify-center rounded-full ${
          verified ? 'bg-verified text-canvas' : 'bg-caution text-canvas'
        }`}
        aria-hidden
      >
        {verified ? (
          <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m2.5 6.5 2.3 2.3L9.5 4" />
          </svg>
        ) : (
          <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M6 3v3.5" />
            <path d="M6 9h.01" />
          </svg>
        )}
      </span>
      <span>{verified ? 'Verified' : 'Abstained'}</span>
      <span className="font-mono text-[11px] opacity-90">VCS {score}</span>
      {verified && claimCount > 0 && (
        <span className="text-[11px] opacity-70">
          · {claimCount} {claimCount === 1 ? 'claim' : 'claims'} checked
        </span>
      )}
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
            <span key={id} className="rounded-md border border-line bg-accent-weak/60 px-2 py-1 font-mono text-[11px] text-accent">
              {id}
            </span>
          ))}
          <span className="ml-auto font-mono text-[11px] text-faint">contributes {claim.vcs_contribution.toFixed(2)}</span>
        </div>
        {claim.quoted_span && (
          <blockquote className="border-l-2 border-accent/60 px-3 py-1 text-[13px] leading-relaxed text-ink/80">
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
              open ? 'border-accent bg-accent text-canvas' : 'border-accent/40 bg-accent-weak/60 text-accent hover:bg-accent-weak'
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
  const general = data.answer_mode === 'general_knowledge'
  // A general-knowledge answer carries no verified claims, so it renders as
  // plain prose — never through the citation/proof path.
  const abstainedOrNoClaims = general || data.abstained || claims.length === 0

  return (
    <div className="rounded-2xl rounded-tl-sm border border-line bg-surface p-4 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent-weak text-accent">
          <ShieldIcon className="h-4 w-4" />
        </span>
        <VerificationBadge decision={data.decision} vcs={data.vcs} claimCount={claims.length} mode={data.answer_mode} />
      </div>

      {abstainedOrNoClaims ? (
        <div className="space-y-2">
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink/90">{data.answer_text}</p>
          {general ? (
            <div className="rounded-xl border border-unsourced/30 bg-unsourced-weak/50 p-3 text-[13px] leading-relaxed text-ink/80">
              <p className="font-medium text-unsourced">Not from your documents</p>
              <p className="mt-1">
                Your indexed documents didn't support an answer, and this was a general legal
                concept question, so it was answered from the model's own knowledge. It has no
                citations and no verification score — don't rely on it as a statement about your
                own agreements.
              </p>
            </div>
          ) : (
            data.abstained && (
              <Banner variant="info" title="Abstained">
                The answer wasn't supported by the retrieved context, so nothing was asserted.
              </Banner>
            )
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
            <span className="inline-block h-4 w-2 animate-pulse rounded-sm bg-accent/70 align-middle" aria-hidden />
          )}
          <p className="mt-2 text-[11px] text-faint">Click a citation to see the passage it came from and each verification verdict.</p>
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
      const data = await runQuery({ query: q, k: 12, rerank: true, self_consistency: 0 })
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
          <div className="rounded-2xl border border-line bg-raised p-6 shadow-[var(--shadow-card),var(--shadow-glow)]">
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
                  className="rounded-lg border border-line bg-canvas/40 px-3 py-2 text-left text-sm text-muted transition-colors hover:border-accent/50 hover:text-ink"
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
              <div className="bg-gradient-brand max-w-[80%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-white shadow-[var(--shadow-button)]">
                {turn.text}
              </div>
            </motion.div>
          ) : (
            <AssistantTurn key={i} turn={turn} />
          ),
        )}

        {busy && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <span className="h-2 w-2 animate-bounce rounded-full bg-brand-indigo [animation-delay:-0.2s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-brand-violet [animation-delay:-0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-brand-cyan" />
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
          className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm text-ink shadow-[var(--shadow-flat)] placeholder:text-faint focus:border-accent"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="bg-gradient-brand rounded-xl px-5 py-3 text-sm font-medium text-white shadow-[var(--shadow-button)] transition-[filter,opacity] hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          Ask
        </button>
      </form>
    </div>
  )
}
