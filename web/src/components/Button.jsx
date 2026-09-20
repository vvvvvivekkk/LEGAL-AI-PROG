const VARIANTS = {
  // The brand gradient with a violet glow; brightens on hover, goes flat when disabled.
  primary:
    'bg-gradient-brand text-white shadow-[var(--shadow-button)] hover:brightness-110 active:brightness-95 disabled:opacity-40 disabled:shadow-none disabled:hover:brightness-100',
  ghost:
    'bg-transparent text-muted border border-line hover:text-ink hover:border-faint disabled:opacity-50',
}

export default function Button({ variant = 'primary', className = '', children, ...rest }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-[filter,opacity] disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
