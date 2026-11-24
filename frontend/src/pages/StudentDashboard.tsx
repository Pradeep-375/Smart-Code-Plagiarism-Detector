import { Link } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Clock, FileCode2 } from 'lucide-react'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Badge, Card, EmptyState, ErrorBox, PageHeader, Spinner, StatCard, StatusBadge } from '../components/ui'
import { StatusPie } from '../components/charts'
import { fmtDate, LANG_LABELS } from '../utils/format'
import type { StudentDashboard as Data } from '../types'

export default function StudentDashboard() {
  const { data, loading, error, reload } = useFetch(() => api.get<Data>('/dashboard/student').then((r) => r.data), [])
  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? 'No data'} onRetry={reload} />
  return (
    <>
      <PageHeader title="My dashboard" subtitle="Your tasks and submissions" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="To do" value={data.totals.assignments_to_do} icon={<Clock className="h-5 w-5" />} tone="amber" />
        <StatCard label="Submissions" value={data.totals.submissions} icon={<FileCode2 className="h-5 w-5" />} />
        <StatCard label="Analysed" value={data.totals.analyzed} icon={<CheckCircle2 className="h-5 w-5" />} tone="green" />
        <StatCard label="Late" value={data.totals.late_submissions} icon={<AlertCircle className="h-5 w-5" />} tone="red" />
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-3 font-semibold">Assigned tasks</h2>
          {data.todo.length === 0 ? <EmptyState title="All caught up" text="No open assignments waiting for you." /> : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {data.todo.map((t) => (
                <li key={t.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0"><div className="truncate font-medium">{t.title}</div><div className="text-xs text-slate-500">{LANG_LABELS[t.language_key]} · due {fmtDate(t.deadline)}</div></div>
                  <div className="flex shrink-0 items-center gap-2">{t.overdue && <Badge tone="red">overdue</Badge>}<Link className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white" to={`/app/submit/${t.id}`}>Submit</Link></div>
                </li>))}
            </ul>)}
        </Card>
        <Card className="p-5"><h2 className="mb-2 font-semibold">Submission status</h2><StatusPie data={data.status_distribution} /></Card>
        <Card className="p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Recent submissions</h2><Link to="/app/submit" className="text-sm text-brand-600">View history</Link></div>
          {data.recent.length === 0 ? <p className="text-sm text-slate-500">You haven't submitted anything yet.</p> : (
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">
              {data.recent.map((s) => (
                <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                  <span className="font-medium">{s.assignment_title} <span className="text-slate-500">v{s.version}</span></span>
                  <span className="flex items-center gap-2 text-xs text-slate-500">{fmtDate(s.submitted_at)}{s.is_late && <Badge tone="red">late</Badge>}<StatusBadge status={s.status} /></span>
                </li>))}
            </ul>)}
        </Card>
      </div>
    </>
  )
}
