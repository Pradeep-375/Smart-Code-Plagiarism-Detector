import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, AlertTriangle, BarChart3, BookOpen, Clock, FileCode2, Users } from 'lucide-react'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Card, DataTable, EmptyState, ErrorBox, PageHeader, RiskBadge, Spinner, StatCard, StatusBadge } from './ui'
import { AssignmentBars, LanguagePie, MonthlyLine } from './charts'
import { LANG_LABELS, pct } from '../utils/format'
import type { StaffDashboard } from '../types'

export default function StaffDashboardView({ scope }: { scope: 'admin' | 'faculty' }) {
  const [days, setDays] = useState(365)
  const [language, setLanguage] = useState('')
  const nav = useNavigate()
  const { data, loading, error, reload } = useFetch(
    () => api.get<StaffDashboard>(`/dashboard/${scope}`, { params: { days, language: language || undefined } }).then((r) => r.data), [scope, days, language])

  const filters = (
    <>
      <select aria-label="Period" className="input w-auto" value={days} onChange={(e) => setDays(+e.target.value)}>
        <option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last 12 months</option><option value={3650}>All time</option>
      </select>
      <select aria-label="Language" className="input w-auto" value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option value="">All languages</option>{Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
    </>
  )
  return (
    <>
      <PageHeader title={scope === 'admin' ? 'System overview' : 'My courses overview'} subtitle={scope === 'admin' ? 'System-wide plagiarism statistics' : 'Statistics for your assignments'} actions={filters} />
      {loading && !data ? <Spinner /> : error ? <ErrorBox message={error} onRetry={reload} /> : data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {data.totals.users !== undefined && <StatCard label="Registered users" value={data.totals.users} icon={<Users className="h-5 w-5" />} />}
            <StatCard label="Assignments" value={data.totals.assignments} icon={<BookOpen className="h-5 w-5" />} />
            <StatCard label="Submissions" value={data.totals.submissions} icon={<FileCode2 className="h-5 w-5" />} />
            <StatCard label="Completed analyses" value={data.totals.completed_analyses} icon={<Activity className="h-5 w-5" />} tone="green" />
            <StatCard label="Pending analyses" value={data.totals.pending_analyses} hint={`${data.totals.unanalyzed_submissions} submissions unanalysed`} icon={<Clock className="h-5 w-5" />} tone="amber" />
            <StatCard label="Avg similarity" value={pct(data.totals.average_similarity, 1)} icon={<BarChart3 className="h-5 w-5" />} />
            <StatCard label="Cases to review" value={data.totals.high_similarity_cases} icon={<AlertTriangle className="h-5 w-5" />} tone="red" />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="p-5 lg:col-span-1"><h2 className="mb-2 font-semibold">Language distribution</h2><LanguagePie data={data.language_distribution} /></Card>
            <Card className="p-5 lg:col-span-2"><h2 className="mb-2 font-semibold">Monthly submissions</h2><MonthlyLine data={data.monthly_submissions} /></Card>
          </div>
          <Card className="p-5"><h2 className="mb-2 font-semibold">Assignment-wise plagiarism statistics</h2><AssignmentBars data={data.assignment_stats} /></Card>
          <Card>
            <div className="p-5 pb-2"><h2 className="font-semibold">High-similarity cases awaiting review</h2></div>
            <DataTable rowKey={(r) => r.id} onRowClick={(r) => nav(`/app/compare/${r.id}`)} rows={data.cases_for_review}
              empty={<EmptyState title="No cases waiting" text="Nothing above the review threshold needs your attention." />}
              columns={[
                { key: 'pair', header: 'Pair', primary: true, render: (r) => `${r.student_a} ↔ ${r.student_b}` },
                { key: 'assignment_title', header: 'Assignment' },
                { key: 'overall', header: 'Similarity', render: (r) => <strong>{pct(r.effective_score)}</strong> },
                { key: 'risk', header: 'Risk', render: (r) => <RiskBadge level={r.risk_level} /> },
                { key: 'review_status', header: 'Status', render: (r) => <StatusBadge status={r.review_status} /> },
              ]} />
          </Card>
          {data.users_by_role && <Card className="p-5"><h2 className="mb-2 font-semibold">Users by role</h2><div className="flex flex-wrap gap-3">{data.users_by_role.map((u) => <div key={u.role} className="rounded-xl bg-slate-100 px-4 py-2 text-sm capitalize dark:bg-navy-800">{u.role}: <strong>{u.count}</strong></div>)}</div></Card>}
        </div>
      )}
    </>
  )
}
