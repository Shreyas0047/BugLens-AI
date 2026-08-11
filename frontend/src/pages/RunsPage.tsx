import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { ProgressBar, RunStatusBadge } from '../components/ui'
import { formatDate } from '../lib/format'

export default function RunsPage() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 1500,
  })

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-bold text-slate-900">Analysis runs</h1>
      {isLoading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {runs?.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">No analyses yet — start one from the home page.</p>
      )}
      <div className="mt-6 space-y-3">
        {runs?.map((run) => (
          <Link
            key={run.id}
            to={`/runs/${run.id}`}
            className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate font-medium text-slate-900">{run.repository_name}</p>
                <p className="text-sm text-slate-500">
                  Run #{run.id} · {run.source_type} · started {formatDate(run.started_at)}
                </p>
                {run.stage && run.status === 'running' && (
                  <p className="mt-1 text-sm capitalize text-blue-700">Stage: {run.stage}</p>
                )}
                {run.error && run.status === 'failed' && (
                  <p className="mt-1 truncate text-sm text-red-600" title={run.error}>
                    {run.error}
                  </p>
                )}
              </div>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="mt-3">
              <ProgressBar progress={run.progress} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
