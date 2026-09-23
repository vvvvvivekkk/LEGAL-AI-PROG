import { AlertIcon, CheckIcon, InfoIcon } from './icons.jsx'

// Status banner. Variants map to real outcomes (success / caution / info /
// error) with a distinct color and icon each — left accent rule + tinted
// surface, so the outcome never rests on colour alone.
const VARIANTS = {
  success: {
    Icon: CheckIcon,
    wrap: 'border-verified-line border-l-verified bg-verified-weak text-verified',
    body: 'text-ink',
  },
  caution: {
    Icon: AlertIcon,
    wrap: 'border-caution-line border-l-caution bg-caution-weak text-caution',
    body: 'text-ink',
  },
  info: {
    Icon: InfoIcon,
    wrap: 'border-info-line border-l-info bg-info-weak text-info',
    body: 'text-ink',
  },
  error: {
    Icon: AlertIcon,
    wrap: 'border-danger-line border-l-danger bg-danger-weak text-danger',
    body: 'text-ink',
  },
}

export default function Banner({ variant = 'info', title, children }) {
  const v = VARIANTS[variant] ?? VARIANTS.info
  const { Icon } = v
  return (
    <div className={`flex gap-3 rounded-[var(--radius)] border border-l-2 px-4 py-3 ${v.wrap}`}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0">
        {title && <div className="text-sm font-semibold leading-5">{title}</div>}
        {children && <div className={`text-sm leading-5 ${v.body} ${title ? 'mt-0.5' : ''}`}>{children}</div>}
      </div>
    </div>
  )
}
