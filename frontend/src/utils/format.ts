import type { Risk } from '../types'

export const pct = (v: number | null | undefined, digits = 0) => (v == null ? '—' : `${(v * 100).toFixed(digits)}%`)

export function fmtDate(iso?: string | null, withTime = true) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return withTime ? d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : d.toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export function timeAgo(iso: string) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export const ALGO_LABELS: Record<string, string> = {
  exact: 'Exact matching', token: 'Token-based', lexical: 'Lexical', ast: 'AST analysis', tfidf: 'TF-IDF / cosine',
  winnowing: 'Winnowing fingerprints', structural: 'Structural', transformation: 'Transformation analysis',
}

export const LANG_LABELS: Record<string, string> = { python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JavaScript', typescript: 'TypeScript' }
export const MONACO_LANG: Record<string, string> = { python: 'python', java: 'java', c: 'c', cpp: 'cpp', javascript: 'javascript', typescript: 'typescript' }

export const riskTone = (r: Risk | string): 'green' | 'amber' | 'red' | 'slate' => (r === 'high' ? 'red' : r === 'medium' ? 'amber' : r === 'low' ? 'green' : 'slate')

/** Heat-map colour: white -> amber -> red as similarity grows. */
export function heatColor(score: number) {
  const s = Math.max(0, Math.min(1, score))
  if (s < 0.5) return `rgba(99,102,241,${0.08 + s * 0.5})`
  return `rgba(${239},${68 + Math.round((1 - s) * 120)},68,${0.45 + s * 0.5})`
}

export const bytes = (n: number) => (n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`)
