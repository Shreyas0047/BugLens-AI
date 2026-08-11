import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RunsPage from './pages/RunsPage'
import RepositoriesPage from './pages/RepositoriesPage'
import RunDetailPage from './pages/RunDetailPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 2000 } },
})

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
    isActive ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100'
  }`

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 text-slate-900">
          <header className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
              <Link to="/" className="text-lg font-bold tracking-tight">
                Bug Lens<span className="text-blue-600">-Ai</span>
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
