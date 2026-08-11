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
}
