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
      <h1 className="text-2xl font-bold text-slate-900">Repositories</h1>
      {isLoading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {repos?.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">Nothing analyzed yet.</p>
      )}
      <div className="mt-6 space-y-3">
        {repos?.map((repo) => {
          const languages = repo.languages_json ? Object.entries(repo.languages_json) : []
          return (
            <div key={repo.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <p className="font-medium text-slate-900">{repo.name}</p>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs capitalize text-slate-600">
                  {repo.source_type}
                </span>
              </div>
              {repo.url && <p className="mt-1 truncate text-sm text-slate-500">{repo.url}</p>}
              <p className="mt-1 text-sm text-slate-500">Analyzed {formatDate(repo.created_at)}</p>
              {languages.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {languages.map(([key, info]) => (
                    <span
                      key={key}
                      className={`rounded-lg border px-2.5 py-1 text-xs ${
                        info.supported
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                          : 'border-slate-200 bg-slate-50 text-slate-500'
                      }`}
                      title={info.supported ? 'Fully analyzed' : 'Unsupported — listed only'}
                    >
                      {info.label} · {info.files} files · {info.loc.toLocaleString()} lines
                    </span>
                  ))}
                </div>
              )}
              {repo.structure_json && repo.structure_json.frameworks.length > 0 && (
                <p className="mt-2 text-sm text-slate-500">
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
