import { FormEvent, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { api, errMsg } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import { useDebounce } from '../hooks/useDebounce'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { Badge, Button, Card, DataTable, ErrorBox, Field, Modal, PageHeader, Pagination, Spinner } from '../components/ui'
import { fmtDate } from '../utils/format'
import type { Page, Role, User } from '../types'

export default function UsersPage() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const dq = useDebounce(q)
  const { data, loading, error, reload } = useFetch(() => api.get<Page<User>>('/users', { params: { q: dq || undefined, role: role || undefined, page, page_size: 15 } }).then((r) => r.data), [dq, role, page])
  const [f, setF] = useState({ full_name: '', email: '', password: '', role: 'faculty' as Role })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const create = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { await api.post('/users', f); toast.success('User created'); setOpen(false); setF({ full_name: '', email: '', password: '', role: 'faculty' }); reload() } catch (x) { setErr(errMsg(x)) } finally { setBusy(false) }
  }
  const patch = async (u: User, body: Partial<{ role: Role; is_active: boolean }>) => {
    try { await api.patch(`/users/${u.id}`, body); toast.success('User updated'); reload() } catch (x) { toast.error(errMsg(x)) }
  }
  return (
    <>
      <PageHeader title="User management" subtitle="Manage instructors, students and administrators" actions={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Add user</Button>} />
      <Card>
        <div className="flex flex-col gap-2 border-b border-slate-100 p-4 sm:flex-row dark:border-navy-800">
          <div className="relative flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" /><input className="input pl-9" placeholder="Search name or email" aria-label="Search users" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
          <select className="input sm:w-40" aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value); setPage(1) }}><option value="">All roles</option><option>admin</option><option>faculty</option><option>student</option></select>
        </div>
        {loading && !data ? <Spinner /> : error ? <div className="p-4"><ErrorBox message={error} onRetry={reload} /></div> : (
          <>
            <DataTable rows={data?.items ?? []} rowKey={(u) => u.id}
              columns={[
                { key: 'full_name', header: 'Name', primary: true, render: (u) => <div><div className="font-medium">{u.full_name}</div><div className="text-xs text-slate-500">{u.email}</div></div> },
                { key: 'role_name', header: 'Role', render: (u) => (
                  <select aria-label={`Role of ${u.full_name}`} className="input w-auto py-1 text-xs capitalize" value={u.role_name} disabled={u.id === me?.id} onChange={(e) => patch(u, { role: e.target.value as Role })}>
                    <option value="admin">admin</option><option value="faculty">faculty</option><option value="student">student</option></select>) },
                { key: 'created_at', header: 'Joined', render: (u) => fmtDate(u.created_at, false) },
                { key: 'last_login_at', header: 'Last login', hideOnMobile: true, render: (u) => fmtDate(u.last_login_at) },
                { key: 'is_active', header: 'Status', render: (u) => (
                  <span className="flex items-center gap-2"><Badge tone={u.is_active ? 'green' : 'slate'}>{u.is_active ? 'active' : 'disabled'}</Badge>
                    {u.id !== me?.id && <button className="text-xs text-brand-600 underline" onClick={() => patch(u, { is_active: !u.is_active })}>{u.is_active ? 'Disable' : 'Enable'}</button>}</span>) },
              ]} />
            <Pagination page={page} pageSize={15} total={data?.total ?? 0} onChange={setPage} />
          </>)}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title="Add user">
        <form onSubmit={create} className="space-y-4">
          {err && <ErrorBox message={err} />}
          <Field label="Full name"><input className="input" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
          <Field label="Email"><input className="input" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Role"><select className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as Role })}><option value="faculty">Faculty</option><option value="student">Student</option><option value="admin">Administrator</option></select></Field>
          <Field label="Temporary password" hint="At least 8 characters with a letter and a digit."><input className="input" type="password" required minLength={8} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete="new-password" /></Field>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" loading={busy}>Create user</Button></div>
        </form>
      </Modal>
    </>
  )
}
