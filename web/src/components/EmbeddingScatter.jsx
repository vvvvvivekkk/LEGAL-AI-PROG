import { useState } from 'react'
import { motion } from 'framer-motion'

// 2D PCA scatter of indexed chunk embeddings, colored by source document.
// Points arrive already projected from GET /embedding-map.
const PALETTE = ['#6d7cff', '#38bdf8', '#34d399', '#fbbf24', '#f472b6', '#a78bfa', '#f87171', '#22d3ee']
const W = 480
const H = 320
const PAD = 24

function scaler(values, lo, hi) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min
  if (span === 0) return () => (lo + hi) / 2
  return (v) => lo + ((v - min) / span) * (hi - lo)
}

export default function EmbeddingScatter({ points, sources }) {
  const [hover, setHover] = useState(null)

  if (!points || points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-line px-5 py-10 text-center text-sm text-muted">
        Index a document to see its chunks projected into embedding space.
      </div>
    )
  }

  const colorFor = (src) => PALETTE[Math.max(0, sources.indexOf(src)) % PALETTE.length]
  const sx = scaler(points.map((p) => p.x), PAD, W - PAD)
  const sy = scaler(points.map((p) => p.y), H - PAD, PAD) // invert y for screen space

  const counts = sources.map((s) => ({
    source: s,
    color: colorFor(s),
    count: points.filter((p) => p.source_id === s).length,
  }))

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full flex-1 rounded-lg border border-line-soft bg-canvas/40"
        role="img"
        aria-label="Embedding-space scatter of indexed chunks, colored by source document"
      >
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
          {points.map((p, i) => {
            const cx = sx(p.x)
            const cy = sy(p.y)
            const active = hover?.i === i
            return (
              <motion.circle
                key={p.chunk_id}
                cx={cx}
                cy={cy}
                r={active ? 6 : 4}
                fill={colorFor(p.source_id)}
                fillOpacity={hover && !active ? 0.35 : 0.85}
                stroke={active ? '#e8ecf3' : 'transparent'}
                strokeWidth={active ? 1.5 : 0}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: Math.min(i * 0.008, 0.5), type: 'spring', stiffness: 300, damping: 20 }}
                onMouseEnter={() => setHover({ i, cx, cy, p })}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: 'pointer' }}
              />
            )
          })}
          {hover && (
            <g transform={`translate(${Math.min(hover.cx + 8, W - 150)}, ${Math.max(hover.cy - 8, 14)})`}>
              <rect width="150" height="34" rx="6" fill="#0b0f17" stroke="#243044" />
              <text x="8" y="14" fill="#e8ecf3" fontSize="10" fontFamily="monospace">
                {hover.p.section_ref || hover.p.chunk_id}
              </text>
              <text x="8" y="27" fill="#94a3b8" fontSize="9">
                {hover.p.source_id}
              </text>
            </g>
          )}
        </motion.g>
      </svg>

      <ul className="flex flex-row flex-wrap gap-3 lg:w-48 lg:flex-col lg:gap-2">
        {counts.map((c) => (
          <li key={c.source} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: c.color }} />
            <span className="truncate font-mono text-[11px] text-muted" title={c.source}>{c.source}</span>
            <span className="ml-auto font-mono text-[11px] text-faint">{c.count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
