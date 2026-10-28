export const API_URL: string = ((import.meta as any).env?.VITE_API_URL as string) || 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'ep_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string | null) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  status: number
  body: any
  constructor(status: number, message: string, body?: any) {
    super(message)
    this.status = status
    this.body = body
  }
}

let onUnauthorized: () => void = () => {
  setToken(null)
  if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) window.location.assign('/login')
}
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn }

export function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return ''
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

function detailMessage(body: any, fallback: string): string {
  const d = body?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((e) => (e?.msg ? `${(e.loc || []).slice(1).join('.')}: ${e.msg}` : String(e))).join('; ')
  return fallback
}

export async function request<T>(method: string, path: string, opts: { body?: unknown; params?: Record<string, unknown>; auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token && opts.auth !== false) headers.Authorization = `Bearer ${token}`
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}${buildQuery(opts.params)}`, { method, headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Check that the backend is running.')
  }
  const text = await res.text()
  let data: any = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!res.ok) {
    if (res.status === 401 && opts.auth !== false && !path.startsWith('/auth/login')) onUnauthorized()
    throw new ApiError(res.status, detailMessage(data, res.statusText || `Request failed (${res.status})`), data)
  }
  return data as T
}

export async function download(path: string, filename: string) {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) {
    if (res.status === 401) onUnauthorized()
    let body: any = null
    try { body = await res.json() } catch { /* ignore */ }
    throw new ApiError(res.status, detailMessage(body, 'Export failed'), body)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  get: <T>(p: string, params?: Record<string, unknown>) => request<T>('GET', p, { params }),
  post: <T>(p: string, body?: unknown) => request<T>('POST', p, { body: body ?? {} }),
  put: <T>(p: string, body?: unknown) => request<T>('PUT', p, { body }),
  patch: <T>(p: string, body?: unknown) => request<T>('PATCH', p, { body }),
  del: <T>(p: string) => request<T>('DELETE', p),
}
