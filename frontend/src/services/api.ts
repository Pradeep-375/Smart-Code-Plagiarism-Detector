import axios from 'axios'

const configuredBase = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined)
  || (import.meta.env.VITE_API_URL as string | undefined)
  || '/api/v1'
).replace(/\/$/, '')

export const API_URL = configuredBase.endsWith('/api/v1')
  ? configuredBase
  : `${configuredBase}/api/v1`
export const api = axios.create({ baseURL: API_URL, timeout: 60000 })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token')
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(err)
  },
)

export function errMsg(e: unknown): string {
  const anyE = e as any
  const d = anyE?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg ?? JSON.stringify(x)).join('; ')
  if (anyE?.response?.status === 429) return 'Too many requests - please wait a moment and try again.'
  if (anyE?.code === 'ERR_NETWORK') return 'Cannot reach the server. Check your connection.'
  return anyE?.message ?? 'Something went wrong'
}

/** Download an authenticated file (PDF / CSV) via a blob so the bearer token is sent. */
export async function downloadFile(url: string, fallbackName: string) {
  const res = await api.get(url, { responseType: 'blob' })
  const cd = (res.headers['content-disposition'] as string | undefined) ?? ''
  const m = /filename="?([^";]+)"?/.exec(cd)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(res.data)
  a.download = m?.[1] ?? fallbackName
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}
