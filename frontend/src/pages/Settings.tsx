import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction, useIntegrations } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { useTheme } from '../lib/theme'
import { fmtDate, isEmail } from '../lib/format'
import type { AppSettings, Health, Role, User } from '../types'
import { Badge, Confirm, ErrorBox, Field, Modal, PageHeader, SkeletonRows, Toggle } from '../components/ui'

const Row = ({ k, children }: { k: string; children: React.ReactNode }) => <div className="flex items-center justify-between gap-3 py-2 text-sm"><span className="text-slate-500">{k}</span><span>{children}</span></div>

function UserModal({ onClose }: { onClose: () => void }) {
  const [f, setF] = useState({ email: '', full_name: '', password: '', role: 'agent' }); const [errs, setErrs] = useState<Record<string, string>>({})
  const save = useAction((b: typeof f) => api.post('/users', b), { success: 'User created', invalidate: ['users'], onSuccess: onClose })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const e: Record<string, string> = {}
    if (!isEmail(f.email)) e.email = 'Valid email required'
    if (!f.full_name.trim()) e.full_name = 'Name is required'
    if (f.password.length < 8) e.password = 'At least 8 characters'
    setErrs(e); if (!Object.keys(e).length) save.mutate(f)
  }
  return (
    <Modal open onClose={onClose} title="New user" footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={save.isPending} onClick={submit}>Create</button></>}>
      <div className="space-y-3">
        <Field label="Email" htmlFor="u-email" error={errs.email}><input id="u-email" className="input" value={f.email} onChange={set('email')} /></Field>
        <Field label="Full name" htmlFor="u-name" error={errs.full_name}><input id="u-name" className="input" value={f.full_name} onChange={set('full_name')} /></Field>
        <Field label="Password" htmlFor="u-pw" error={errs.password}><input id="u-pw" type="password" className="input" value={f.password} onChange={set('password')} /></Field>
        <Field label="Role" htmlFor="u-role"><select id="u-role" className="input" value={f.role} onChange={set('role')}>{['admin', 'manager', 'agent', 'analyst'].map((r) => <option key={r}>{r}</option>)}</select></Field>
      </div>
    </Modal>
  )
}

