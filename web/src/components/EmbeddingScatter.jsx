import { useState } from 'react'
import { motion } from 'framer-motion'

// 2D PCA scatter of indexed chunk embeddings, colored by source document.
// Points arrive already projected from GET /embedding-map.
//
// Colour here is *identity* (which document), so it uses the categorical data
// palette from styles.css rather than the brand orange or the status colors
// — a document must never be coloured like a verification outcome. Slots are
// assigned by the document's index in a fixed order and never cycled through a
// generated hue; the order is what keeps neighbouring slots distinguishable
// under colour-vision deficiency. The legend below carries the name, so
// identity is never colour alone.
const PALETTE = [
  'var(--color-data-1)',
  'var(--color-data-2)',
  'var(--color-data-3)',
  'var(--color-data-4)',
  'var(--color-data-5)',
  'var(--color-data-6)',
]

// Composite encoding: identity is (colour, shape), not colour alone. Six hues
// is the most this surface supports as mutually distinguishable, and under
// deuteranopia even those collapse pairwise — so document 7 reuses hue 1 with
// the next shape rather than getting an invented seventh colour, and a
// colour-blind reader can still separate every series.
const SHAPES = ['circle', 'square', 'triangle', 'diamond']

// `animated` picks the motion-wrapped SVG primitive. A custom component can't
// be handed to motion() here (it would need ref forwarding), so each branch
// returns the motion element directly.
function Marker({ shape, cx, cy, r, animated = false, ...rest }) {
  const Rect = animated ? motion.rect : 'rect'
  const Poly = animated ? motion.polygon : 'polygon'
  const Circ = animated ? motion.circle : 'circle'
  if (shape === 'square') {
    return <Rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} rx={r * 0.25} {...rest} />
  }
  if (shape === 'triangle') {
    const h = r * 1.25
    return <Poly points={`${cx},${cy - h} ${cx - h},${cy + h * 0.8} ${cx + h},${cy + h * 0.8}`} {...rest} />
  }
  if (shape === 'diamond') {
    const d = r * 1.25
    return <Poly points={`${cx},${cy - d} ${cx + d},${cy} ${cx},${cy + d} ${cx - d},${cy}`} {...rest} />
  }
  return <Circ cx={cx} cy={cy} r={r} {...rest} />
}
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

  const slotFor = (src) => Math.max(0, sources.indexOf(src))
  const colorFor = (src) => PALETTE[slotFor(src) % PALETTE.length]
  const shapeFor = (src) => SHAPES[Math.floor(slotFor(src) / PALETTE.length) % SHAPES.length]
  const sx = scaler(points.map((p) => p.x), PAD, W - PAD)
  const sy = scaler(points.map((p) => p.y), H - PAD, PAD) // invert y for screen space

  const counts = sources.map((s) => ({
    source: s,
    color: colorFor(s),
    shape: shapeFor(s),
    count: points.filter((p) => p.source_id === s).length,
  }))

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full min-w-0 flex-1 rounded-lg border border-line bg-surface"
        role="img"
        aria-label="Embedding-space scatter of indexed chunks, colored by source document"
      >
        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
          {points.map((p, i) => {
            const cx = sx(p.x)
            const cy = sy(p.y)
            const active = hover?.i === i
            return (
              <Marker
                key={p.chunk_id}
                animated
                shape={shapeFor(p.source_id)}
                cx={cx}
                cy={cy}
                r={active ? 6 : 4}
                fill={colorFor(p.source_id)}
                fillOpacity={hover && !active ? 0.35 : 0.85}
                stroke={active ? 'var(--color-ink)' : 'transparent'}
                strokeWidth={active ? 1.5 : 0}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{
                  delay: Math.min(i * 0.004, 0.9),
                  duration: 0.45,
                  type: 'spring',
                  stiffness: 220,
                  damping: 18,
                }}
                style={{ transformOrigin: `${cx}px ${cy}px`, cursor: 'pointer' }}
                onMouseEnter={() => setHover({ i, cx, cy, p })}
                onMouseLeave={() => setHover(null)}
              />
            )
          })}
          {hover && (
            <g transform={`translate(${Math.min(hover.cx + 8, W - 150)}, ${Math.max(hover.cy - 8, 14)})`}>
              <rect width="150" height="34" rx="6" fill="var(--color-canvas)" stroke="var(--color-line)" />
              <text x="8" y="14" fill="var(--color-ink)" fontSize="10" fontFamily="monospace">
                {hover.p.section_ref || hover.p.chunk_id}
              </text>
              <text x="8" y="27" fill="var(--color-muted)" fontSize="9">
                {hover.p.source_id}
              </text>
            </g>
          )}
        </motion.g>
      </svg>

      <ul className="flex min-w-0 flex-row flex-wrap gap-3 lg:w-56 lg:shrink-0 lg:flex-col lg:gap-2">
        {counts.map((c) => (
          <li key={c.source} className="flex min-w-0 max-w-full items-center gap-2">
            <svg viewBox="0 0 12 12" className="h-3 w-3 shrink-0" aria-hidden>
              <Marker shape={c.shape} cx={6} cy={6} r={4} fill={c.color} />
            </svg>
            <span className="truncate font-mono text-[11px] text-muted" title={c.source}>{c.source}</span>
            <span className="ml-auto font-mono text-[11px] text-faint">{c.count}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
