import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Layout from './components/Layout.jsx'
import PageTransition from './components/PageTransition.jsx'
import Home from './pages/Home.jsx'
import Ingest from './pages/Ingest.jsx'
import Ask from './pages/Ask.jsx'
import Search from './pages/Search.jsx'
import Evaluation from './pages/Evaluation.jsx'

const PAGES = [
  { path: '/', element: <Home /> },
  { path: '/ingest', element: <Ingest /> },
  { path: '/ask', element: <Ask /> },
  { path: '/search', element: <Search /> },
  { path: '/evaluation', element: <Evaluation /> },
]

export default function App() {
  const location = useLocation()
  return (
    <Routes location={location}>
      <Route element={<Layout />}>
        {PAGES.map((p) => (
          <Route
            key={p.path}
            path={p.path}
            element={
              <AnimatePresence mode="wait">
                <PageTransition key={p.path}>{p.element}</PageTransition>
              </AnimatePresence>
            }
          />
        ))}
      </Route>
    </Routes>
  )
}
