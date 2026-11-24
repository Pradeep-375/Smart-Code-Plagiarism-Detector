import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck } from 'lucide-react'
import clsx from 'clsx'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { Button, Card, EmptyState, ErrorBox, PageHeader, Pagination, Spinner } from '../components/ui'
import { timeAgo } from '../utils/format'
import type { Notification, Page } from '../types'

export default function Notifications() {
  const nav = useNavigate()
  const [page, setPage] = useState(1)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const { data, loading, error, reload } = useFetch(() => api.get<Page<Notification>>('/notifications', { params: { page, page_size: 15, unread_only: unreadOnly } }).then((r) => r.data), [page, unreadOnly])
  const open = async (n: Notification) => {
    if (!n.is_read) await api.post(`/notifications/${n.id}/read`).catch(() => undefined)
    if (n.link) nav(n.link.replace(/^\/assignments\/(\d+)\/analysis/, '/app/analysis/$1').replace(/^\/assignments\//, '/app/assignments/'))
    else reload()
  }
  return (
    <>
      <PageHeader title="Notifications" subtitle={data?.unread ? `${data.unread} unread` : 'You are all caught up'}
        actions={<><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1) }} />Unread only</label>
          <Button variant="secondary" onClick={async () => { await api.post('/notifications/read-all'); reload() }}><CheckCheck className="h-4 w-4" />Mark all read</Button></>} />
      <Card>
        {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} /></div> : !data?.items.length ? <EmptyState icon={<Bell className="h-6 w-6" />} title="No notifications" /> : (
          <>
            <ul className="divide-y divide-slate-100 dark:divide-navy-800">{data.items.map((n) => (
              <li key={n.id}><button onClick={() => open(n)} className={clsx('flex w-full items-start gap-3 px-4 py-4 text-left hover:bg-slate-50 dark:hover:bg-navy-800/50', !n.is_read && 'bg-brand-50/60 dark:bg-brand-900/10')}>
                <span className={clsx('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', n.is_read ? 'bg-transparent' : 'bg-brand-500')} />
                <span className="min-w-0 flex-1"><span className="block font-medium">{n.title}</span><span className="block text-sm text-slate-600 dark:text-slate-400">{n.message}</span></span>
                <span className="shrink-0 text-xs text-slate-500">{timeAgo(n.created_at)}</span></button></li>))}</ul>
            <Pagination page={page} pageSize={15} total={data.total} onChange={setPage} />
          </>)}
      </Card>
    </>
  )
}
