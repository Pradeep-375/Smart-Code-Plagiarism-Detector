import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, FileText } from 'lucide-react'
import { api, downloadFile, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useToast } from '../contexts/ToastContext'
import { Button, Card, DataTable, EmptyState, Field, PageHeader, RiskBadge, Spinner, StatusBadge } from '../components/ui'
import { fmtDate, pct } from '../utils/format'
import type { Assignment, Page, ResultSummary } from '../types'

export default function Reports() {
  const toast = useToast()
  const nav = useNavigate()
  const [aid, setAid] = useState('')
  const assignments = useFetch(() => api.get<Page<Assignment>>('/assignments', { params: { page_size: 100 } }).then((r) => r.data.items), [])
  const top = useFetch(() => api.get<Page<ResultSummary>>(`/assignments/${aid}/results`, { params: { page_size: 25 } }).then((r) => r.data.items), [aid], { enabled: !!aid })
  const saved = useFetch(() => api.get<{ id: number; kind: string; result_id: number | null; created_at: string }[]>(`/assignments/${aid}/reports`).then((r) => r.data), [aid], { enabled: !!aid })
  const dl = (url: string, name: string) => downloadFile(url, name).then(() => saved.reload()).catch((e) => toast.error(errMsg(e)))
  return (
    <>
      <PageHeader title="Reports" subtitle="Download PDF and CSV reports for an assignment or an individual pair" />
      <Card className="mb-4 space-y-4 p-5">
        <Field label="Assignment"><select className="input" value={aid} onChange={(e) => setAid(e.target.value)}><option value="">Select…</option>{(assignments.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.title}</option>)}</select></Field>
        {aid && <div className="flex flex-wrap gap-2"><Button onClick={() => dl(`/assignments/${aid}/report.pdf`, 'assignment-report.pdf')}><Download className="h-4 w-4" />Assignment PDF</Button><Button variant="secondary" onClick={() => dl(`/assignments/${aid}/export.csv`, 'assignment.csv')}><Download className="h-4 w-4" />CSV export</Button></div>}
      </Card>
      {!aid ? <Card><EmptyState icon={<FileText className="h-6 w-6" />} title="Select an assignment" text="Choose an assignment to download its reports." /></Card> : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <div className="p-5 pb-2"><h2 className="font-semibold">Highest-similarity pairs</h2></div>
            {top.loading ? <Spinner /> : <DataTable rows={top.data ?? []} rowKey={(r) => r.id} empty={<EmptyState title="No analysis results yet" />}
              columns={[
                { key: 'pair', header: 'Pair', primary: true, render: (r) => `${r.student_a} ↔ ${r.student_b}` },
                { key: 'overall', header: 'Similarity', render: (r) => <strong>{pct(r.effective_score)}</strong> },
                { key: 'risk', header: 'Risk', render: (r) => <RiskBadge level={r.risk_level} /> },
                { key: 'review_status', header: 'Review', render: (r) => <StatusBadge status={r.review_status} /> },
                { key: 'act', header: '', render: (r) => <span className="flex gap-1"><Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); dl(`/results/${r.id}/report.pdf`, `report-${r.id}.pdf`) }}><Download className="h-3.5 w-3.5" />PDF</Button><Button size="sm" variant="ghost" onClick={() => nav(`/app/compare/${r.id}`)}>Open</Button></span> },
              ]} />}
          </Card>
          <Card className="p-5"><h2 className="mb-3 font-semibold">Generated reports</h2>
            {!saved.data?.length ? <p className="text-sm text-slate-500">Reports you generate are kept here.</p> : <ul className="divide-y divide-slate-100 text-sm dark:divide-navy-800">{saved.data.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2.5"><span>{r.kind === 'pair' ? 'Pair report' : 'Assignment report'}<span className="block text-xs text-slate-500">{fmtDate(r.created_at)}</span></span>
                <Button size="sm" variant="secondary" onClick={() => dl(`/reports/${r.id}/download`, `report-${r.id}.pdf`)}><Download className="h-3.5 w-3.5" /></Button></li>))}</ul>}
          </Card>
        </div>)}
    </>
  )
}
