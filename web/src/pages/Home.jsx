import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { stats } from '../api.js'
import Hero3D from '../components/Hero3D.jsx'

const REDUCED =
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function useCountUp(target, ms = 900) {
  const [value, setValue] = useState(REDUCED ? target : 0)
  useEffect(() => {
    if (REDUCED) {
      setValue(target)
      return
    }
    let raf = 0
    let start = 0
    const step = (t) => {
      if (!start) start = t
      const p = Math.min(1, (t - start) / ms)
      setValue(Math.round(target * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return value
}

function StatChip({ value, label }) {
  const shown = useCountUp(value)
  return (
    <div className="group rounded-xl border border-line bg-white px-4 py-3 shadow-[var(--shadow-card)] transition-[border-color,transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-accent-line hover:shadow-[var(--shadow-card),var(--shadow-glow)]">
      <div className="font-mono text-2xl font-medium text-ink transition-colors group-hover:text-accent">{shown}</div>
      <div className="mt-0.5 text-xs text-muted">{label}</div>
    </div>
  )
}

const STEPS = [
  { n: 1, title: 'Retrieve', body: 'Hybrid search finds the passages most likely to answer your question.' },
  { n: 2, title: 'Cite', body: 'The model must attribute every claim to a specific source chunk.' },
  { n: 3, title: 'Verify', body: 'Each claim is checked against its source before you ever see it.' },
]

export default function Home() {
  const [totals, setTotals] = useState(null)

  useEffect(() => {
    let alive = true
    stats()
      .then((d) => alive && setTotals(d))
      .catch(() => alive && setTotals({ chunks: 0, documents: 0 }))
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="space-y-10">
      <section className="grid items-center gap-8 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <p className="text-sm text-muted">Retrieval-augmented, verification-gated</p>
          <h1 className="text-gradient mt-2 text-[2.75rem] font-bold leading-[1.08] tracking-[-0.02em] md:text-5xl">
            Legal answers you can audit.
          </h1>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-muted">
            Ask questions over your indexed statutes and get answers where every claim is checked
            against its source — with the proof attached, not promised.
          </p>

          <div className="mt-6 flex gap-3">
            <Link
              to="/ask"
              className="rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-[var(--shadow-button)] transition-colors hover:bg-primary-hover"
            >
              Ask a question
            </Link>
            <Link
              to="/ingest"
              className="rounded-lg border border-line bg-canvas px-4 py-2.5 text-sm font-medium text-muted shadow-[var(--shadow-flat)] transition-colors hover:border-faint hover:text-ink"
            >
              Add a document
            </Link>
          </div>

          {totals && (
            <div className="mt-8 grid max-w-sm grid-cols-2 gap-3">
              <StatChip value={totals.documents} label="documents indexed" />
              <StatChip value={totals.chunks} label="chunks indexed" />
            </div>
          )}
          {totals && totals.chunks === 0 && (
            <p className="mt-3 text-xs text-faint">
              Nothing indexed yet — <Link to="/ingest" className="font-medium text-accent underline decoration-accent-line underline-offset-2">add a document</Link> to get started.
            </p>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative h-64 md:h-80"
        >
          {/* A very soft orange glow behind the hero canvas so it sits in light rather than on a flat panel. */}
          <div
            aria-hidden
            className="absolute -inset-10 bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--color-brand)_16%,transparent),transparent)] blur-xl"
          />
          <div className="relative h-full overflow-hidden rounded-2xl border border-line bg-white/80 shadow-[var(--shadow-card)] backdrop-blur-sm">
            <Hero3D />
          </div>
          <div className="pointer-events-none absolute bottom-3 left-4 font-mono text-[11px] text-muted">
            embedding space · {totals?.chunks ?? '—'} vectors
          </div>
        </motion.div>
      </section>

      <section className="grid gap-6 sm:grid-cols-3">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 + i * 0.08 }}
            className="rounded-xl border border-line bg-white/80 p-6 shadow-[var(--shadow-card)] backdrop-blur-lg"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full border border-accent-line bg-accent-weak font-mono text-sm font-medium text-accent">{s.n}</div>
            <div className="mt-3 text-sm font-semibold text-ink">{s.title}</div>
            <p className="mt-1 text-[13px] leading-relaxed text-muted">{s.body}</p>
          </motion.div>
        ))}
      </section>
    </div>
  )
}
