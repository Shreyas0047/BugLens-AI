import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api, type Finding } from '../api/client'
import { ProgressBar, RunStatusBadge, SeverityBadge } from '../components/ui'
import { formatDate } from '../lib/format'

const CATEGORY_TONE: Record<string, string> = {
  SECURITY: 'border-high/30 bg-high/10 text-[#f08780]',
  CORRECTNESS: 'border-medium/30 bg-medium/10 text-medium',
  CODE_SMELL: 'border-champagne/25 bg-champagne/[0.07] text-champagne-dim',
  PERFORMANCE: 'border-low/30 bg-low/10 text-low',
}

const STATUS_TONE: Record<string, string> = {
  open: 'border-white/10 bg-white/[0.03] text-ink-soft',
  confirmed: 'border-gold/30 bg-gold/10 text-gold-bright',
  false_positive: 'border-medium/30 bg-medium/10 text-medium',
  overridden: 'border-[#c9a0dc]/30 bg-[#c9a0dc]/10 text-[#c9a0dc]',
}

function severityLabel(confidence: number): string {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

function FindingRow({
  finding,
  onStatusChange,
  updating,
}: {
  finding: Finding
  onStatusChange: (status: string) => void
  updating: boolean
}) {
  const severity = finding.severity_predicted ?? severityLabel(finding.confidence)
  const confirmed = finding.status === 'confirmed'
  return (
    <div
      className={`card p-5 transition hover:border-white/[0.12] ${
        confirmed ? 'border-l-2 border-l-gold bg-gold/[0.03]' : ''
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${CATEGORY_TONE[finding.category] ?? 'border-white/10 bg-white/[0.03] text-ink-soft'}`}
        >
          {finding.category}
        </span>
        <code className="rounded-md border border-gold/20 bg-gold/[0.06] px-1.5 py-0.5 font-mono text-[11px] font-medium text-gold-bright">
          {finding.type}
        </code>
        <span className="text-xs text-ink-faint">
          via <span className="font-mono">{finding.source}</span>
        </span>
        <span className="ml-auto">
          <SeverityBadge
            severity={severity}
            risk={finding.risk_score}
            title={`risk ${finding.risk_score ?? '—'} · confidence ${(finding.confidence * 100).toFixed(0)}%`}
          />
        </span>
      </div>

      <p className="mt-3 text-sm font-medium text-ink">{finding.message}</p>

      <p className="mt-1 font-mono text-xs text-ink-soft">
        <span className="text-champagne-dim">{finding.file}</span>
        {finding.line > 0 ? (
          <>
            <span className="text-ink-faint">:</span>
            <span className="text-gold-bright">
              {finding.line}
              {finding.column > 0 ? `:${finding.column}` : ''}
            </span>
          </>
        ) : null}
      </p>

      {finding.description && <p className="mt-2 text-xs text-ink-faint">{finding.description}</p>}

      {typeof finding.evidence_json?.snippet === 'string' && (
        <pre className="mt-3 overflow-x-auto rounded-lg border border-white/[0.06] bg-[#0b0b10] p-3 font-mono text-xs leading-relaxed text-[#d8d2c2]">
          {finding.evidence_json.snippet}
        </pre>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/[0.06] pt-3">
        <span
          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider ${STATUS_TONE[finding.status] ?? 'border-white/10 bg-white/[0.03] text-ink-soft'}`}
        >
          {finding.status.replace('_', ' ')}
        </span>
        <div className="ml-auto flex gap-1.5">
          {finding.status !== 'confirmed' && (
            <button
              onClick={() => onStatusChange('confirmed')}
              disabled={updating}
              className="rounded-lg border border-gold/30 px-2.5 py-1 text-xs font-medium text-champagne transition hover:border-gold hover:bg-gold/10 hover:text-gold-bright disabled:opacity-50"
            >
              Confirm
            </button>
          )}
          {finding.status !== 'false_positive' && (
            <button
              onClick={() => onStatusChange('false_positive')}
              disabled={updating}
              className="rounded-lg border border-medium/30 px-2.5 py-1 text-xs font-medium text-ink-soft transition hover:border-medium hover:bg-medium/10 hover:text-medium disabled:opacity-50"
            >
              False positive
            </button>
          )}
          {finding.status !== 'open' && (
            <button
              onClick={() => onStatusChange('open')}
              disabled={updating}
              className="rounded-lg border border-white/15 px-2.5 py-1 text-xs font-medium text-ink-soft transition hover:border-white/40 hover:text-ink disabled:opacity-50"
            >
              Reopen
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function StatTile({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="card p-4">
      <p className={`font-mono text-3xl font-medium tabular-nums ${accent ? 'text-gold-bright' : 'text-champagne'}`}>
        {value}
      </p>
      <p className="kicker mt-1.5">{label}</p>
    </div>
  )
}

export default function RunDetailPage() {
  const { id } = useParams()
  const runId = Number(id)
  const [category, setCategory] = useState('')
  const [source, setSource] = useState('')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const [limit, setLimit] = useState(100)

  const queryClient = useQueryClient()

  const statusMutation = useMutation({
    mutationFn: ({ findingId, status }: { findingId: number; status: string }) =>
      api.updateFindingStatus(runId, findingId, status),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['run-findings', runId] })
      queryClient.invalidateQueries({ queryKey: ['run-findings-stats', runId] })
    },
  })

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
    queryKey: ['run-findings', runId, category, source, status, q, limit],
    queryFn: () =>
      api.getRunFindings(runId, {
        category: category || undefined,
        source: source || undefined,
        status: status || undefined,
        q: q || undefined,
        limit,
      }),
    enabled: run?.status === 'completed',
  })

  const { data: files } = useQuery({
    queryKey: ['run-files', runId],
    queryFn: () => api.getRunFiles(runId),
    enabled: run?.status === 'completed',
  })

  const categories = useMemo(() => stats?.by_category ?? [], [stats])
  const sources = useMemo(() => stats?.by_source ?? [], [stats])

  const filtersVisible = (stats?.total ?? 0) > 0
  const running = run?.status === 'running' || run?.status === 'pending'

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Link
        to="/runs"
        className="font-mono text-sm text-champagne-dim transition hover:text-gold-bright"
      >
        ← All runs
      </Link>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Run <span className="gold-text">{runId}</span>
          </h1>
          <p className="mt-1 text-sm text-ink-soft">
            {run?.started_at ? `Started ${formatDate(run.started_at)}` : ''}
            {run?.finished_at ? ` · finished ${formatDate(run.finished_at)}` : ''}
          </p>
        </div>
        {run && <RunStatusBadge status={run.status} />}
      </div>

      {findings?.items[0]?.model_version && (
        <p className="mt-1 font-mono text-xs text-ink-faint">
          risk model: {findings.items[0].model_version}
        </p>
      )}

      {run?.stage && running && (
        <p className="mt-2 text-sm capitalize text-gold-bright">Stage: {run.stage}</p>
      )}
      {run?.error && run.status === 'failed' && (
        <p className="mt-2 rounded-lg border border-high/40 bg-high/10 px-4 py-3 text-sm text-high">
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
          <StatTile value={String(stats.total)} label="Findings" accent />
          <StatTile value={String(stats.high_confidence)} label="High confidence" />
          <StatTile value={String(sources.length)} label="Analyzers" />
        </div>
      )}

      {filtersVisible && (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-ink outline-none transition focus:border-gold/60 focus:ring-2 focus:ring-gold/20"
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
            className="rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-ink outline-none transition focus:border-gold/60 focus:ring-2 focus:ring-gold/20"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s.source} value={s.source}>
                {s.source} ({s.count})
              </option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border border-white/10 bg-card px-3 py-2 text-sm text-ink outline-none transition focus:border-gold/60 focus:ring-2 focus:ring-gold/20"
          >
            <option value="">All statuses</option>
            <option value="open">open</option>
            <option value="confirmed">confirmed</option>
            <option value="false_positive">false positive</option>
            <option value="overridden">overridden</option>
          </select>
          <form
            className="min-w-48 flex-1"
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
              className="field"
            />
          </form>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {running && <p className="text-sm text-ink-soft">Waiting for analysis to complete…</p>}
        {isLoading && !running && <p className="text-sm text-ink-soft">Loading findings…</p>}
        {!running && !isLoading && (findings?.items.length ?? 0) === 0 && (
          <div className="card p-10 text-center">
            <p className="font-medium text-ink">No findings</p>
            <p className="mt-1 text-sm text-ink-faint">
              {findings ? 'No issues matched the current filters.' : 'No issues found in this run.'}
            </p>
          </div>
        )}
        {!running &&
          findings?.items.map((f) => (
            <FindingRow
              key={f.id}
              finding={f}
              updating={statusMutation.isPending}
              onStatusChange={(next) => statusMutation.mutate({ findingId: f.id, status: next })}
            />
          ))}
        {!running && findings && findings.total > findings.items.length && (
          <button
            onClick={() => setLimit((l) => l + 100)}
            className="btn-ghost-gold w-full py-3"
          >
            Show more ({findings.items.length} of {findings.total})
          </button>
        )}
      </div>

      {!running && (files?.length ?? 0) > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold text-ink">File metrics</h2>
          <div className="card mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/[0.07] text-[11px] uppercase tracking-[0.12em] text-champagne-dim">
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
                    className="border-b border-white/[0.05] last:border-0 hover:bg-white/[0.02]"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-champagne-dim">{f.path}</td>
                    <td className="px-4 py-2.5 text-xs text-ink-soft">{f.language}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
                      {f.loc}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
                      {f.complexity}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs tabular-nums text-ink">
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