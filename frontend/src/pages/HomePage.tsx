import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import { ProgressBar, RunStatusBadge } from '../components/ui'

export default function HomePage() {
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const urlMutation = useMutation({
    mutationFn: (u: string) => api.createFromUrl(u),
    onError: (e: Error) => setError(e.message),
  })
  const zipMutation = useMutation({
    mutationFn: (f: File) => api.uploadZip(f),
    onError: (e: Error) => setError(e.message),
  })

  const submitUrl = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (url.trim()) urlMutation.mutate(url.trim())
  }

  const submitZip = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (file) zipMutation.mutate(file)
  }

  const running = urlMutation.isPending || zipMutation.isPending
  const result = urlMutation.data ?? zipMutation.data

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">Bug Lens-Ai</h1>
      <p className="mt-2 text-slate-600">
        Autonomous repository analysis — defect discovery, duplicate detection, dead code and
        risk assessment. Point it at a repository and get a software health report.
      </p>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <form
          onSubmit={submitUrl}
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-slate-900">From GitHub</h2>
          <p className="mt-1 text-sm text-slate-500">Clone a public repository by URL.</p>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/user/project"
            className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
          <button
            type="submit"
            disabled={running || !url.trim()}
            className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Analyze repository
          </button>
        </form>

        <form
          onSubmit={submitZip}
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-slate-900">Upload a ZIP</h2>
          <p className="mt-1 text-sm text-slate-500">Maximum 50 MB, extracted to a sandbox.</p>
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-4 w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
          <button
            type="submit"
            disabled={running || !file}
            className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Upload &amp; analyze
          </button>
        </form>
      </div>

      {running && (
        <div className="mt-8 rounded-xl border border-blue-200 bg-blue-50 p-5 text-sm text-blue-800">
          <p className="font-medium">Submitting analysis job…</p>
          <p className="mt-1">
            The repository is being ingested into an isolated workspace. Track progress below.
          </p>
        </div>
      )}

      {result && (
        <div className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-emerald-900">Analysis queued</p>
              <p className="text-sm text-emerald-700">
                {result.repository.name} — run #{result.run.id}
              </p>
            </div>
            <RunStatusBadge status={result.run.status} />
          </div>
          <div className="mt-3">
            <ProgressBar progress={result.run.progress} />
          </div>
        </div>
      )}
    </div>
  )
}
