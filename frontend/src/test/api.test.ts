import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, buildQuery, getToken, setToken, setUnauthorizedHandler } from '../lib/api'

const mockFetch = (status: number, body: unknown) => vi.fn().mockResolvedValue({ ok: status < 400, status, statusText: 'x', text: async () => JSON.stringify(body) })
describe('api client', () => {
  beforeEach(() => { localStorage.clear() })
  afterEach(() => vi.unstubAllGlobals())
  it('builds query strings skipping empty values', () => { expect(buildQuery({ a: 1, b: '', c: undefined, d: 'x y' })).toBe('?a=1&d=x+y'); expect(buildQuery({})).toBe('') })
  it('sends bearer token', async () => {
    setToken('abc'); const f = mockFetch(200, { ok: 1 }); vi.stubGlobal('fetch', f)
    await api.get('/leads', { q: 'a' })
    expect(f.mock.calls[0][0]).toContain('/leads?q=a'); expect(f.mock.calls[0][1].headers.Authorization).toBe('Bearer abc')
  })
  it('throws ApiError with detail and triggers unauthorized handler on 401', async () => {
    const h = vi.fn(); setUnauthorizedHandler(h); setToken('t'); vi.stubGlobal('fetch', mockFetch(401, { detail: 'Not authenticated' }))
    await expect(api.get('/x')).rejects.toMatchObject({ status: 401, message: 'Not authenticated' })
    expect(h).toHaveBeenCalled()
  })
  it('surfaces 409 body', async () => {
    vi.stubGlobal('fetch', mockFetch(409, { detail: 'duplicate', existing_email_id: 4 }))
    const e: any = await api.post("/emails/import", {}).catch((x: any) => x)
    expect(e).toBeInstanceOf(ApiError); expect(e.body.existing_email_id).toBe(4); expect(getToken()).toBeNull()
  })
})
