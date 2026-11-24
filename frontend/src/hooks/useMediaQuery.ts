import { useEffect, useState } from 'react'

export function useMediaQuery(query: string) {
  const get = () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false)
  const [matches, setMatches] = useState(get)
  useEffect(() => {
    const m = window.matchMedia(query)
    const on = () => setMatches(m.matches)
    on()
    m.addEventListener('change', on)
    return () => m.removeEventListener('change', on)
  }, [query])
  return matches
}
export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)')
export const useIsMobile = () => !useMediaQuery('(min-width: 768px)')
