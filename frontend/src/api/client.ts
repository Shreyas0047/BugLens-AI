export interface Repository {
  id: number
  name: string
  source_type: 'github' | 'zip'
  url: string | null
  workspace_path: string | null
  languages_json: Record<string, LanguageInfo> | null
  structure_json: {
    manifests: { path: string; kind: string }[]
    frameworks: string[]
    top_level_dirs: string[]
    supported_languages: string[]
  } | null
  created_at: string
}

export interface LanguageInfo {
  label: string
  files: number
  loc: number
  supported: boolean
}

export interface AnalysisRun {
  id: number
  repository_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  stage: string | null
  progress: number
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface RunListItem {
  id: number
  repository_id: number
  repository_name: string
  source_type: string
  status: string
  stage: string | null
  progress: number
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface RepositoryWithRun {
  repository: Repository
  run: AnalysisRun
}

export interface Finding {
  id: number
  run_id: number
  source: string
  type: string
  category: string
  file: string
  line: number
  column: number
  message: string
  description: string
  confidence: number
  evidence_json: Record<string, unknown> | null
  status: string
  risk_score: number | null
  severity_predicted: string | null
  model_version: string | null
  created_at: string
}

export interface FindingListOut {
  total: number
  items: Finding[]
}

export interface FindingsStatsOut {
  total: number
  by_category: { category: string; count: number }[]
  by_source: { source: string; count: number }[]
  high_confidence: number
}

export interface FileStat {
  id: number
  path: string
  language: string
  loc: number
  complexity: number
  maintainability: number | null
}

export interface RunFindingsParams {
  category?: string
  source?: string
  type?: string
  status?: string
  min_confidence?: number
  q?: string
  limit?: number
  offset?: number
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep default */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  createFromUrl: (url: string) =>
    request<RepositoryWithRun>('/repositories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    }),

  uploadZip: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<RepositoryWithRun>('/repositories/upload', { method: 'POST', body: form })
  },

  listRepositories: () => request<Repository[]>('/repositories'),
  getRepository: (id: number) => request<Repository>(`/repositories/${id}`),
  listRuns: () => request<RunListItem[]>('/runs'),
  getRun: (id: number) => request<AnalysisRun>(`/runs/${id}`),
  getRunFindings: (id: number, params: RunFindingsParams = {}) => {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
    }
    const q = qs.toString()
    return request<FindingListOut>(`/runs/${id}/findings${q ? `?${q}` : ''}`)
  },
  getRunFindingsStats: (id: number) => request<FindingsStatsOut>(`/runs/${id}/findings/stats`),
  getRunFiles: (id: number) => request<FileStat[]>(`/runs/${id}/files`),
  updateFindingStatus: (runId: number, findingId: number, status: string) =>
    request<Finding>(`/runs/${runId}/findings/${findingId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }),
}
