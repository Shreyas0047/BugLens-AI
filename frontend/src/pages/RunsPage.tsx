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
      <p className="kicker">Analysis history</p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-ink">Analysis runs</h1>
      {isLoading && <p className="mt-4 text-sm text-ink-soft">Loading…</p>}
      {runs?.length === 0 && (
        <p className="mt-4 text-sm text-ink-soft">
          No analyses yet — start one from the home page.
        </p>
      )}
      <div className="mt-6 space-y-3">
        {runs?.map((run) => (
          <Link
            key={run.id}
            to={`/runs/${run.id}`}
            className="card card-hover block p-5"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{run.repository_name}</p>
                <p className="mt-0.5 font-mono text-[13px] text-ink-soft">
                  Run <span className="text-gold-bright">#{run.id}</span>
                  <span className="text-ink-faint">
                    {' '}· {run.source_type} · started {formatDate(run.started_at)}
                  </span>
                </p>
                {run.stage && run.status === 'running' && (
                  <p className="mt-1 text-sm capitalize text-gold-bright">
                    Stage: {run.stage}
                  </p>
                )}
                {run.error && run.status === 'failed' && (
                  <p className="mt-1 truncate text-sm text-high" title={run.error}>
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