import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { formatDate } from '../lib/format'

export default function RepositoriesPage() {
  const { data: repos, isLoading } = useQuery({
    queryKey: ['repositories'],
    queryFn: api.listRepositories,
  })

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-bold tracking-tight text-ink">Repositories</h1>
      {isLoading && <p className="mt-4 text-sm text-ink-soft">Loading…</p>}
      {repos?.length === 0 && (
        <p className="mt-4 text-sm text-ink-soft">Nothing analyzed yet.</p>
      )}
      <div className="mt-6 space-y-3">
        {repos?.map((repo) => {
          const languages = repo.languages_json ? Object.entries(repo.languages_json) : []
          return (
            <div key={repo.id} className="card card-hover p-5">
              <div className="flex items-center justify-between gap-4">
                <p className="truncate font-medium text-ink">{repo.name}</p>
                <span className="chip-graphite font-mono text-[11px] uppercase tracking-wider text-champagne-dim">
                  {repo.source_type}
                </span>
              </div>
              {repo.url && <p className="mt-1 truncate text-sm text-ink-soft">{repo.url}</p>}
              <p className="mt-1 text-sm text-ink-faint">
                Analyzed <span className="tabular-nums">{formatDate(repo.created_at)}</span>
              </p>
              {languages.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {languages.map(([key, info]) => (
                    <span
                      key={key}
                      className={`inline-flex items-center rounded-full border px-2.5 py-1 font-mono text-[11px] ${
                        info.supported
                          ? 'border-low/30 bg-low/[0.08] text-low'
                          : 'border-white/10 bg-white/[0.03] text-ink-faint'
                      }`}
                      title={info.supported ? 'Fully analyzed' : 'Unsupported — listed only'}
                    >
                      <span
                        className={`mr-1.5 h-1.5 w-1.5 rounded-full ${info.supported ? 'bg-low' : 'bg-ink-faint'}`}
                      />
                      {info.label} · {info.files} files · {info.loc.toLocaleString()} lines
                    </span>
                  ))}
                </div>
              )}
              {repo.structure_json && repo.structure_json.frameworks.length > 0 && (
                <p className="mt-2 text-sm text-ink-faint">
                  Frameworks: {repo.structure_json.frameworks.join(', ')}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}