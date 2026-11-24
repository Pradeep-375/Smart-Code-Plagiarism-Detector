import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, FlaskConical, Pencil, Trash2, Upload } from 'lucide-react'
import { api, downloadFile, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Badge, Button, Card, DataTable, EmptyState, ErrorBox, Field, Modal, PageHeader, Pagination, Spinner, StatusBadge, Tabs } from '../components/ui'
import { AssignmentForm } from './Assignments'
import { bytes, fmtDate, LANG_LABELS, pct } from '../utils/format'
import type { Assignment, Group, Page, Submission, User } from '../types'

type Tab = 'submissions' | 'groups' | 'reference' | 'upload'

export default function AssignmentDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('submissions')
  const [edit, setEdit] = useState(false)
  const a = useFetch(() => api.get<Assignment>(`/assignments/${id}`).then((r) => r.data), [id])
  if (a.loading) return <Spinner />
  if (a.error || !a.data) return <ErrorBox message={a.error ?? 'Not found'} />
  const as = a.data
  const remove = async () => {
    if (!confirm('Delete this assignment and all of its submissions and results? This cannot be undone.')) return
    try { await api.delete(`/assignments/${as.id}`); toast.success('Assignment deleted'); nav('/app/assignments') } catch (e) { toast.error(errMsg(e)) }
  }
  return (
    <>
      <PageHeader title={as.title} subtitle={`${LANG_LABELS[as.language_key]} · ${as.is_group ? 'Group' : 'Individual'} · due ${fmtDate(as.deadline)}`}
        actions={<>
          <Button onClick={() => nav(`/app/analysis/${as.id}`)}><FlaskConical className="h-4 w-4" />Analysis</Button>
          <Button variant="secondary" onClick={() => downloadFile(`/assignments/${as.id}/export.csv`, 'assignment.csv').catch((e) => toast.error(errMsg(e)))}><Download className="h-4 w-4" />CSV</Button>
          <Button variant="secondary" onClick={() => downloadFile(`/assignments/${as.id}/report.pdf`, 'assignment-report.pdf').catch((e) => toast.error(errMsg(e)))}><Download className="h-4 w-4" />PDF</Button>
          <Button variant="secondary" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" />Edit</Button>
          {(user?.role_name === 'admin' || as.created_by === user?.id) && <Button variant="danger" onClick={remove}><Trash2 className="h-4 w-4" /></Button>}
        </>} />
      {as.description && <Card className="mb-4 whitespace-pre-wrap p-4 text-sm text-slate-600 dark:text-slate-300">{as.description}</Card>}
      <div className="mb-4"><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: 'submissions', label: 'Submissions' }, { id: 'upload', label: 'Upload for student' }, ...(as.is_group ? [{ id: 'groups' as Tab, label: 'Groups' }] : []), { id: 'reference', label: 'Reference files' }]} /></div>
      {tab === 'submissions' && <Submissions assignmentId={as.id} />}
      {tab === 'upload' && <UploadForStudent assignmentId={as.id} onDone={() => setTab('submissions')} />}
      {tab === 'groups' && <Groups assignmentId={as.id} />}
      {tab === 'reference' && <Reference assignmentId={as.id} />}
      <Modal open={edit} onClose={() => setEdit(false)} title="Edit assignment" wide><AssignmentForm initial={as} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); a.reload() }} /></Modal>
    </>
  )
}