export default function SettingsPage() {
  const { can, user } = useAuth(); const toast = useToast(); const qc = useQueryClient()
  const { theme, setTheme } = useTheme()
  const [params, setParams] = useSearchParams()
  const integ = useIntegrations()
  const health = useQuery({ queryKey: ['health'], queryFn: () => api.get<Health>('/health') })
  const settings = useQuery({ queryKey: ['settings'], queryFn: () => api.get<AppSettings>('/settings') })
  const users = useQuery({ queryKey: ['users'], queryFn: () => api.get<User[] | { items: User[] }>('/users'), enabled: can('manager') })
  const userList = Array.isArray(users.data) ? users.data : users.data?.items ?? []
  const [newUser, setNewUser] = useState(false); const [disc, setDisc] = useState(false); const [reset, setReset] = useState(false)

  useEffect(() => {
    const g = params.get('gmail')
    if (g) { g === 'connected' ? toast.success('Gmail connected') : toast.error(new Error('Gmail connection failed')); qc.invalidateQueries({ queryKey: ['integrations'] }); params.delete('gmail'); setParams(params, { replace: true }) }
  }, []) // eslint-disable-line

  const connect = useAction(() => api.get<{ url: string }>('/integrations/gmail/auth-url'), { onSuccess: (r) => window.location.assign(r.url) })
  const sync = useAction(() => api.post<{ imported: number; skipped_duplicates: number }>('/integrations/gmail/sync'), { success: (r) => `Imported ${r.imported}, skipped ${r.skipped_duplicates} duplicates`, invalidate: ['integrations', 'emails'] })
  const disconnect = useAction(() => api.post('/integrations/gmail/disconnect'), { success: 'Gmail disconnected', invalidate: ['integrations'], onSuccess: () => setDisc(false) })
  const demo = useAction((demo_mode: boolean) => api.patch<AppSettings>('/settings', { demo_mode }), { success: 'Demo mode updated', invalidate: ['settings', 'health', 'integrations'] })
  const patchUser = useAction((v: { id: User['id']; body: Partial<User> }) => api.patch(`/users/${v.id}`, v.body), { success: 'User updated', invalidate: ['users'] })
  const resetDemo = useAction(() => api.post('/admin/reset-demo', { confirm: true }), { success: 'Demo data restored to original', onSuccess: () => { setReset(false); qc.invalidateQueries() } })
  const i = integ.data; const g = i?.gmail
  const mgr = can('manager'); const adm = can('admin')

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" />
      <section className="card" aria-label="Integrations">
        <h2 className="mb-2 font-semibold">Integrations</h2>
        {integ.isLoading ? <SkeletonRows rows={4} /> : integ.isError ? <ErrorBox error={integ.error} retry={() => integ.refetch()} /> : i && (
          <div className="divide-y dark:divide-slate-800">
            <Row k="Backend"><Badge color="green">{i.backend}</Badge> {health.data && <span className="text-xs text-slate-500">v{health.data.version}</span>}</Row>
            <Row k="AI provider">{i.ai.provider}{i.ai.model ? ` / ${i.ai.model}` : ''} <Badge color={i.ai.configured ? 'green' : 'gray'}>{i.ai.configured ? 'configured' : 'not configured'}</Badge> {i.ai.demo_mode && <Badge color="purple">DEMO AI</Badge>}</Row>
            <Row k="Gmail"><Badge color={g!.connected ? 'green' : 'gray'}>{g!.connected ? `connected${g!.account_email ? ` (${g!.account_email})` : ''}` : g!.configured ? 'not connected' : 'not configured'}</Badge></Row>
            {g!.last_sync_at && <Row k="Last Gmail sync">{fmtDate(g!.last_sync_at)}</Row>}
            <Row k="Power BI"><Badge color={i.powerbi.configured ? 'green' : 'gray'}>{i.powerbi.configured ? 'configured' : 'not configured'}</Badge></Row>
            <Row k="Sending"><Badge color={i.sending_enabled ? 'amber' : 'gray'}>{i.sending_enabled ? 'enabled' : 'disabled (server env)'}</Badge></Row>
            <Row k="Automation"><Badge color={i.paused ? 'amber' : 'green'}>{i.paused ? 'paused' : 'running'}</Badge> {i.kill_switch && <Badge color="red">kill switch ON</Badge>}</Row>
            <div className="flex flex-wrap gap-2 pt-3">
              {!g!.connected && <button className="btn-primary" disabled={!g!.configured || !mgr || connect.isPending} title={!g!.configured ? 'Gmail OAuth is not configured on the server' : !mgr ? 'Requires manager or admin' : undefined} onClick={() => connect.mutate(undefined)}>Connect Gmail</button>}
              <button className="btn-secondary" disabled={!g!.connected || !mgr || sync.isPending} title={!g!.connected ? 'Connect Gmail first' : !mgr ? 'Requires manager or admin' : undefined} onClick={() => sync.mutate(undefined)}>{sync.isPending ? 'Syncing…' : 'Sync now'}</button>
              <button className="btn-secondary" disabled={!g!.connected || !mgr} title={!g!.connected ? 'Gmail is not connected' : !mgr ? 'Requires manager or admin' : undefined} onClick={() => setDisc(true)}>Disconnect</button>
            </div>
          </div>
        )}
      </section>
      <section className="card" aria-label="Preferences">
        <h2 className="mb-2 font-semibold">Preferences</h2>
        <Row k="Theme"><select aria-label="Theme" className="input !w-auto" value={theme} onChange={(e) => setTheme(e.target.value as 'light' | 'dark')}><option value="light">Light</option><option value="dark">Dark</option></select></Row>
        <Row k="Demo mode">{settings.isLoading ? '…' : settings.isError ? <span className="text-red-600">unavailable</span> : <Toggle name="Demo mode" checked={!!settings.data?.demo_mode} disabled={!mgr || demo.isPending} title={mgr ? undefined : 'Requires manager or admin'} onChange={(v) => demo.mutate(v)} />}</Row>
        <Row k="Timezone">{settings.data?.timezone ?? '—'}</Row>
        <Row k="Signed in as">{user?.email} ({user?.role})</Row>
      </section>
      {mgr && (
        <section className="card" aria-label="Users">
          <div className="mb-2 flex items-center justify-between"><h2 className="font-semibold">Users</h2><button className="btn-primary" disabled={!adm} title={adm ? undefined : 'Only admins can add users'} onClick={() => setNewUser(true)}>Add user</button></div>
          {users.isLoading ? <SkeletonRows rows={4} /> : users.isError ? <ErrorBox error={users.error} /> : (
            <div className="overflow-x-auto"><table className="w-full"><thead className="border-b dark:border-slate-800"><tr>{['Name', 'Email', 'Role', 'Active'].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody className="divide-y dark:divide-slate-800">{userList.map((u) => (
                <tr key={String(u.id)}><td className="td">{u.full_name}</td><td className="td">{u.email}</td>
                  <td className="td"><select aria-label={`Role for ${u.email}`} className="input !w-auto" value={u.role} disabled={!adm || patchUser.isPending} title={adm ? undefined : 'Only admins can change roles'} onChange={(e) => patchUser.mutate({ id: u.id, body: { role: e.target.value as Role } })}>{['admin', 'manager', 'agent', 'analyst'].map((r) => <option key={r}>{r}</option>)}</select></td>
                  <td className="td"><Toggle name={`Active ${u.email}`} checked={u.is_active} disabled={!adm || u.id === user?.id} title={u.id === user?.id ? 'You cannot deactivate yourself' : adm ? undefined : 'Only admins can change this'} onChange={(v) => patchUser.mutate({ id: u.id, body: { is_active: v } })} /></td></tr>))}</tbody></table></div>
          )}
        </section>
      )}
      <section className="card" aria-label="Demo data">
        <h2 className="mb-1 font-semibold">Demo data</h2>
        <p className="mb-3 text-sm text-slate-500">Deletes all emails, leads, tasks, drafts, matches, logs and notifications you created, then restores the original demo properties, leads and tasks. Users and settings are kept.</p>
        <button className="btn-secondary" disabled={!adm || resetDemo.isPending} title={adm ? undefined : 'Only admins can reset demo data'} onClick={() => setReset(true)}>Reset demo data</button>
      </section>
      <Confirm open={reset} title="Reset all demo data?" message="This permanently deletes everything added or changed since the original demo data (emails, leads, tasks, drafts, logs) and restores the original demo set. This cannot be undone." confirmLabel="Yes, reset everything" danger busy={resetDemo.isPending} onClose={() => setReset(false)} onConfirm={() => resetDemo.mutate(undefined)} />
      {newUser && <UserModal onClose={() => setNewUser(false)} />}
      <Confirm open={disc} title="Disconnect Gmail?" message="Email sync and sending will stop until you reconnect." confirmLabel="Disconnect" danger busy={disconnect.isPending} onClose={() => setDisc(false)} onConfirm={() => disconnect.mutate(undefined)} />
    </div>
  )
}
