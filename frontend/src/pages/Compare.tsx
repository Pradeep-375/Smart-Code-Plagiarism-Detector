import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ChevronLeft, ChevronRight, Download, Info } from 'lucide-react'
import clsx from 'clsx'
import { api, downloadFile, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useToast } from '../contexts/ToastContext'
import CodePane from '../components/CodePane'
import { Badge, Button, Card, ErrorBox, Field, PageHeader, ProgressBar, RiskBadge, Spinner, StatusBadge, Tabs } from '../components/ui'
import { ALGO_LABELS, fmtDate, pct } from '../utils/format'
import type { ResultDetail, ReviewStatus } from '../types'

type MTab = 'a' | 'b' | 'matches' | 'scores'

export default function Compare() {
  const { resultId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const mobile = useIsMobile()
  const { data, loading, error, reload } = useFetch(() => api.get<ResultDetail>(`/results/${resultId}`).then((r) => r.data), [resultId])
  const [fileA, setFileA] = useState(0)
  const [fileB, setFileB] = useState(0)
  const [active, setActive] = useState(0)
  const [mtab, setMtab] = useState<MTab>('matches')
  const [status, setStatus] = useState<ReviewStatus>('pending')
  const [notes, setNotes] = useState('')
  const [override, setOverride] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { if (data) { setStatus(data.review_status); setNotes(data.review_notes); setOverride(data.override_score != null ? String(Math.round(data.override_score * 100)) : '') } }, [data])

  const A = data?.files_a[fileA], B = data?.files_b[fileB]
  const segs = useMemo(() => (data?.segments ?? []).filter((s) => s.a_file === A?.filename && s.b_file === B?.filename), [data, A, B])
  const cur = segs[Math.min(active, Math.max(0, segs.length - 1))]
  useEffect(() => setActive(0), [fileA, fileB])
  // when the active match is in a different file pair, jump to it
  const jump = (idx: number, all = data?.segments ?? []) => {
    const s = all[idx]; if (!s || !data) return
    setFileA(Math.max(0, data.files_a.findIndex((f) => f.filename === s.a_file)))
    setFileB(Math.max(0, data.files_b.findIndex((f) => f.filename === s.b_file)))
  }

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? 'Not found'} onRetry={reload} />

  const step = (d: number) => { if (segs.length) setActive((a) => (a + d + segs.length) % segs.length) }
  const save = async () => {
    setSaving(true)
    try {
      await api.patch(`/results/${data.id}/review`, { review_status: status, notes, override_score: override ? +override / 100 : null })
      toast.success('Review saved'); reload()
    } catch (e) { toast.error(errMsg(e)) } finally { setSaving(false) }
  }
  const nonZero = (n: number) => (n > 0 ? n : 1)

  const matches = (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold">Matching sections <span className="text-slate-500">({segs.length})</span></h2>
        <div className="flex gap-1"><Button size="sm" variant="secondary" onClick={() => step(-1)} aria-label="Previous match"><ChevronLeft className="h-4 w-4" /></Button><Button size="sm" variant="secondary" onClick={() => step(1)} aria-label="Next match"><ChevronRight className="h-4 w-4" /></Button></div>
      </div>
      {segs.length === 0 ? <p className="text-sm text-slate-500">No matching blocks between these two files.</p> : (
        <ol className="max-h-64 space-y-1.5 overflow-auto">
          {segs.map((s, i) => (
            <li key={s.id}><button onClick={() => setActive(i)} className={clsx('w-full rounded-lg border px-3 py-2 text-left text-xs transition', i === active ? 'border-amber-400 bg-amber-50 dark:bg-amber-500/10' : 'border-slate-200 hover:bg-slate-50 dark:border-navy-700 dark:hover:bg-navy-800')}>
              <div className="font-medium">#{i + 1} · {s.token_count} tokens</div>
              <div className="text-slate-500">A: lines {s.a_start_line}–{s.a_end_line} · B: lines {s.b_start_line}–{s.b_end_line}</div></button></li>))}
        </ol>)}
      {data.segments.length > segs.length && (
        <div className="mt-2 text-xs text-slate-500">Other file pairs: {Array.from(new Set(data.segments.filter((s) => s.a_file !== A?.filename || s.b_file !== B?.filename).map((s) => `${s.a_file} ↔ ${s.b_file}`))).map((l) => <button key={l} className="mr-2 underline" onClick={() => jump(data.segments.findIndex((s) => `${s.a_file} ↔ ${s.b_file}` === l))}>{l}</button>)}</div>)}
    </Card>
  )

  const scores = (
    <Card className="space-y-4 p-4">
      <div><h2 className="mb-2 font-semibold">Algorithm scores</h2>
        <div className="space-y-2.5">{Object.entries(data.scores).map(([k, v]) => (
          <div key={k}><div className="mb-1 flex justify-between text-xs"><span>{ALGO_LABELS[k] ?? k}</span><span className="font-semibold">{pct(v)}</span></div><ProgressBar value={v} tone={v >= 0.75 ? 'red' : v >= 0.5 ? 'amber' : 'brand'} /></div>))}</div></div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-slate-50 p-3 dark:bg-navy-800"><div className="text-xs text-slate-500">Confidence</div><div className="font-semibold capitalize">{data.confidence_label} ({pct(data.confidence)})</div></div>
        {data.ml_probability != null && <div className="rounded-xl bg-slate-50 p-3 dark:bg-navy-800"><div className="text-xs text-slate-500">ML layer (supplementary)</div><div className="font-semibold">{pct(data.ml_probability)}</div></div>}
      </div>
    </Card>
  )

  const explain = (
    <Card className="p-4">
      <h2 className="mb-2 flex items-center gap-2 font-semibold"><Info className="h-4 w-4 text-brand-500" />Why was this flagged?</h2>
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700 dark:text-slate-300">{data.explanations.map((e, i) => <li key={i}>{e}</li>)}</ul>
    </Card>
  )

  const reviewCard = (
    <Card className="space-y-3 p-4">
      <h2 className="font-semibold">Faculty review</h2>
      <p className="text-xs text-slate-500">{data.reviewed_at ? `Last reviewed ${fmtDate(data.reviewed_at)}${data.reviewer_name ? ` by ${data.reviewer_name}` : ''}` : 'Not reviewed yet.'}</p>
      <Field label="Decision"><select className="input" value={status} onChange={(e) => setStatus(e.target.value as ReviewStatus)}>
        <option value="pending">Pending</option><option value="dismissed">Dismissed – no concern</option><option value="flagged">Flagged – investigate further</option><option value="confirmed">Confirmed – copying</option></select></Field>
      <Field label="Notes" hint="Required (min. 5 characters) for dismissed or confirmed."><textarea className="input min-h-[80px]" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <Field label="Override similarity (%)" hint="Optional manual adjustment of the score."><input type="number" min={0} max={100} className="input" value={override} onChange={(e) => setOverride(e.target.value)} /></Field>
      <Button onClick={save} loading={saving} className="w-full">Save review</Button>
    </Card>
  )

  return (
    <>
      <PageHeader title={`${data.student_a} ↔ ${data.student_b}`} subtitle={data.assignment_title}
        actions={<><Button variant="secondary" onClick={() => nav(-1)}><ArrowLeft className="h-4 w-4" />Back</Button>
          <Button variant="secondary" onClick={() => downloadFile(`/results/${data.id}/report.pdf`, `report-${data.id}.pdf`).catch((e) => toast.error(errMsg(e)))}><Download className="h-4 w-4" />PDF</Button></>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="text-3xl font-extrabold text-slate-900 dark:text-white">{pct(data.effective_score)}</div>
        <RiskBadge level={data.risk_level} /><StatusBadge status={data.review_status} />
        {data.is_duplicate && <Badge tone="red">identical submissions</Badge>}
        {data.override_score != null && <Badge tone="blue">score overridden (auto {pct(data.overall)})</Badge>}
      </div>
      <div role="note" className="mb-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">{data.disclaimer}</div>

      {mobile ? (
        <div className="space-y-3">
          <Tabs<MTab> value={mtab} onChange={setMtab} tabs={[{ id: 'matches', label: 'Matches' }, { id: 'a', label: 'Code A' }, { id: 'b', label: 'Code B' }, { id: 'scores', label: 'Scores' }]} />
          {(mtab === 'a' || mtab === 'b') && <FileSelect files={mtab === 'a' ? data.files_a : data.files_b} value={mtab === 'a' ? fileA : fileB} onChange={mtab === 'a' ? setFileA : setFileB} />}
          {mtab === 'a' && A && <CodePane label="code-a" code={A.content} language={A.language_key} ranges={segs.map((s) => ({ start: s.a_start_line, end: nonZero(s.a_end_line) }))} activeIndex={active} />}
          {mtab === 'b' && B && <CodePane label="code-b" code={B.content} language={B.language_key} ranges={segs.map((s) => ({ start: s.b_start_line, end: nonZero(s.b_end_line) }))} activeIndex={active} />}
          {mtab === 'matches' && <>{matches}{explain}{reviewCard}</>}
          {mtab === 'scores' && scores}
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-4 xl:col-span-2">
            <div className="grid gap-3 md:grid-cols-2">
              <div><FileSelect files={data.files_a} value={fileA} onChange={setFileA} label={`${data.student_a}`} />
                {A && <CodePane label="code-a" code={A.content} language={A.language_key} ranges={segs.map((s) => ({ start: s.a_start_line, end: nonZero(s.a_end_line) }))} activeIndex={active} />}</div>
              <div><FileSelect files={data.files_b} value={fileB} onChange={setFileB} label={`${data.student_b}`} />
                {B && <CodePane label="code-b" code={B.content} language={B.language_key} ranges={segs.map((s) => ({ start: s.b_start_line, end: nonZero(s.b_end_line) }))} activeIndex={active} />}</div>
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-slate-500"><span><i className="mr-1 inline-block h-3 w-3 rounded bg-brand-300/60" />Matching block</span><span><i className="mr-1 inline-block h-3 w-3 rounded bg-amber-300/70" />Selected match</span><span>Unhighlighted lines differ</span>{cur && <span>Current: A {cur.a_start_line}–{cur.a_end_line} ↔ B {cur.b_start_line}–{cur.b_end_line}</span>}</div>
            {explain}
          </div>
          <div className="space-y-4">{matches}{scores}{reviewCard}</div>
        </div>)}
    </>
  )
}

function FileSelect({ files, value, onChange, label }: { files: { id: number; filename: string }[]; value: number; onChange: (i: number) => void; label?: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      {label && <span className="truncate text-sm font-semibold">{label}</span>}
      <select aria-label="Select file" className="input ml-auto w-auto max-w-[60%] py-1.5 text-xs" value={value} onChange={(e) => onChange(+e.target.value)}>{files.map((f, i) => <option key={f.id} value={i}>{f.filename}</option>)}</select>
    </div>
  )
}
