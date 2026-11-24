import { FormEvent, useState } from 'react'
import { Monitor, Moon, Sun } from 'lucide-react'
import { api, errMsg } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { useFetch } from '../hooks/useFetch'
import { Badge, Button, Card, ErrorBox, Field, PageHeader, Spinner, Tabs } from '../components/ui'
import { ALGO_LABELS } from '../utils/format'
import type { DetectionSettings, Language } from '../types'

type Tab = 'profile' | 'security' | 'appearance' | 'system'

export default function Profile() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('profile')
  if (!user) return null
  return (
    <>
      <PageHeader title="Profile & settings" subtitle={user.email} />
      <div className="mb-4"><Tabs<Tab> value={tab} onChange={setTab} tabs={[{ id: 'profile', label: 'Profile' }, { id: 'security', label: 'Security' }, { id: 'appearance', label: 'Appearance' }, ...(user.role_name === 'admin' ? [{ id: 'system' as Tab, label: 'System configuration' }] : [])]} /></div>
      {tab === 'profile' && <ProfileForm />}
      {tab === 'security' && <PasswordForm />}
      {tab === 'appearance' && <Appearance />}
      {tab === 'system' && <SystemConfig />}
    </>
  )
}

function ProfileForm() {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const [f, setF] = useState({ full_name: user!.full_name, organization_id: user!.organization_id ?? '', email_notifications: user!.email_notifications })
  const [busy, setBusy] = useState(false)
  const save = async (e: FormEvent) => { e.preventDefault(); setBusy(true); try { await api.patch('/auth/me', f); await refresh(); toast.success('Profile updated') } catch (x) { toast.error(errMsg(x)) } finally { setBusy(false) } }
  return (
    <Card className="max-w-xl p-5"><form onSubmit={save} className="space-y-4">
      <Field label="Full name"><input className="input" required minLength={2} value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></Field>
      <Field label="Roll / employee ID"><input className="input" value={f.organization_id} onChange={(e) => setF({ ...f, organization_id: e.target.value })} /></Field>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.email_notifications} onChange={(e) => setF({ ...f, email_notifications: e.target.checked })} />Send me e-mail notifications</label>
      <div className="flex items-center gap-2 text-sm text-slate-500">Role: <Badge tone="blue">{user!.role_name}</Badge></div>
      <Button type="submit" loading={busy}>Save</Button></form></Card>
  )
}

function PasswordForm() {
  const toast = useToast()
  const [f, setF] = useState({ current_password: '', new_password: '' })
  const [busy, setBusy] = useState(false)
  const save = async (e: FormEvent) => { e.preventDefault(); setBusy(true); try { await api.post('/auth/change-password', f); setF({ current_password: '', new_password: '' }); toast.success('Password changed') } catch (x) { toast.error(errMsg(x)) } finally { setBusy(false) } }
  return (
    <Card className="max-w-xl p-5"><form onSubmit={save} className="space-y-4">
      <Field label="Current password"><input className="input" type="password" required autoComplete="current-password" value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} /></Field>
      <Field label="New password" hint="At least 8 characters with a letter and a digit."><input className="input" type="password" required minLength={8} autoComplete="new-password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></Field>
      <Button type="submit" loading={busy}>Change password</Button></form></Card>
  )
}

function Appearance() {
  const { theme, setTheme } = useTheme()
  const opts = [{ id: 'light', label: 'Light', icon: Sun }, { id: 'dark', label: 'Dark', icon: Moon }, { id: 'system', label: 'System', icon: Monitor }] as const
  return (
    <Card className="max-w-xl p-5"><h2 className="mb-3 font-semibold">Theme</h2>
      <div className="grid grid-cols-3 gap-3">{opts.map((o) => (
        <button key={o.id} onClick={() => setTheme(o.id)} aria-pressed={theme === o.id} className={`flex flex-col items-center gap-2 rounded-xl border p-4 text-sm font-medium ${theme === o.id ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-200' : 'border-slate-200 dark:border-navy-700'}`}><o.icon className="h-5 w-5" />{o.label}</button>))}</div></Card>
  )
}

function SystemConfig() {
  const toast = useToast()
  const settings = useFetch(() => api.get<DetectionSettings>('/admin/settings/detection').then((r) => r.data), [])
  const langs = useFetch(() => api.get<Language[]>('/languages', { params: { all: true } }).then((r) => r.data), [])
  const [w, setW] = useState<Record<string, number> | null>(null)
  const [th, setTh] = useState<{ review: number; high: number } | null>(null)
  if (settings.loading || langs.loading) return <Spinner />
  if (settings.error || !settings.data) return <ErrorBox message={settings.error ?? 'Failed to load'} />
  const weights = w ?? settings.data.weights
  const t = th ?? { review: Math.round(settings.data.review_threshold * 100), high: Math.round(settings.data.high_threshold * 100) }
  const total = Object.values(weights).reduce((a, b) => a + b, 0)
  const save = async () => {
    try { await api.put('/admin/settings/detection', { weights, review_threshold: t.review / 100, high_threshold: t.high / 100 }); toast.success('Detection settings saved'); settings.reload() } catch (x) { toast.error(errMsg(x)) }
  }
  const toggle = async (l: Language) => { try { await api.patch(`/admin/languages/${l.id}`, { key: l.key, name: l.name, extensions: l.extensions, enabled: !l.enabled }); langs.reload() } catch (x) { toast.error(errMsg(x)) } }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-4 p-5">
        <h2 className="font-semibold">Detection weights & thresholds</h2>
        <p className="text-xs text-slate-500">Weights are normalised when used (current sum {total.toFixed(2)}).</p>
        {settings.data.algorithms.map((a) => (
          <div key={a}><div className="flex justify-between text-sm"><label htmlFor={`w-${a}`}>{ALGO_LABELS[a] ?? a}</label><span className="font-mono text-xs">{(weights[a] ?? 0).toFixed(2)}</span></div>
            <input id={`w-${a}`} type="range" min={0} max={0.5} step={0.01} className="w-full accent-brand-600" value={weights[a] ?? 0} onChange={(e) => setW({ ...weights, [a]: +e.target.value })} /></div>))}
        <div className="grid grid-cols-2 gap-3">
          <Field label="Review threshold (%)"><input type="number" min={1} max={100} className="input" value={t.review} onChange={(e) => setTh({ ...t, review: +e.target.value })} /></Field>
          <Field label="High threshold (%)"><input type="number" min={1} max={100} className="input" value={t.high} onChange={(e) => setTh({ ...t, high: +e.target.value })} /></Field>
        </div>
        <div className="flex gap-2"><Button onClick={save}>Save settings</Button><Button variant="secondary" onClick={() => { setW(null); setTh(null) }}>Reset form</Button></div>
      </Card>
      <Card className="p-5"><h2 className="mb-3 font-semibold">Programming languages</h2>
        <ul className="divide-y divide-slate-100 dark:divide-navy-800">{(langs.data ?? []).map((l) => (
          <li key={l.id} className="flex items-center justify-between py-3"><div><div className="font-medium">{l.name}</div><div className="text-xs text-slate-500">{l.extensions}</div></div>
            <Button size="sm" variant={l.enabled ? 'secondary' : 'primary'} onClick={() => toggle(l)}>{l.enabled ? 'Disable' : 'Enable'}</Button></li>))}</ul></Card>
    </div>
  )
}
