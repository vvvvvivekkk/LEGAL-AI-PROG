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
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative flex h-16 items-center px-3 text-sm font-medium transition-colors ${
          isActive ? 'text-accent' : 'text-muted hover:text-ink'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {label}
          {isActive && (
            <motion.span
              layoutId="nav-underline"
              className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-brand"
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
      <header className="sticky top-0 z-10 border-b border-line bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 px-6">
          <NavLink to="/" className="flex h-16 items-center gap-3" aria-label="Legal AI home">
            <Logo />
          </NavLink>
          <p className="hidden border-l border-line pl-4 text-xs text-muted lg:block">Answers checked against their source</p>
          <nav className="-mx-3 flex gap-1 overflow-x-auto sm:ml-auto sm:mx-0">
            {LINKS.map((l) => (
              <Tab key={l.to} to={l.to} label={l.label} end={l.end} />
            ))}
          </nav>
        </div>
      </header>

      <main className="relative mx-auto max-w-5xl px-6 py-10">
        {page === 'home' && <div className="home-atmosphere" aria-hidden />}
        <Outlet />
      </main>
    </div>
  )
}
