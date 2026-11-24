import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Plus, Search } from 'lucide-react'
import { api, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Badge, Button, Card, DataTable, EmptyState, ErrorBox, Field, Modal, PageHeader, Pagination, Spinner } from '../components/ui'
import { fmtDate, LANG_LABELS } from '../utils/format'
import type { Assignment, Language, Page } from '../types'

export function AssignmentForm({ initial, onSaved, onClose }: { initial?: Assignment; onSaved: () => void; onClose: () => void }) {
  const toast = useToast()
  const langs = useFetch(() => api.get<Language[]>('/languages').then((r) => r.data), [])
  const [f, setF] = useState({
    title: initial?.title ?? '', description: initial?.description ?? '', language_key: initial?.language_key ?? 'python',
    deadline: initial?.deadline ? initial.deadline.slice(0, 16) : '', is_group: initial?.is_group ?? false, is_published: initial?.is_published ?? true,
    show_results_to_students: initial?.show_results_to_students ?? false,
    review_threshold: initial?.review_threshold != null ? String(Math.round(initial.review_threshold * 100)) : '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError('')
    const body = {
      title: f.title, description: f.description, language_key: f.language_key, is_group: f.is_group, is_published: f.is_published,
      show_results_to_students: f.show_results_to_students, deadline: f.deadline ? new Date(f.deadline).toISOString() : null,
      review_threshold: f.review_threshold ? +f.review_threshold / 100 : null,
    }
    try {
      initial ? await api.patch(`/assignments/${initial.id}`, body) : await api.post('/assignments', body)
      toast.success(initial ? 'Assignment updated' : 'Assignment created'); onSaved()
    } catch (err) { setError(errMsg(err)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      {error && <ErrorBox message={error} />}
      <Field label="Title"><input className="input" required minLength={3} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field>
      <Field label="Description"><textarea className="input min-h-[96px]" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Programming language">
          <select className="input" value={f.language_key} onChange={(e) => setF({ ...f, language_key: e.target.value })}>
            {(langs.data ?? []).map((l) => <option key={l.key} value={l.key}>{l.name}</option>)}
          </select>
        </Field>
        <Field label="Submission deadline"><input type="datetime-local" className="input" value={f.deadline} onChange={(e) => setF({ ...f, deadline: e.target.value })} /></Field>
      </div>
      <Field label="Review threshold (%)" hint="Optional. Overrides the system default for this assignment."><input type="number" min={1} max={100} className="input" value={f.review_threshold} onChange={(e) => setF({ ...f, review_threshold: e.target.value })} /></Field>
      <div className="space-y-2 text-sm">
        {([['is_group', 'Group assignment (students submit as teams)'], ['is_published', 'Published (visible to students)'], ['show_results_to_students', 'Show students an anonymous similarity band after analysis']] as const).map(([k, label]) => (
          <label key={k} className="flex items-center gap-2"><input type="checkbox" checked={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.checked })} className="h-4 w-4 rounded" />{label}</label>))}
      </div>
      <div className="flex justify-end gap-2 pt-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" loading={busy}>{initial ? 'Save changes' : 'Create assignment'}</Button></div>
    </form>
  )
}

export default function Assignments() {
  const { user } = useAuth()
  const nav = useNavigate()
  const staff = user?.role_name !== 'student'
  const [q, setQ] = useState('')
  const [language, setLanguage] = useState('')
  const [sort, setSort] = useState('-created_at')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const dq = useDebounce(q)
  const { data, loading, error, reload } = useFetch(
    () => api.get<Page<Assignment>>('/assignments', { params: { q: dq || undefined, language: language || undefined, sort, page, page_size: 15 } }).then((r) => r.data), [dq, language, sort, page])
  return (
    <>
      <PageHeader title="Assignments" subtitle={staff ? 'Create assignments, collect submissions and run analysis' : 'Programming tasks assigned to you'}
        actions={staff && <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />New assignment</Button>} />
      <Card>
        <div className="flex flex-col gap-2 border-b border-slate-100 p-4 sm:flex-row dark:border-navy-800">
          <div className="relative flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input className="input pl-9" placeholder="Search assignments" aria-label="Search assignments" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
          <select className="input sm:w-44" aria-label="Filter by language" value={language} onChange={(e) => { setLanguage(e.target.value); setPage(1) }}>
            <option value="">All languages</option>{Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div> : (
          <>
            <DataTable rows={data?.items ?? []} rowKey={(a) => a.id} sort={sort} onSort={setSort}
              onRowClick={(a) => nav(staff ? `/app/assignments/${a.id}` : `/app/submit/${a.id}`)}
              empty={<EmptyState icon={<BookOpen className="h-6 w-6" />} title="No assignments found" text={staff ? 'Create your first assignment to start collecting code.' : 'Nothing has been assigned yet.'} />}
              columns={[
                { key: 'title', header: 'Title', primary: true, sortKey: 'title', render: (a) => <span className="font-medium">{a.title}</span> },
                { key: 'language_key', header: 'Language', render: (a) => LANG_LABELS[a.language_key] ?? a.language_key },
                { key: 'deadline', header: 'Deadline', sortKey: 'deadline', render: (a) => fmtDate(a.deadline) },
                { key: 'type', header: 'Type', render: (a) => (a.is_group ? 'Group' : 'Individual') },
                staff ? { key: 'submission_count', header: 'Submissions' } : { key: 'my', header: 'My submissions', render: (a) => a.my_submission_count ?? 0 },
                { key: 'is_published', header: 'Status', render: (a) => <Badge tone={a.is_published ? 'green' : 'slate'}>{a.is_published ? 'published' : 'draft'}</Badge> },
              ]} />
            <Pagination page={page} pageSize={15} total={data?.total ?? 0} onChange={setPage} />
          </>)}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title="New assignment" wide><AssignmentForm onClose={() => setOpen(false)} onSaved={() => { setOpen(false); reload() }} /></Modal>
    </>
  )
}