function Submissions({ assignmentId }: { assignmentId: number }) {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [sort, setSort] = useState('-submitted_at')
  const [latest, setLatest] = useState(true)
  const [page, setPage] = useState(1)
  const dq = useDebounce(q)
  const { data, loading, error, reload } = useFetch(() => api.get<Page<Submission>>(`/assignments/${assignmentId}/submissions`, { params: { q: dq || undefined, status: status || undefined, sort, latest_only: latest, page, page_size: 20 } }).then((r) => r.data), [assignmentId, dq, status, sort, latest, page])
  return (
    <Card>
      <div className="flex flex-col gap-2 border-b border-slate-100 p-4 sm:flex-row dark:border-navy-800">
        <input className="input flex-1" placeholder="Search by student name or email" aria-label="Search submissions" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} />
        <select className="input sm:w-40" aria-label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          <option value="">Any status</option>{['uploaded', 'queued', 'analyzing', 'analyzed', 'failed'].map((s) => <option key={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={latest} onChange={(e) => setLatest(e.target.checked)} />Latest versions only</label>
      </div>
      {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div> : (
        <>
          <DataTable rows={data?.items ?? []} rowKey={(s) => s.id} sort={sort} onSort={setSort}
            empty={<EmptyState title="No submissions yet" text="Students can submit from their dashboard, or upload on their behalf." />}
            columns={[
              { key: 'student_name', header: 'Student', primary: true, sortKey: 'student', render: (s) => <div><div className="font-medium">{s.student_name}</div><div className="text-xs text-slate-500">{s.student_email}</div></div> },
              { key: 'version', header: 'Version', render: (s) => `v${s.version}` },
              { key: 'files', header: 'Files', render: (s) => `${s.files.length} (${bytes(s.files.reduce((n, f) => n + f.size_bytes, 0))})` },
              { key: 'submitted_at', header: 'Submitted', sortKey: 'submitted_at', render: (s) => <>{fmtDate(s.submitted_at)} {s.is_late && <Badge tone="red">late</Badge>}</> },
              { key: 'status', header: 'Status', sortKey: 'status', render: (s) => <StatusBadge status={s.status} /> },
              { key: 'max_similarity', header: 'Max similarity', sortKey: 'similarity', render: (s) => <>{pct(s.max_similarity)} {s.duplicate_of_id && <Badge tone="red">duplicate</Badge>}</> },
            ]} />
          <Pagination page={page} pageSize={20} total={data?.total ?? 0} onChange={setPage} />
        </>)}
    </Card>
  )
}

function UploadForStudent({ assignmentId, onDone }: { assignmentId: number; onDone: () => void }) {
  const toast = useToast()
  const [q, setQ] = useState('')
  const dq = useDebounce(q)
  const students = useFetch(() => api.get<Page<User>>('/users', { params: { q: dq || undefined, page_size: 8 } }).then((r) => r.data.items), [dq])
  const [studentId, setStudentId] = useState<number | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const go = async () => {
    if (!studentId || !files.length) return
    const fd = new FormData(); fd.append('student_id', String(studentId)); files.forEach((f) => fd.append('files', f))
    setBusy(true)
    try { await api.post(`/assignments/${assignmentId}/submissions`, fd); toast.success('Submission uploaded'); onDone() } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }
  return (
    <Card className="space-y-4 p-5">
      <Field label="Find student"><input className="input" placeholder="Name or email" value={q} onChange={(e) => setQ(e.target.value)} /></Field>
      <div className="flex flex-wrap gap-2">{(students.data ?? []).map((s) => (
        <button key={s.id} onClick={() => setStudentId(s.id)} className={`rounded-xl border px-3 py-2 text-left text-sm ${studentId === s.id ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/30' : 'border-slate-200 dark:border-navy-700'}`}>
          <div className="font-medium">{s.full_name}</div><div className="text-xs text-slate-500">{s.email}</div></button>))}</div>
      <Field label="Source files or ZIP" hint=".py .java .c .cpp .js .ts .zip"><input type="file" multiple accept=".py,.java,.c,.cpp,.js,.ts,.zip" onChange={(e) => setFiles(Array.from(e.target.files ?? []))} className="input" /></Field>
      <Button onClick={go} loading={busy} disabled={!studentId || !files.length}><Upload className="h-4 w-4" />Upload submission</Button>
    </Card>
  )
}

function Groups({ assignmentId }: { assignmentId: number }) {
  const toast = useToast()
  const groups = useFetch(() => api.get<Group[]>(`/assignments/${assignmentId}/groups`).then((r) => r.data), [assignmentId])
  const [name, setName] = useState('')
  const [q, setQ] = useState('')
  const dq = useDebounce(q)
  const found = useFetch(() => api.get<Page<User>>('/users', { params: { q: dq || undefined, page_size: 8 } }).then((r) => r.data.items), [dq])
  const [members, setMembers] = useState<User[]>([])
  const create = async () => {
    try { await api.post(`/assignments/${assignmentId}/groups`, { name, member_ids: members.map((m) => m.id) }); setName(''); setMembers([]); groups.reload(); toast.success('Group created') } catch (e) { toast.error(errMsg(e)) }
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-3 p-5">
        <h2 className="font-semibold">Create group</h2>
        <Field label="Group name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Add members"><input className="input" placeholder="Search students" value={q} onChange={(e) => setQ(e.target.value)} /></Field>
        <div className="flex flex-wrap gap-1.5">{(found.data ?? []).filter((s) => !members.find((m) => m.id === s.id)).map((s) => <button key={s.id} className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50 dark:border-navy-700" onClick={() => setMembers([...members, s])}>+ {s.full_name}</button>)}</div>
        <div className="flex flex-wrap gap-1.5">{members.map((m) => <Badge key={m.id} tone="blue">{m.full_name} <button aria-label={`Remove ${m.full_name}`} onClick={() => setMembers(members.filter((x) => x.id !== m.id))}>×</button></Badge>)}</div>
        <Button onClick={create} disabled={!name.trim()}>Create group</Button>
      </Card>
      <Card className="p-5">
        <h2 className="mb-3 font-semibold">Groups</h2>
        {!groups.data?.length ? <p className="text-sm text-slate-500">No groups yet.</p> : groups.data.map((g) => (
          <div key={g.id} className="flex items-start justify-between gap-2 border-b border-slate-100 py-3 last:border-0 dark:border-navy-800">
            <div><div className="font-medium">{g.name}</div><div className="text-xs text-slate-500">{g.members.map((m) => m.full_name).join(', ') || 'No members'}</div></div>
            <button aria-label={`Delete ${g.name}`} className="p-2 text-red-600" onClick={async () => { await api.delete(`/assignments/${assignmentId}/groups/${g.id}`); groups.reload() }}><Trash2 className="h-4 w-4" /></button>
          </div>))}
      </Card>
    </div>
  )
}

function Reference({ assignmentId }: { assignmentId: number }) {
  const toast = useToast()
  const ref = useFetch(() => api.get<{ id: number; filename: string; size: number }[]>(`/assignments/${assignmentId}/reference-files`).then((r) => r.data), [assignmentId])
  const input = useRef<HTMLInputElement>(null)
  const upload = async (files: FileList | null) => {
    if (!files?.length) return
    const fd = new FormData(); Array.from(files).forEach((f) => fd.append('files', f))
    try { await api.post(`/assignments/${assignmentId}/reference-files`, fd); toast.success('Reference files uploaded'); ref.reload() } catch (e) { toast.error(errMsg(e)) }
  }
  return (
    <Card className="p-5">
      <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">Starter or template code you provided to students. Matches against these files are excluded so shared boilerplate is not counted as copying.</p>
      <input ref={input} type="file" multiple hidden accept=".py,.java,.c,.cpp,.js,.ts,.zip" onChange={(e) => upload(e.target.files)} />
      <Button variant="secondary" onClick={() => input.current?.click()}><Upload className="h-4 w-4" />Upload reference files</Button>
      <ul className="mt-4 divide-y divide-slate-100 text-sm dark:divide-navy-800">
        {(ref.data ?? []).map((r) => <li key={r.id} className="flex items-center justify-between py-2.5"><span>{r.filename} <span className="text-xs text-slate-500">({bytes(r.size)})</span></span>
          <button aria-label={`Delete ${r.filename}`} className="p-2 text-red-600" onClick={async () => { await api.delete(`/assignments/${assignmentId}/reference-files/${r.id}`); ref.reload() }}><Trash2 className="h-4 w-4" /></button></li>)}
      </ul>
    </Card>
  )
}
