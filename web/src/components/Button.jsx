const VARIANTS = {
  // Solid brand orange with white text (5.2:1); darkens on hover, goes flat when disabled.
  primary:
    'bg-primary text-white shadow-[var(--shadow-button)] hover:bg-primary-hover disabled:bg-raised disabled:text-faint disabled:shadow-none disabled:hover:bg-raised',
  ghost:
    'bg-canvas text-muted border border-line hover:text-ink hover:border-faint disabled:opacity-50',
}

export default function Button({ variant = 'primary', className = '', children, ...rest }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-[background-color,border-color,color,opacity] disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
