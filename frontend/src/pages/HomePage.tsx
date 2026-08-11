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
    <div className="relative">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[480px] bg-[radial-gradient(ellipse_60%_50%_at_50%_-10%,rgba(212,175,55,0.10),transparent_70%)]"
      />
      <div className="relative mx-auto max-w-3xl px-6 pb-16 pt-14">
        <div className="flex flex-col items-center text-center">
          <p className="kicker">Autonomous code intelligence</p>
          <h1 className="gold-text mt-4 text-5xl font-bold tracking-tight">
            Bug Lens<span className="text-ink">-Ai</span>
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-ink-soft">
            Defect discovery, duplicate detection, dead code and risk assessment. Point it at a
            repository and get a software health report.
          </p>
        </div>

        {error && (
          <div className="mt-8 rounded-lg border border-high/40 bg-high/10 px-4 py-3 text-sm text-high">
            {error}
          </div>
        )}

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          <form onSubmit={submitUrl} className="card card-hover p-6">
            <h2 className="kicker">From GitHub</h2>
            <p className="mt-1 text-sm text-ink-soft">Clone a public repository by URL.</p>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/user/project"
              className="field mt-4 font-mono text-[13px]"
            />
            <button
              type="submit"
              disabled={running || !url.trim()}
              className="btn-gold mt-3 w-full"
            >
              Analyze repository
            </button>
          </form>

          <form onSubmit={submitZip} className="card card-hover p-6">
            <h2 className="kicker">Upload a ZIP</h2>
            <p className="mt-1 text-sm text-ink-soft">Maximum 50 MB, extracted to a sandbox.</p>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="mt-4 w-full font-mono text-[13px] text-ink-soft file:mr-3 file:rounded-lg file:border file:border-gold/30 file:bg-gold/[0.08] file:px-3 file:py-2 file:font-medium file:text-champagne hover:file:bg-gold/[0.14]"
            />
            <button
              type="submit"
              disabled={running || !file}
              className="btn-gold mt-3 w-full"
            >
              Upload &amp; analyze
            </button>
          </form>
        </div>

        {running && (
          <div className="card mt-8 p-5 text-sm text-ink-soft">
            <p className="font-medium text-ink">Submitting analysis job…</p>
            <p className="mt-1">
              The repository is being ingested into an isolated workspace. Track progress below.
            </p>
          </div>
        )}

        {result && (
          <div className="card mt-8 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-medium text-ink">Analysis queued</p>
                <p className="mt-0.5 font-mono text-sm text-champagne-dim">
                  {result.repository.name}
                  <span className="text-ink-faint"> — run #{result.run.id}</span>
                </p>
              </div>
              <RunStatusBadge status={result.run.status} />
            </div>
            <div className="mt-4">
              <ProgressBar progress={result.run.progress} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}