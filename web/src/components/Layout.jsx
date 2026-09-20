import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import Logo from './Logo.jsx'

const LINKS = [
  { to: '/', label: 'Home', end: true, page: 'home' },
  { to: '/ingest', label: 'Ingest', page: 'ingest' },
  { to: '/ask', label: 'Ask', page: 'ask' },
  { to: '/search', label: 'Search', page: 'search' },
  { to: '/evaluation', label: 'Evaluation', page: 'evaluation' },
]

// Which accent the page gets — see [data-page] in styles.css.
function pageFor(pathname) {
  const hit = LINKS.find((l) => (l.end ? pathname === l.to : pathname.startsWith(l.to)))
  return hit?.page ?? 'home'
}

function Tab({ to, label, end }) {
  return (
    <NavLink to={to} end={end} className="relative px-3 py-2.5 text-sm font-medium">
      {({ isActive }) => (
        <>
          <span className={isActive ? 'text-gradient' : 'text-muted transition-colors hover:text-ink'}>{label}</span>
          {isActive && (
            <motion.span
              layoutId="nav-underline"
              className="bg-gradient-brand absolute inset-x-2 -bottom-px h-[3px] rounded-full shadow-[0_0_12px_rgba(168,85,247,0.8)]"
              transition={{ type: 'spring', stiffness: 500, damping: 40 }}
            />
          )}
        </>
      )}
    </NavLink>
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  const page = pageFor(pathname)

  return (
    <div className="canvas min-h-screen" data-page={page}>
      <header className="sticky top-0 z-10 border-b border-line bg-canvas/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-6 pt-4">
          <NavLink to="/" className="flex items-center gap-3">
            <Logo />
          </NavLink>
          <p className="hidden text-xs text-muted sm:block">Answers checked against their source</p>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-6 pt-2">
          {LINKS.map((l) => (
            <Tab key={l.to} to={l.to} label={l.label} end={l.end} />
          ))}
        </nav>
      </header>

      <main className="relative mx-auto max-w-5xl px-6 py-8">
        {page === 'home' && <div className="home-atmosphere" aria-hidden />}
        <Outlet />
      </main>
    </div>
  )
}
