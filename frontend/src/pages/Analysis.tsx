import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Download, FlaskConical, Play } from 'lucide-react'
import { api, downloadFile, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Badge, Button, Card, DataTable, EmptyState, ErrorBox, Field, PageHeader, Pagination, ProgressBar, RiskBadge, Spinner, StatusBadge, Tabs } from '../components/ui'
import Heatmap from '../components/Heatmap'
import { fmtDate, pct } from '../utils/format'
import type { Assignment, Job, Page, ResultSummary } from '../types'

type Tab = 'results' | 'heatmap'

export default function Analysis() {
  const { assignmentId } = useParams()
  const nav = useNavigate()
  const { user } = useAuth()
  const toast = useToast()
  const assignments = useFetch(() => api.get<Page<Assignment>>('/assignments', { params: { page_size: 100 } }).then((r) => r.data.items), [])
  const [history, setHistory] = useState(false)
  const [cross, setCross] = useState(false)
  const [threshold, setThreshold] = useState('')
  const [starting, setStarting] = useState(false)
  const [tab, setTab] = useState<Tab>('results')
  const [q, setQ] = useState('')
  const [risk, setRisk] = useState('')
  const [review, setReview] = useState('')
  const [sort, setSort] = useState('-overall')
  const [page, setPage] = useState(1)
  const dq = useDebounce(q)
  const id = assignmentId ? Number(assignmentId) : null

  // silent polling every 1.5 s gives real-time progress (cheap request, no loading flicker)
  const jobs = useFetch(() => api.get<Job[]>(`/assignments/${id}/jobs`).then((r) => r.data), [id], { enabled: !!id, intervalMs: 1500 })
  const active = jobs.data?.find((j) => j.status === 'queued' || j.status === 'running')
  const results = useFetch(() => api.get<Page<ResultSummary>>(`/assignments/${id}/results`, { params: { q: dq || undefined, risk: risk || undefined, review_status: review || undefined, sort, page, page_size: 20 } }).then((r) => r.data),
    [id, dq, risk, review, sort, page, jobs.data?.[0]?.status], { enabled: !!id })
  const matrix = useFetch(() => api.get<{ submissions: { id: number; label: string }[]; cells: { a: number; b: number; score: number; result_id: number }[] }>(`/assignments/${id}/matrix`).then((r) => r.data),
    [id, jobs.data?.[0]?.status], { enabled: !!id && tab === 'heatmap' })

  const start = async () => {
    setStarting(true)
    try {
      await api.post(`/assignments/${id}/analyze`, { include_history: history, include_other_assignments: cross, review_threshold: threshold ? +threshold / 100 : null })
      toast.success('Analysis started'); jobs.reload()
    } catch (e) { toast.error(errMsg(e)) } finally { setStarting(false) }
  }
  const latest = jobs.data?.[0]

  return (
    <>
      <PageHeader title="Plagiarism analysis" subtitle="Run batch comparisons, review flagged pairs and explore similarity" />
      <Card className="mb-4 p-4">
        <Field label="Assignment">
          <select className="input" value={assignmentId ?? ''} onChange={(e) => { setPage(1); nav(`/app/analysis/${e.target.value}`) }}>
            <option value="">Select an assignment…</option>{(assignments.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.title} — {a.submission_count} submissions</option>)}
          </select>
        </Field>
      </Card>
      {!id ? <Card><EmptyState icon={<FlaskConical className="h-6 w-6" />} title="Choose an assignment" text="Select an assignment above to run or review an analysis." /></Card> : (
        <div className="space-y-4">
          <Card className="space-y-4 p-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={history} onChange={(e) => setHistory(e.target.checked)} />Compare with my earlier assignments (history)</label>
              {user?.role_name === 'admin' && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={cross} onChange={(e) => setCross(e.target.checked)} />Cross-assignment (all instructors)</label>}
              <Field label="Review threshold override (%)"><input className="input" type="number" min={1} max={100} placeholder="default" value={threshold} onChange={(e) => setThreshold(e.target.value)} /></Field>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={start} loading={starting} disabled={!!active}><Play className="h-4 w-4" />Run batch analysis</Button>
              <Button variant="secondary" onClick={() => downloadFile(`/assignments/${id}/report.pdf`, 'assignment-report.pdf').catch((e) => toast.error(errMsg(e)))}><Download className="h-4 w-4" />PDF report</Button>
              <Button variant="secondary" onClick={() => downloadFile(`/assignments/${id}/export.csv`, 'assignment.csv').catch((e) => toast.error(errMsg(e)))}><Download className="h-4 w-4" />CSV</Button>
            </div>
            {latest && (
              <div aria-live="polite">
                <div className="mb-1.5 flex items-center justify-between text-sm"><span className="flex items-center gap-2">Latest job #{latest.id} <StatusBadge status={latest.status} /></span><span className="text-slate-500">{latest.done_pairs}/{latest.total_pairs} pairs · {fmtDate(latest.finished_at ?? latest.started_at ?? latest.created_at)}</span></div>
                <ProgressBar value={latest.progress} tone={latest.status === 'failed' ? 'red' : latest.status === 'completed' ? 'green' : 'brand'} />
                {latest.error && <p className="mt-2 text-sm text-red-600">{latest.error}</p>}
              </div>)}
          </Card>
          <Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: 'results', label: 'Results' }, { id: 'heatmap', label: 'Similarity heat-map' }]} />
          {tab === 'heatmap' ? (
            <Card>{matrix.loading ? <Spinner /> : matrix.error ? <ErrorBox message={matrix.error} /> : <Heatmap submissions={matrix.data?.submissions ?? []} cells={matrix.data?.cells ?? []} />}</Card>
          ) : (
            <Card>
              <div className="grid gap-2 border-b border-slate-100 p-4 sm:grid-cols-4 dark:border-navy-800">
                <input className="input sm:col-span-2" placeholder="Search student" aria-label="Search student" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
                <select className="input" aria-label="Risk" value={risk} onChange={(e) => { setRisk(e.target.value); setPage(1) }}><option value="">Any risk</option><option>high</option><option>medium</option><option>low</option></select>
                <select className="input" aria-label="Review status" value={review} onChange={(e) => { setReview(e.target.value); setPage(1) }}><option value="">Any review status</option>{['pending', 'flagged', 'confirmed', 'dismissed'].map((s) => <option key={s}>{s}</option>)}</select>
              </div>
              {results.loading && !results.data ? <Spinner /> : results.error ? <div className="p-4"><ErrorBox message={results.error} onRetry={results.reload} /></div> : (
                <>
                  <DataTable rows={results.data?.items ?? []} rowKey={(r) => r.id} sort={sort} onSort={setSort} onRowClick={(r) => nav(`/app/compare/${r.id}`)}
                    empty={<EmptyState title="No results" text="Run an analysis (at least two students' submissions are required)." />}
                    columns={[
                      { key: 'pair', header: 'Pair', primary: true, render: (r) => <span className="font-medium">{r.student_a} ↔ {r.student_b}</span> },
                      { key: 'overall', header: 'Similarity', sortKey: 'overall', render: (r) => <strong>{pct(r.effective_score)}</strong> },
                      { key: 'risk_level', header: 'Risk', render: (r) => <RiskBadge level={r.risk_level} /> },
                      { key: 'confidence_label', header: 'Confidence', sortKey: 'confidence', render: (r) => r.confidence_label },
                      { key: 'dup', header: 'Flags', render: (r) => r.is_duplicate ? <Badge tone="red">identical</Badge> : '—' },
                      { key: 'review_status', header: 'Review', sortKey: 'review_status', render: (r) => <StatusBadge status={r.review_status} /> },
                    ]} />
                  <Pagination page={page} pageSize={20} total={results.data?.total ?? 0} onChange={setPage} />
                </>)}
            </Card>)}
        </div>)}
    </>
  )
}
