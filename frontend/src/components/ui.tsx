export function RunStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'border-white/10 bg-white/[0.03] text-ink-faint',
    running: 'border-gold/30 bg-gold/[0.08] text-gold-bright',
    completed: 'border-low/30 bg-low/[0.08] text-low',
    failed: 'border-high/30 bg-high/[0.08] text-high',
    cancelled: 'border-champagne/20 bg-champagne/[0.06] text-champagne-dim',
  }
  const dots: Record<string, string> = {
    pending: 'bg-ink-faint',
    running: 'animate-pulse bg-gold-bright',
    completed: 'bg-low',
    failed: 'bg-high',
    cancelled: 'bg-champagne-dim',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider ${styles[status] ?? 'border-white/10 bg-white/[0.03] text-ink-faint'}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dots[status] ?? ''}`} />
      {status}
    </span>
  )
}

export function ProgressBar({ progress }: { progress: number }) {
  const pct = Math.max(0, Math.min(100, progress))
  return (
    <div className="flex items-center gap-3">
      <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06] ring-1 ring-inset ring-white/[0.04]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-bronze via-gold to-gold-bright transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 shrink-0 text-right font-mono text-[11px] tabular-nums text-champagne-dim">
        {pct}%
      </span>
    </div>
  )
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-critical shadow-[0_0_6px_rgba(179,38,30,0.9)]',
  high: 'bg-high shadow-[0_0_6px_rgba(224,82,74,0.9)]',
  medium: 'bg-medium shadow-[0_0_6px_rgba(230,162,60,0.9)]',
  low: 'bg-low shadow-[0_0_6px_rgba(125,190,140,0.9)]',
}

export function SeverityBadge({
  severity,
  risk,
  title,
}: {
  severity: string
  risk?: number | null
  title?: string
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider text-ink-soft"
      title={title}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[severity] ?? 'bg-ink-faint'}`} />
      {severity}
      {risk !== null && risk !== undefined ? ` · ${(risk * 100).toFixed(0)}%` : ''}
    </span>
  )
}

export function LensMark({ className }: { className?: string }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className={className}>
      <defs>
        <linearGradient id="lens-gold" x1="0" y1="0" x2="24" y2="24">
          <stop stopColor="#F5D98B" />
          <stop offset="0.5" stopColor="#D4AF37" />
          <stop offset="1" stopColor="#8C6D1F" />
        </linearGradient>
      </defs>
      <circle cx="12" cy="12" r="10" stroke="url(#lens-gold)" strokeWidth="1.2" opacity="0.35" />
      <circle cx="12" cy="12" r="6.5" stroke="url(#lens-gold)" strokeWidth="1.2" opacity="0.65" />
      <circle cx="12" cy="12" r="2.6" fill="url(#lens-gold)" />
    </svg>
  )
}