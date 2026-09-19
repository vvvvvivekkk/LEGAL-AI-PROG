// Section container. `tone` encodes hierarchy rather than making every card
// identical: "input" cards are raised and prominent, "flat" cards recede.
const TONES = {
  input: 'bg-raised border-line shadow-lg shadow-black/30',
  flat: 'bg-surface border-line-soft',
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
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-weak text-primary">
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
