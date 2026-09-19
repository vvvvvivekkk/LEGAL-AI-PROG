import { NavLink, Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ScaleCheckIcon } from './icons.jsx'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/ingest', label: 'Ingest' },
  { to: '/ask', label: 'Ask' },
  { to: '/search', label: 'Search' },
  { to: '/evaluation', label: 'Evaluation' },
]

function Tab({ to, label, end }) {
  return (
    <NavLink to={to} end={end} className="relative px-3 py-2.5 text-sm font-medium">
      {({ isActive }) => (
        <>
          <span className={isActive ? 'text-ink' : 'text-muted transition-colors hover:text-ink'}>{label}</span>
          {isActive && (
            <motion.span
              layoutId="nav-underline"
              className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-primary"
              transition={{ type: 'spring', stiffness: 500, damping: 40 }}
            />
          )}
        </>
      )}
    </NavLink>
  )
}

export default function Layout() {
  return (
    <div className="canvas-grid min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-canvas/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-6 pt-5">
          <NavLink to="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-weak text-primary">
              <ScaleCheckIcon className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-lg font-semibold leading-tight tracking-tight">Legal AI</h1>
              <p className="text-xs text-muted">Answers checked against their source</p>
            </div>
          </NavLink>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-6 pt-3">
          {LINKS.map((l) => (
            <Tab key={l.to} {...l} />
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
