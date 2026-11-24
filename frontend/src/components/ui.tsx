import { ButtonHTMLAttributes, ReactNode, useEffect } from 'react'
import clsx from 'clsx'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight, Loader2, X } from 'lucide-react'
import { riskTone } from '../utils/format'

export function Button({ variant = 'primary', size = 'md', loading, className, children, disabled, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; loading?: boolean }) {
  const styles = {
    primary: 'bg-gradient-to-r from-brand-600 to-brand-700 text-white hover:from-brand-700 hover:to-brand-800 shadow-sm',
    secondary: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200 dark:hover:bg-navy-800',
    ghost: 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-navy-800',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }[variant]
  return (
    <button {...rest} disabled={disabled || loading}
      className={clsx('inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:cursor-not-allowed disabled:opacity-60',
        size === 'sm' ? 'px-3 py-1.5 text-xs' : 'min-h-[44px] px-4 py-2 text-sm md:min-h-0', styles, className)}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
}

export function Card({ className, children, ...rest }: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={clsx('card', className)}>{children}</div>
}

const tones: Record<string, string> = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300',
  red: 'bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-950 dark:text-red-300',
  blue: 'bg-brand-50 text-brand-700 ring-brand-600/20 dark:bg-brand-900/40 dark:text-brand-200',
  slate: 'bg-slate-100 text-slate-700 ring-slate-500/20 dark:bg-navy-800 dark:text-slate-300',
}
export function Badge({ tone = 'slate', children }: { tone?: keyof typeof tones | string; children: ReactNode }) {
  return <span className={clsx('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset', tones[tone] ?? tones.slate)}>{children}</span>
}
export const RiskBadge = ({ level }: { level: string }) => <Badge tone={riskTone(level)}>{level}</Badge>
export const StatusBadge = ({ status }: { status: string }) => (
  <Badge tone={{ analyzed: 'green', completed: 'green', confirmed: 'red', flagged: 'amber', failed: 'red', analyzing: 'blue', running: 'blue', queued: 'blue', pending: 'slate', dismissed: 'slate', uploaded: 'slate' }[status] ?? 'slate'}>{status}</Badge>
)

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  )
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return <div className="flex items-center justify-center gap-2 py-16 text-slate-500" role="status"><Loader2 className="h-5 w-5 animate-spin" />{label}…</div>
}

export function EmptyState({ icon, title, text, action }: { icon?: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {icon && <div className="mb-3 rounded-2xl bg-brand-50 p-3 text-brand-600 dark:bg-brand-900/30">{icon}</div>}
      <h3 className="font-semibold text-slate-900 dark:text-white">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300" role="alert">
      {message} {onRetry && <button className="ml-2 font-medium underline" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function StatCard({ label, value, icon, tone = 'brand', hint }: { label: string; value: ReactNode; icon?: ReactNode; tone?: 'brand' | 'green' | 'amber' | 'red'; hint?: string }) {
  const bg = { brand: 'from-brand-500 to-brand-700', green: 'from-emerald-500 to-emerald-700', amber: 'from-amber-500 to-orange-600', red: 'from-red-500 to-rose-700' }[tone]
  return (
    <Card className="flex items-center gap-4 p-4 sm:p-5">
      {icon && <div className={`rounded-xl bg-gradient-to-br ${bg} p-3 text-white`}>{icon}</div>}
      <div className="min-w-0">
        <div className="truncate text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
        <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
        {hint && <div className="text-xs text-slate-500">{hint}</div>}
      </div>
    </Card>
  )
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [open, onClose])
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div className="absolute inset-0 bg-navy-950/60 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
            className={clsx('card relative max-h-[92vh] w-full overflow-y-auto rounded-b-none p-5 sm:rounded-b-2xl', wide ? 'sm:max-w-2xl' : 'sm:max-w-lg')}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h2>
              <button onClick={onClose} aria-label="Close" className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-navy-800"><X className="h-4 w-4" /></button>
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

export function Pagination({ page, pageSize, total, onChange }: { page: number; pageSize: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total <= pageSize) return null
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm dark:border-navy-800">
      <span className="text-slate-500">{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}</span>
      <div className="flex items-center gap-1">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
        <span className="px-2">{page} / {pages}</span>
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
      </div>
    </div>
  )
}

export interface Column<T> { key: string; header: string; render?: (row: T) => ReactNode; primary?: boolean; hideOnMobile?: boolean; sortKey?: string; className?: string }

/** Table on md+ screens, stacked cards on phones (a redesign, not a shrunken table). */
export function DataTable<T>({ columns, rows, rowKey, onRowClick, sort, onSort, empty }: {
  columns: Column<T>[]; rows: T[]; rowKey: (r: T) => string | number; onRowClick?: (r: T) => void
  sort?: string; onSort?: (s: string) => void; empty?: ReactNode
}) {
  if (!rows.length) return <>{empty ?? <EmptyState title="Nothing here yet" />}</>
  const cell = (c: Column<T>, r: T) => (c.render ? c.render(r) : String((r as any)[c.key] ?? '—'))
  const sortArrow = (c: Column<T>) => (sort && c.sortKey && sort.replace('-', '') === c.sortKey ? (sort.startsWith('-') ? ' ↓' : ' ↑') : '')
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-500 dark:border-navy-800">
            <tr>{columns.map((c) => (
              <th key={c.key} className={clsx('px-4 py-3 font-medium', c.className)}>
                {c.sortKey && onSort ? <button onClick={() => onSort(sort === c.sortKey ? `-${c.sortKey}` : c.sortKey!)} className="uppercase hover:text-brand-600">{c.header}{sortArrow(c)}</button> : c.header}
              </th>))}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-navy-800">
            {rows.map((r) => (
              <tr key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined}
                className={clsx('transition hover:bg-slate-50 dark:hover:bg-navy-800/50', onRowClick && 'cursor-pointer')}>
                {columns.map((c) => <td key={c.key} className={clsx('px-4 py-3', c.className)}>{cell(c, r)}</td>)}
              </tr>))}
          </tbody>
        </table>
      </div>
      <ul className="divide-y divide-slate-100 md:hidden dark:divide-navy-800" data-testid="mobile-cards">
        {rows.map((r) => {
          const primary = columns.find((c) => c.primary) ?? columns[0]
          return (
            <li key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined} className={clsx('space-y-1.5 px-4 py-3.5', onRowClick && 'active:bg-slate-50 dark:active:bg-navy-800')}>
              <div className="font-medium text-slate-900 dark:text-white">{cell(primary, r)}</div>
              <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                {columns.filter((c) => c !== primary && !c.hideOnMobile).map((c) => (
                  <div key={c.key} className="min-w-0"><dt className="text-slate-500">{c.header}</dt><dd className="truncate text-slate-800 dark:text-slate-200">{cell(c, r)}</dd></div>
                ))}
              </dl>
            </li>)
        })}
      </ul>
    </>
  )
}

export function ProgressBar({ value, tone = 'brand' }: { value: number; tone?: 'brand' | 'amber' | 'red' | 'green' }) {
  const c = { brand: 'bg-brand-600', amber: 'bg-amber-500', red: 'bg-red-500', green: 'bg-emerald-500' }[tone]
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-navy-800" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
      <motion.div className={`h-full rounded-full ${c}`} initial={false} animate={{ width: `${Math.max(2, value * 100)}%` }} transition={{ duration: 0.4 }} />
    </div>
  )
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={clsx('whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-medium transition', value === t.id ? 'bg-brand-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-navy-800')}>{t.label}</button>
      ))}
    </div>
  )
}

export const inputCls = 'input'
