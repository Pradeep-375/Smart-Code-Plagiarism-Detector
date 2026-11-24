import { FormEvent, ReactNode, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { GitCompare } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { api, errMsg } from '../services/api'
import { Button, ErrorBox, Field } from '../components/ui'

function Shell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-navy-950 via-navy-900 to-brand-900 px-4 py-10">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2 font-bold text-white"><div className="rounded-lg bg-brand-500 p-1.5"><GitCompare className="h-5 w-5" /></div>CodeIntegrity</Link>
        <div className="card p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{title}</h1>
          <p className="mb-6 mt-1 text-sm text-slate-500">{subtitle}</p>
          {children}
        </div>
        <p className="mt-5 text-center text-sm text-navy-200">{footer}</p>
      </div>
    </div>
  )
}

export function Login() {
  const { login, user } = useAuth()
  const nav = useNavigate()
  const loc = useLocation() as { state?: { from?: string } }
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/app/dashboard" replace />
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await login(email, password); nav(loc.state?.from ?? '/app/dashboard', { replace: true }) } catch (err) { setError(errMsg(err)) } finally { setBusy(false) }
  }
  return (
    <Shell title="Welcome back" subtitle="Sign in to your account" footer={<>New here? <Link className="font-semibold underline" to="/register">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorBox message={error} />}
        <Field label="Email"><input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
        <Field label="Password"><input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <div className="text-right text-sm"><Link className="text-brand-600 hover:underline" to="/forgot-password">Forgot password?</Link></div>
        <Button type="submit" loading={busy} className="w-full">Sign in</Button>
      </form>
    </Shell>
  )
}

export function Register() {
  const { register, user } = useAuth()
  const nav = useNavigate()
  const [role, setRole] = useState<'student' | 'faculty'>('student')
  const [f, setF] = useState({ full_name: '', email: '', organization_id: '', password: '', faculty_code: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/app/dashboard" replace />
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError('')
    try {
      const { faculty_code, ...rest } = f
      // the selected account type is sent explicitly; the server decides (and validates) the stored role
      await register({ ...rest, organization_id: f.organization_id || undefined, role, ...(role === 'faculty' ? { faculty_code } : {}) })
      nav('/app/dashboard', { replace: true })
    } catch (err) { setError(errMsg(err)) } finally { setBusy(false) }
  }
  const tab = (value: 'student' | 'faculty', label: string) => (
    <button type="button" role="tab" aria-selected={role === value} onClick={() => { setRole(value); setError('') }}
      className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition ${role === value ? 'bg-brand-600 text-white shadow' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'}`}>{label}</button>
  )
  return (
    <Shell title="Create account" subtitle="Administrator accounts are created by an existing administrator." footer={<>Already registered? <Link className="font-semibold underline" to="/login">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4">
        <div role="tablist" aria-label="Account type" className="flex gap-1 rounded-xl border border-slate-200 p-1 dark:border-slate-700">
          {tab('student', 'Register as Student')}
          {tab('faculty', 'Register as Faculty')}
        </div>
        {error && <ErrorBox message={error} />}
        <Field label="Full name"><input className="input" required minLength={2} value={f.full_name} onChange={set('full_name')} autoComplete="name" /></Field>
        <Field label="Email"><input className="input" type="email" required value={f.email} onChange={set('email')} autoComplete="email" /></Field>
        <Field label={role === 'faculty' ? 'Employee ID (optional)' : 'Roll number (optional)'}><input className="input" value={f.organization_id} onChange={set('organization_id')} /></Field>
        {role === 'faculty' && (
          <Field label="Faculty access code" hint="Provided by your institution's administrator."><input className="input" type="password" required value={f.faculty_code} onChange={set('faculty_code')} autoComplete="off" /></Field>
        )}
        <Field label="Password" hint="At least 8 characters with a letter and a digit."><input className="input" type="password" required minLength={8} value={f.password} onChange={set('password')} autoComplete="new-password" /></Field>
        <Button type="submit" loading={busy} className="w-full">{role === 'faculty' ? 'Create faculty account' : 'Create student account'}</Button>
      </form>
    </Shell>
  )
}

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await api.post('/auth/forgot-password', { email }); setDone(true) } catch (err) { setError(errMsg(err)) } finally { setBusy(false) }
  }
  return (
    <Shell title="Forgot password" subtitle="We'll email you a reset link." footer={<Link className="font-semibold underline" to="/login">Back to sign in</Link>}>
      {done ? <p className="rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">If that address is registered, a reset link has been sent. Check your inbox.</p> : (
        <form onSubmit={submit} className="space-y-4">
          {error && <ErrorBox message={error} />}
          <Field label="Email"><input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Button type="submit" loading={busy} className="w-full">Send reset link</Button>
        </form>)}
    </Shell>
  )
}

export function ResetPassword() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await api.post('/auth/reset-password', { token: params.get('token') ?? '', new_password: pw }); nav('/login') } catch (err) { setError(errMsg(err)) } finally { setBusy(false) }
  }
  return (
    <Shell title="Choose a new password" subtitle="Your reset link is valid for a short time." footer={<Link className="font-semibold underline" to="/login">Back to sign in</Link>}>
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorBox message={error} />}
        <Field label="New password" hint="At least 8 characters with a letter and a digit."><input className="input" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></Field>
        <Button type="submit" loading={busy} className="w-full">Update password</Button>
      </form>
    </Shell>
  )
}
