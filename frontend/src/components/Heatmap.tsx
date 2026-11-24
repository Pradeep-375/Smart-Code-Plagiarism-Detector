import { useNavigate } from 'react-router-dom'
import { heatColor, pct } from '../utils/format'

interface Props { submissions: { id: number; label: string }[]; cells: { a: number; b: number; score: number; result_id: number }[] }

export default function Heatmap({ submissions, cells }: Props) {
  const nav = useNavigate()
  const lookup = new Map<string, { score: number; result_id: number }>()
  cells.forEach((c) => { lookup.set(`${c.a}-${c.b}`, c); lookup.set(`${c.b}-${c.a}`, c) })
  if (submissions.length < 2) return <p className="p-6 text-center text-sm text-slate-500">Run an analysis to see the similarity heat-map.</p>
  const short = (s: string) => (s.length > 12 ? s.slice(0, 11) + '…' : s)
  return (
    <div className="overflow-auto p-3" role="table" aria-label="Similarity heat-map">
      <div className="inline-grid gap-px" style={{ gridTemplateColumns: `auto repeat(${submissions.length}, minmax(44px, 1fr))` }}>
        <div />
        {submissions.map((s) => <div key={s.id} className="px-1 pb-2 text-center text-[11px] font-medium text-slate-500" title={s.label}>{short(s.label)}</div>)}
        {submissions.map((row) => (
          <div key={row.id} className="contents">
            <div className="sticky left-0 whitespace-nowrap bg-white pr-3 text-right text-[11px] font-medium text-slate-500 dark:bg-navy-900" title={row.label}>{short(row.label)}</div>
            {submissions.map((col) => {
              if (row.id === col.id) return <div key={col.id} className="h-11 rounded bg-slate-100 dark:bg-navy-800" />
              const c = lookup.get(`${row.id}-${col.id}`)
              return c ? (
                <button key={col.id} onClick={() => nav(`/app/compare/${c.result_id}`)} style={{ background: heatColor(c.score) }}
                  className="h-11 rounded text-[11px] font-semibold text-slate-900 transition hover:ring-2 hover:ring-brand-500 dark:text-white"
                  title={`${row.label} ↔ ${col.label}: ${pct(c.score)}`} aria-label={`${row.label} versus ${col.label}: ${pct(c.score)}`}>{Math.round(c.score * 100)}</button>
              ) : <div key={col.id} className="h-11 rounded bg-slate-50 dark:bg-navy-950" />
            })}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs text-slate-500"><span>Low</span><div className="h-2 w-32 rounded" style={{ background: `linear-gradient(90deg, ${heatColor(0)}, ${heatColor(0.5)}, ${heatColor(1)})` }} /><span>High</span></div>
    </div>
  )
}
