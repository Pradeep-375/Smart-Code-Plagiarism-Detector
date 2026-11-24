import { DependencyList, useCallback, useEffect, useRef, useState } from 'react'
import { errMsg } from '../services/api'

export function useFetch<T>(fn: () => Promise<T>, deps: DependencyList = [], opts: { intervalMs?: number; enabled?: boolean } = {}) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const fnRef = useRef(fn)
  fnRef.current = fn
  const enabled = opts.enabled ?? true

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      setData(await fnRef.current())
      setError(null)
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!enabled) { setLoading(false); return }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])

  useEffect(() => {
    if (!opts.intervalMs || !enabled) return
    const id = setInterval(() => load(true), opts.intervalMs)
    return () => clearInterval(id)
  }, [opts.intervalMs, enabled, load])

  return { data, loading, error, reload: () => load(), setData }
}
