// Section container. `tone` encodes hierarchy rather than making every card
// identical: "input" cards are raised, carry a layered shadow and a faint
// glow in the page accent; "flat" cards recede with a hairline shadow.
const TONES = {
  input: 'bg-raised border-line shadow-[var(--shadow-card),var(--shadow-glow)]',
  flat: 'bg-surface border-line-soft shadow-[var(--shadow-flat)]',
}

export default function Card({ tone = 'flat', className = '', children }) {
  return (
    <section className={`rounded-[var(--radius)] border p-5 ${TONES[tone]} ${className}`}>
      {children}
    </section>
  )
}

export function CardHeader({ title, subtitle, icon: Icon }) {
  return (
    <div className="mb-4 flex items-start gap-3">
      {Icon && (
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent-weak text-accent shadow-[0_0_16px_-4px_var(--accent)]">
          <Icon className="h-[18px] w-[18px]" />
        </span>
      )}
      <div>
        <h2 className="text-[15px] font-semibold leading-6 text-ink">{title}</h2>
        {subtitle && <p className="mt-0.5 text-[13px] leading-5 text-muted">{subtitle}</p>}
      </div>
    </div>
  )
}
