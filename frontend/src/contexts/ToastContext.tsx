import { createContext, ReactNode, useCallback, useContext, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle2 } from 'lucide-react'

interface Toast { id: number; kind: 'success' | 'error'; text: string }
const Ctx = createContext<{ success: (t: string) => void; error: (t: string) => void } | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const push = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, kind, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4500)
  }, [])
  return (
    <Ctx.Provider value={{ success: (t) => push('success', t), error: (t) => push('error', t) }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-20 z-[100] flex flex-col items-center gap-2 px-4 md:bottom-6 md:items-end md:pr-6" role="status" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className={`pointer-events-auto flex max-w-sm items-start gap-2 rounded-xl px-4 py-3 text-sm text-white shadow-lg ${t.kind === 'success' ? 'bg-emerald-600' : 'bg-red-600'}`}>
              {t.kind === 'success' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
              <span>{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  )
}

export const useToast = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useToast must be used inside ToastProvider')
  return c
}
