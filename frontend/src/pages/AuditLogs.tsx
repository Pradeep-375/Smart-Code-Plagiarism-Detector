import { useState } from 'react'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useDebounce } from '../hooks/useDebounce'
import { Badge, Card, DataTable, ErrorBox, PageHeader, Pagination, Spinner } from '../components/ui'
import { fmtDate } from '../utils/format'
import type { AuditLog, Page } from '../types'

const GROUPS = ['auth', 'user', 'assignment', 'submission', 'analysis', 'result', 'report', 'settings', 'language']

export default function AuditLogs() {
  const [q, setQ] = useState('')
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)
  const dq = useDebounce(q)
  const { data, loading, error, reload } = useFetch(() => api.get<Page<AuditLog>>('/admin/audit-logs', { params: { q: dq || undefined, action: action || undefined, page, page_size: 25 } }).then((r) => r.data), [dq, action, page], { intervalMs: 15000 })
  return (
    <>
      <PageHeader title="Audit logs" subtitle="Security-relevant activity across the platform" />
      <Card>
        <div className="flex flex-col gap-2 border-b border-slate-100 p-4 sm:flex-row dark:border-navy-800">
          <input className="input flex-1" placeholder="Search actions" aria-label="Search audit logs" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
          <select className="input sm:w-48" aria-label="Category" value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }}><option value="">All categories</option>{GROUPS.map((g) => <option key={g}>{g}</option>)}</select>
        </div>
        {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div> : (
          <>
            <DataTable rows={data?.items ?? []} rowKey={(l) => l.id}
              columns={[
                { key: 'action', header: 'Action', primary: true, render: (l) => <Badge tone="blue">{l.action}</Badge> },
                { key: 'user_email', header: 'User', render: (l) => l.user_email ?? 'system' },
                { key: 'entity', header: 'Entity', render: (l) => (l.entity_type ? `${l.entity_type} #${l.entity_id ?? ''}` : '—') },
                { key: 'ip_address', header: 'IP', hideOnMobile: true, render: (l) => l.ip_address ?? '—' },
                { key: 'created_at', header: 'When', render: (l) => fmtDate(l.created_at) },
                { key: 'details', header: 'Details', hideOnMobile: true, render: (l) => <code className="text-xs text-slate-500">{Object.keys(l.details).length ? JSON.stringify(l.details).slice(0, 80) : '—'}</code> },
              ]} />
            <Pagination page={page} pageSize={25} total={data?.total ?? 0} onChange={setPage} />
          </>)}
      </Card>
    </>
  )
}
