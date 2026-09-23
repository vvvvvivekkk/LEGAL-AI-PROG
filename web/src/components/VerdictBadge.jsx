// Small verification-verdict badge. Tone maps to outcome, not decoration, and
// each tone carries its own glyph so the verdict never rests on colour alone.
const TONES = {
  ok: 'border-verified-line bg-verified-weak text-verified',
  bad: 'border-danger-line bg-danger-weak text-danger',
  warn: 'border-caution-line bg-caution-weak text-caution',
  off: 'border-line bg-surface text-muted',
}

const GLYPHS = {
  ok: <path d="m2.5 6.3 2.3 2.3L9.5 3.8" />,
  bad: <path d="M3.5 3.5l5 5M8.5 3.5l-5 5" />,
  warn: (
    <>
      <path d="M6 2.8v3.6" />
      <path d="M6 9h.01" />
    </>
  ),
  off: <path d="M3 6h6" />,
}

export default function VerdictBadge({ label, tone = 'off', detail }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium leading-none ${TONES[tone]}`}>
      <svg viewBox="0 0 12 12" className="h-3 w-3 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        {GLYPHS[tone]}
      </svg>
      {label}
      {detail != null && <span className="font-mono opacity-80">{detail}</span>}
    </span>
  )
}

// Map a claim's raw verdicts object to badge props for V1–V4.
export function verdictBadges(v) {
  const badges = [
    v.v1_citation.passed
      ? { label: 'V1 citation', tone: 'ok', detail: 'exists' }
      : { label: 'V1 citation', tone: 'bad', detail: 'missing' },
  ]
  const e = v.v2_entailment
  badges.push({
    label: 'V2 support',
    tone: e.verdict === 'ENTAILS' ? 'ok' : e.verdict === 'CONTRADICTS' ? 'bad' : 'warn',
    detail: `${e.verdict.toLowerCase()}${e.score != null ? ` ${e.score.toFixed(2)}` : ''}`,
  })
  const f = v.v3_fidelity
  badges.push({
    label: 'V3 fidelity',
    tone: f.fidelity >= 0.99 ? 'ok' : f.fidelity > 0 ? 'warn' : 'bad',
    detail: `${Math.round(f.fidelity * 100)}%`,
  })
  const c = v.v4_consistency
  badges.push(
    c
      ? { label: 'V4 consistency', tone: c.stable ? 'ok' : 'bad', detail: `${Math.round(c.consistency * 100)}%` }
      : { label: 'V4 consistency', tone: 'off', detail: 'skipped' },
  )
  return badges
}
