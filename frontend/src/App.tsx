import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RunsPage from './pages/RunsPage'
import RepositoriesPage from './pages/RepositoriesPage'
import RunDetailPage from './pages/RunDetailPage'
import { LensMark } from './components/ui'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 2000 } },
})

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
    isActive
      ? 'bg-gold/[0.12] text-gold-bright ring-1 ring-inset ring-gold/25'
      : 'text-ink-soft hover:bg-white/[0.04] hover:text-ink'
  }`

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-surface text-ink">
          <header className="sticky top-0 z-40 border-b border-hairline bg-surface/85 backdrop-blur-md">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
              <Link to="/" className="flex items-center gap-2.5">
                <LensMark />
                <span className="text-lg font-bold tracking-tight text-ink">
                  Bug Lens
                  <span className="gold-text">-Ai</span>
                </span>
              </Link>
              <nav className="flex items-center gap-1">
                <NavLink to="/" className={navLinkClass} end>
                  Analyze
                </NavLink>
                <NavLink to="/repositories" className={navLinkClass}>
                  Repositories
                </NavLink>
                <NavLink to="/runs" className={navLinkClass}>
                  Runs
                </NavLink>
              </nav>
            </div>
          </header>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/runs" element={<RunsPage />} />
            <Route path="/runs/:id" element={<RunDetailPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}