// Brand mark: a seal. A rounded square set on its corner (a notary stamp,
// read abstractly) filled with the orange brand gradient, with a check cut
// through it in the canvas color — "a sealed, verified answer". Pairs with the
// wordmark; pass `mark` to render the seal alone.
export function LogoMark({ className = 'h-8 w-8' }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id="legal-ai-seal" x1="4" y1="4" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0" style={{ stopColor: 'var(--color-brand)' }} />
          <stop offset="1" style={{ stopColor: 'var(--color-brand-strong)' }} />
        </linearGradient>
      </defs>
      <rect x="6" y="6" width="20" height="20" rx="5.5" transform="rotate(45 16 16)" fill="url(#legal-ai-seal)" />
      <path
        d="M10.5 16.5 14.2 20.2 21.8 12.4"
        fill="none"
        stroke="var(--color-canvas)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Logo({ mark = false, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark className="h-8 w-8 drop-shadow-[0_2px_4px_color-mix(in_oklab,var(--color-brand)_30%,transparent)]" />
      {!mark && (
        <span className="text-[17px] font-semibold leading-none tracking-tight text-ink">
          Legal <span className="text-accent">AI</span>
        </span>
      )}
    </span>
  )
}
