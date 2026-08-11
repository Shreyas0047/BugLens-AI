import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api, type Finding } from '../api/client'
import { ProgressBar, RunStatusBadge, formatDate } from '../components/ui'

const CATEGORY_STYLES: Record<string, string> = {
  SECURITY: 'bg-red-50 text-red-700 border-red-200',
  CORRECTNESS: 'bg-amber-50 text-amber-700 border-amber-200',
  CODE_SMELL: 'bg-violet-50 text-violet-700 border-violet-200',
  PERFORMANCE: 'bg-cyan-50 text-cyan-700 border-cyan-200',
}

const SEVERITY_TONE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-slate-100 text-slate-600',
  info: 'bg-slate-100 text-slate-500',
}

function severityLabel(confidence: number): string {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

function FindingRow({ finding }: { finding: Finding }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${CATEGORY_STYLES[finding.category] ?? 'bg-slate-50 text-slate-600 border-slate-200'}`}
        >
          {finding.category}
        </span>
        <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-700">
          {finding.type}
        </code>
        <span className="text-xs text-slate-400">via {finding.source}</span>
        <span
          className={`ml-auto inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${SEVERITY_TONE[finding.severity_predicted ?? severityLabel(finding.confidence)] ?? 'bg-slate-100 text-slate-600'}`}
          title={`risk ${finding.risk_score ?? '—'} · confidence ${(finding.confidence * 100).toFixed(0)}%`}
        >
          {finding.severity_predicted ?? severityLabel(finding.confidence)}
          {finding.risk_score !== null ? ` · ${(finding.risk_score * 100).toFixed(0)}%` : ''}
        </span>
      </div>

      <p className="mt-3 text-sm font-medium text-slate-900">{finding.message}</p>

      <p className="mt-1 font-mono text-xs text-slate-500">
        {finding.file}
        {finding.line > 0 ? `:${finding.line}${finding.column > 0 ? `:${finding.column}` : ''}` : ''}
      </p>

      {finding.description && (
        <p className="mt-2 text-xs text-slate-500">{finding.description}</p>
      )}

      {typeof finding.evidence_json?.snippet === 'string' && (
        <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-100">
          {finding.evidence_json.snippet}
        </pre>
      )}
    </div>
  )
}

export default function RunDetailPage() {
  const { id } = useParams()
  const runId = Number(id)
  const [category, setCategory] = useState('')
  const [source, setSource] = useState('')
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')

  const { data: run } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'running' || status === 'pending' ? 1500 : false
    },
  })

  const { data: stats } = useQuery({
    queryKey: ['run-findings-stats', runId],
    queryFn: () => api.getRunFindingsStats(runId),
  })

  const { data: findings, isLoading } = useQuery({
    queryKey: ['run-findings', runId, category, source, q],
    queryFn: () =>
      api.getRunFindings(runId, {
        category: category || undefined,
        source: source || undefined,
        q: q || undefined,
        limit: 500,
      }),
    enabled: run?.status === 'completed',
  })

  const { data: files } = useQuery({
    queryKey: ['run-files', runId],
    queryFn: () => api.getRunFiles(runId),
    enabled: run?.status === 'completed',
  })

  const categories = useMemo(
    () => stats?.by_category ?? [],
    [stats],
  )
  const sources = useMemo(
    () => stats?.by_source ?? [],
    [stats],
  )

  const filtersVisible = (stats?.total ?? 0) > 0
  const running = run?.status === 'running' || run?.status === 'pending'

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Link to="/runs" className="text-sm text-blue-600 hover:underline">
        ← All runs
      </Link>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Run #{runId}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {run?.started_at ? `Started ${formatDate(run.started_at)}` : ''}
            {run?.finished_at ? ` · finished ${formatDate(run.finished_at)}` : ''}
          </p>
        </div>
        {run && <RunStatusBadge status={run.status} />}
      </div>

      {run?.stage && running && (
        <p className="mt-2 text-sm capitalize text-blue-700">Stage: {run.stage}</p>
      )}
      {run?.error && run.status === 'failed' && (
        <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {run.error}
        </p>
      )}
      {run && running && (
        <div className="mt-4">
          <ProgressBar progress={run.progress} />
        </div>
      )}

      {stats && stats.total > 0 && (
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-3xl font-bold text-slate-900">{stats.total}</p>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Findings
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-3xl font-bold text-red-600">{stats.high_confidence}</p>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              High confidence
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-3xl font-bold text-slate-900">{sources.length}</p>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Analyzers
            </p>
          </div>
        </div>
      )}

      {filtersVisible && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.category} value={c.category}>
                {c.category} ({c.count})
              </option>
            ))}
          </select>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.source} value={s.source}>
                {s.source} ({s.count})
              </option>
            ))}
          </select>
          <form
            className="flex-1 min-w-48"
            onSubmit={(e) => {
              e.preventDefault()
              setQ(search)
            }}
          >
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search message or file…"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
          </form>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {running && (
          <p className="text-sm text-slate-500">Waiting for analysis to complete…</p>
        )}
        {isLoading && !running && <p className="text-sm text-slate-500">Loading findings…</p>}
        {!running && !isLoading && (findings?.items.length ?? 0) === 0 && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center">
            <p className="font-medium text-emerald-900">No findings</p>
            <p className="mt-1 text-sm text-emerald-700">
              {findings ? 'No issues matched the current filters.' : 'No issues found in this run.'}
            </p>
          </div>
        )}
        {!running && findings?.items.map((f) => <FindingRow key={f.id} finding={f} />)}
      </div>

      {!running && (files?.length ?? 0) > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold text-slate-900">File metrics</h2>
          <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3 font-medium">File</th>
                  <th className="px-4 py-3 font-medium">Language</th>
                  <th className="px-4 py-3 text-right font-medium">LOC</th>
                  <th className="px-4 py-3 text-right font-medium">Complexity</th>
                  <th className="px-4 py-3 text-right font-medium">Maintainability</th>
                </tr>
              </thead>
              <tbody>
                {files?.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-700">{f.path}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{f.language}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">{f.loc}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">
                      {f.complexity}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-700">
                      {f.maintainability !== null ? f.maintainability.toFixed(2) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
