// Section container. `tone` encodes hierarchy rather than making every card
// identical: "input" cards (where you act) carry the fuller shadow plus a
// faint orange edge glow; "flat" cards (results) recede with a hairline shadow.
// Both are white glass over the canvas grid.
const TONES = {
  input: 'bg-white/80 backdrop-blur-xl shadow-[var(--shadow-card),var(--shadow-glow)]',
  flat: 'bg-white/80 backdrop-blur-lg shadow-[var(--shadow-card)]',
}

export default function Card({ tone = 'flat', className = '', children }) {
  return (
    <section className={`rounded-xl border border-line p-6 ${TONES[tone]} ${className}`}>
      {children}
    </section>
  )
}

export function CardHeader({ title, subtitle, icon: Icon }) {
  return (
    <div className="mb-5 flex items-start gap-3">
      {Icon && (
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent-line bg-accent-weak text-accent">
          <Icon className="h-[18px] w-[18px]" />
        </span>
      )}
      <div>
        <h2 className="text-base font-semibold leading-6 text-ink">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm leading-relaxed text-muted">{subtitle}</p>}
      </div>
    </div>
  )
}

// Page title block for the inner pages. Plain ink, not the gradient: the
// gradient belongs to the Home hero alone.
export function PageHeader({ title, subtitle }) {
  return (
    <header className="mb-6">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">{title}</h1>
      {subtitle && <p className="mt-1.5 max-w-2xl text-[15px] leading-relaxed text-muted">{subtitle}</p>}
    </header>
  )
}
