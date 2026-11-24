import Editor, { OnMount } from '@monaco-editor/react'
import { useEffect, useRef } from 'react'
import clsx from 'clsx'
import { useTheme } from '../contexts/ThemeContext'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { MONACO_LANG } from '../utils/format'

export interface Range { start: number; end: number }
interface Props { code: string; language: string; ranges: Range[]; activeIndex: number; label: string; height?: number | string }

/** Desktop: Monaco editor with match decorations. Mobile: lightweight line list (Monaco is heavy on phones). */
export default function CodePane({ code, language, ranges, activeIndex, label, height = 520 }: Props) {
  const desktop = useMediaQuery('(min-width: 768px)')
  const { dark } = useTheme()
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null)
  const decoRef = useRef<{ clear: () => void } | null>(null)

  const apply = () => {
    const ed = editorRef.current
    if (!ed) return
    decoRef.current?.clear()
    decoRef.current = ed.createDecorationsCollection(
      ranges.map((r, i) => ({
        range: { startLineNumber: r.start, startColumn: 1, endLineNumber: r.end, endColumn: 1 },
        options: { isWholeLine: true, className: i === activeIndex ? 'match-line-active' : 'match-line', linesDecorationsClassName: i === activeIndex ? 'match-gutter-active' : 'match-gutter' },
      })),
    )
    const r = ranges[activeIndex]
    if (r) ed.revealLineInCenter(r.start)
  }

  useEffect(apply, [ranges, activeIndex, code]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!desktop) {
    const lines = code.split('\n')
    const active = ranges[activeIndex]
    return (
      <div className="max-h-[60vh] overflow-auto rounded-xl border border-slate-200 bg-white font-mono text-[12px] dark:border-navy-800 dark:bg-navy-950" aria-label={label}>
        {lines.map((ln, i) => {
          const n = i + 1
          const inAny = ranges.some((r) => n >= r.start && n <= r.end)
          const inActive = active && n >= active.start && n <= active.end
          return (
            <div key={i} id={`${label}-L${n}`} className={clsx('flex whitespace-pre', inActive ? 'bg-amber-200/60 dark:bg-amber-500/25' : inAny && 'bg-brand-100/70 dark:bg-brand-500/20')}>
              <span className="w-10 shrink-0 select-none pr-2 text-right text-slate-400">{n}</span><span className="pr-4">{ln || ' '}</span>
            </div>)
        })}
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-navy-800" aria-label={label}>
      <Editor height={height} language={MONACO_LANG[language] ?? 'plaintext'} value={code} theme={dark ? 'vs-dark' : 'light'}
        onMount={(ed) => { editorRef.current = ed; apply() }}
        options={{ readOnly: true, minimap: { enabled: false }, scrollBeyondLastLine: false, fontSize: 13, glyphMargin: false, renderLineHighlight: 'none', automaticLayout: true, wordWrap: 'off' }} />
    </div>
  )
}
