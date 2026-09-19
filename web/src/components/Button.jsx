const VARIANTS = {
  primary:
    'bg-primary text-white hover:bg-primary/90 disabled:bg-primary/40 disabled:text-white/70',
  ghost:
    'bg-transparent text-muted border border-line hover:text-ink hover:border-faint disabled:opacity-50',
}

export default function Button({ variant = 'primary', className = '', children, ...rest }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
