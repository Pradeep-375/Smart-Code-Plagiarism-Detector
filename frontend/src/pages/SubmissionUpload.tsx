import { DragEvent, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FileCode2, UploadCloud, X } from 'lucide-react'
import { api, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useToast } from '../contexts/ToastContext'
import { Badge, Button, Card, DataTable, EmptyState, ErrorBox, Field, PageHeader, Pagination, Spinner, StatusBadge } from '../components/ui'
import { bytes, fmtDate, LANG_LABELS, pct } from '../utils/format'
import type { Assignment, Feedback, Group, Page, Submission } from '../types'

const ACCEPT = ['.py', '.java', '.c', '.cpp', '.js', '.ts', '.zip']

export default function SubmissionUpload() {
  const { assignmentId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const assignments = useFetch(() => api.get<Page<Assignment>>('/assignments', { params: { page_size: 100 } }).then((r) => r.data.items), [])
  const selected = assignments.data?.find((a) => String(a.id) === assignmentId)
  const [files, setFiles] = useState<File[]>([])
  const [groupId, setGroupId] = useState('')
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)
  const [page, setPage] = useState(1)
  const input = useRef<HTMLInputElement>(null)
  const groups = useFetch(() => api.get<Group[]>(`/assignments/${assignmentId}/groups`).then((r) => r.data).catch(() => []), [assignmentId], { enabled: !!selected?.is_group })
  const history = useFetch(() => api.get<Page<Submission>>('/submissions/mine', { params: { page, page_size: 10 } }).then((r) => r.data), [page], { intervalMs: 5000 })
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({})

  const add = (list: FileList | File[]) => {
    const ok = Array.from(list).filter((f) => ACCEPT.some((e) => f.name.toLowerCase().endsWith(e)))
    if (ok.length !== Array.from(list).length) toast.error(`Only ${ACCEPT.join(' ')} files are accepted`)
    setFiles((cur) => [...cur, ...ok])
  }
  const onDrop = (e: DragEvent) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files) }
  const submit = async () => {
    if (!selected || !files.length) return
    const fd = new FormData(); files.forEach((f) => fd.append('files', f)); if (groupId) fd.append('group_id', groupId)
    setBusy(true)
    try { await api.post(`/assignments/${selected.id}/submissions`, fd); toast.success('Submission received'); setFiles([]); history.reload() } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }
  const loadFeedback = async (s: Submission) => {
    try { const { data } = await api.get<Feedback>(`/submissions/${s.id}/feedback`); setFeedback((f) => ({ ...f, [s.id]: data })) } catch (e) { toast.error(errMsg(e)) }
  }

  return (
    <>
      <PageHeader title="Submit code" subtitle="Upload source files or a ZIP. Uploaded code is never executed." />
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="space-y-4 p-5 lg:col-span-3">
          <Field label="Assignment">
            <select className="input" value={assignmentId ?? ''} onChange={(e) => nav(`/app/submit/${e.target.value}`)}>
              <option value="">Select an assignment…</option>
              {(assignments.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.title} ({LANG_LABELS[a.language_key]})</option>)}
            </select>
          </Field>
          {selected && <p className="text-xs text-slate-500">Accepts {LANG_LABELS[selected.language_key]} files · deadline {fmtDate(selected.deadline)}{selected.my_submission_count ? ` · you have ${selected.my_submission_count} previous submission(s); a new upload becomes the latest version` : ''}</p>}
          {selected?.is_group && (
            <Field label="Group"><select className="input" value={groupId} onChange={(e) => setGroupId(e.target.value)}><option value="">Select your group…</option>{(groups.data ?? []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></Field>)}
          <div onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)} onDrop={onDrop} onClick={() => input.current?.click()} role="button" tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && input.current?.click()}
            className={`flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-4 py-10 text-center transition ${drag ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-slate-300 dark:border-navy-700'}`}>
            <UploadCloud className="mb-2 h-8 w-8 text-brand-500" />
            <p className="text-sm font-medium">Tap to choose files or drag & drop</p>
            <p className="text-xs text-slate-500">{ACCEPT.join('  ')}</p>
            <input ref={input} type="file" multiple hidden accept={ACCEPT.join(',')} onChange={(e) => { if (e.target.files) add(e.target.files); e.target.value = '' }} />
          </div>
          {files.length > 0 && <ul className="space-y-1.5 text-sm">{files.map((f, i) => (
            <li key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-navy-800"><span className="flex min-w-0 items-center gap-2"><FileCode2 className="h-4 w-4 shrink-0 text-brand-500" /><span className="truncate">{f.name}</span><span className="text-xs text-slate-500">{bytes(f.size)}</span></span>
              <button aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}><X className="h-4 w-4" /></button></li>))}</ul>}
          <Button onClick={submit} loading={busy} disabled={!selected || !files.length || (selected.is_group && !groupId)} className="w-full sm:w-auto">Submit</Button>
        </Card>
        <Card className="p-5 text-sm text-slate-600 lg:col-span-2 dark:text-slate-300">
          <h2 className="mb-2 font-semibold text-slate-900 dark:text-white">Before you submit</h2>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>Submit your own work. Similarity to other submissions is checked automatically.</li>
            <li>Resubmitting creates a new version; the latest version is analysed.</li>
            <li>ZIP files may contain source files only (max 100 files).</li>
            <li>Similarity results are shown only if your instructor enables them, and never prove misconduct.</li>
          </ul>
        </Card>
      </div>
      <h2 className="mb-3 mt-8 text-lg font-semibold">Submission history</h2>
      <Card>
        {history.loading && !history.data ? <Spinner /> : history.error ? <div className="p-4"><ErrorBox message={history.error} /></div> : (
          <>
            <DataTable rows={history.data?.items ?? []} rowKey={(s) => s.id} empty={<EmptyState title="No submissions yet" />}
              columns={[
                { key: 'assignment_title', header: 'Assignment', primary: true },
                { key: 'version', header: 'Version', render: (s) => `v${s.version}` },
                { key: 'submitted_at', header: 'Submitted', render: (s) => <>{fmtDate(s.submitted_at)} {s.is_late && <Badge tone="red">late</Badge>}</> },
                { key: 'files', header: 'Files', render: (s) => s.files.map((f) => f.filename).join(', ') },
                { key: 'status', header: 'Analysis', render: (s) => <StatusBadge status={s.status} /> },
                { key: 'fb', header: 'Feedback', render: (s) => feedback[s.id] ? (
                  <span className="text-xs">{feedback[s.id].results_visible ? <><strong>{pct(feedback[s.id].max_similarity)}</strong> · </> : null}{feedback[s.id].message}</span>
                ) : <button className="text-xs text-brand-600 underline" onClick={(e) => { e.stopPropagation(); loadFeedback(s) }}>View</button> },
              ]} />
            <Pagination page={page} pageSize={10} total={history.data?.total ?? 0} onChange={setPage} />
          </>)}
      </Card>
    </>
  )
}
