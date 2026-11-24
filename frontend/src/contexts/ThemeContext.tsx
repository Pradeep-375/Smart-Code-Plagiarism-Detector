import { createContext, ReactNode, useContext, useEffect, useState } from 'react'

type Theme = 'light' | 'dark' | 'system'
const Ctx = createContext<{ theme: Theme; dark: boolean; setTheme: (t: Theme) => void } | null>(null)

const prefersDark = () => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    try { return (localStorage.getItem('theme') as Theme) || 'system' } catch { return 'system' }
  })
  const [dark, setDark] = useState(false)

  useEffect(() => {
    const apply = () => {
      const d = theme === 'dark' || (theme === 'system' && prefersDark())
      setDark(d)
      document.documentElement.classList.toggle('dark', d)
    }
    apply()
    const m = window.matchMedia?.('(prefers-color-scheme: dark)')
    m?.addEventListener('change', apply)
    return () => m?.removeEventListener('change', apply)
  }, [theme])

  const setTheme = (t: Theme) => {
    setThemeState(t)
    try { localStorage.setItem('theme', t) } catch { /* storage unavailable */ }
  }
  return <Ctx.Provider value={{ theme, dark, setTheme }}>{children}</Ctx.Provider>
}

export const useTheme = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useTheme must be used inside ThemeProvider')
  return c
}
