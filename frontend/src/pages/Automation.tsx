import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { OctagonAlert, Pause, Play } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction } from '../lib/hooks'
import { fmtDate } from '../lib/format'
import type { AIRun, AutomationState, Rule } from '../types'
import { Badge, Confirm, DemoAIBadge, Empty, ErrorBox, PageHeader, SkeletonRows, Toggle } from '../components/ui'

export default function Automation() {
  const { can } = useAuth()
  const rules = useQuery({ queryKey: ['rules'], queryFn: () => api.get<Rule[]>('/automation/rules') })
  const state = useQuery({ queryKey: ['auto-state'], queryFn: () => api.get<AutomationState>('/automation/state') })
  const runs = useQuery({ queryKey: ['runs'], queryFn: () => api.get<AIRun[] | { items: AIRun[] }>('/automation/runs') })
  const runList = Array.isArray(runs.data) ? runs.data : runs.data?.items ?? []
  const inv = { invalidate: ['rules', 'auto-state', 'integrations', 'runs'] }
  const toggle = useAction((v: { id: Rule['id']; enabled: boolean }) => api.patch(`/automation/rules/${v.id}`, { enabled: v.enabled }), { success: 'Rule updated', ...inv })
  const pause = useAction((p: boolean) => api.post(p ? '/automation/pause' : '/automation/resume'), { success: 'Automation state updated', ...inv })
  const kill = useAction((enabled: boolean) => api.post('/automation/kill-switch', { enabled }), { success: 'Kill switch updated', ...inv, onSuccess: () => setConfirm(false) })
  const [confirm, setConfirm] = useState(false)
  const s = state.data
  return (
    <div>
      <PageHeader title="Automation" subtitle="Control the AI pipeline" />
      <section className="card mb-4" aria-label="Controls">
        {state.isLoading ? <SkeletonRows rows={1} /> : state.isError ? <ErrorBox error={state.error} /> : (
          <div className="flex flex-wrap items-center gap-3">
            <Badge color={s!.paused ? 'amber' : 'green'}>{s!.paused ? 'Paused' : 'Running'}</Badge>
            <Badge color={s!.kill_switch ? 'red' : 'gray'}>Kill switch {s!.kill_switch ? 'ON' : 'off'}</Badge>
            <Badge color={s!.sending_enabled ? 'amber' : 'gray'}>Sending {s!.sending_enabled ? 'enabled' : 'disabled'}</Badge>
            <div className="flex-1" />
            {s!.paused ? <button className="btn-secondary" disabled={!can('manager') || pause.isPending} title={can('manager') ? undefined : 'Requires manager or admin'} onClick={() => pause.mutate(false)}><Play className="h-4 w-4" />Resume</button>
              : <button className="btn-secondary" disabled={!can('manager') || pause.isPending} title={can('manager') ? undefined : 'Requires manager or admin'} onClick={() => pause.mutate(true)}><Pause className="h-4 w-4" />Pause</button>}
            <button className={s!.kill_switch ? 'btn-secondary' : 'btn-danger'} disabled={!can('admin')} title={can('admin') ? undefined : 'Only admins can use the kill switch'} onClick={() => (s!.kill_switch ? kill.mutate(false) : setConfirm(true))}><OctagonAlert className="h-4 w-4" />{s!.kill_switch ? 'Disable kill switch' : 'Kill switch'}</button>
          </div>
        )}
      </section>
      <section className="card mb-4" aria-label="Rules">
        <h2 className="mb-2 font-semibold">Rules</h2>
        {rules.isLoading ? <SkeletonRows rows={4} /> : rules.isError ? <ErrorBox error={rules.error} retry={() => rules.refetch()} /> : (
          <ul className="divide-y dark:divide-slate-800">{rules.data!.map((r) => (
            <li key={String(r.id)} className="flex items-center justify-between gap-3 py-3">
              <div><p className="font-medium">{r.name}</p><p className="text-sm text-slate-500">{r.description}</p><p className="text-xs text-slate-500">Runs: {r.run_count} · Last run: {r.last_run_at ? fmtDate(r.last_run_at) : 'never'}{r.last_result ? ` · ${r.last_result}` : ''}</p></div>
              <Toggle name={`Toggle ${r.name}`} checked={r.enabled} disabled={!can('manager') || toggle.isPending} title={can('manager') ? undefined : 'Requires manager or admin'} onChange={(enabled) => toggle.mutate({ id: r.id, enabled })} />
            </li>))}</ul>
        )}
      </section>
      <section className="card" aria-label="Runs">
        <h2 className="mb-2 font-semibold">Recent runs</h2>
        {runs.isLoading ? <SkeletonRows /> : runs.isError ? <ErrorBox error={runs.error} /> : runList.length === 0 ? <Empty title="No runs yet" hint="Process an email to create an AI run." /> : (
          <div className="overflow-x-auto"><table className="w-full"><thead className="border-b dark:border-slate-800"><tr>{['When', 'Status', 'Provider', 'Attempts', 'Duration', 'Error'].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody className="divide-y dark:divide-slate-800">{runList.map((r) => <tr key={String(r.id)}><td className="td">{fmtDate(r.created_at)}</td><td className="td"><Badge color={r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'amber'}>{r.status}</Badge></td><td className="td">{r.provider}{r.model ? ` / ${r.model}` : ''} {r.is_demo && <DemoAIBadge />}</td><td className="td">{r.attempts}</td><td className="td">{r.duration_ms} ms</td><td className="td text-red-600">{r.error ?? ''}</td></tr>)}</tbody></table></div>
        )}
      </section>
      <Confirm open={confirm} title="Activate kill switch?" message="This immediately halts all automation and sending until it is disabled again." confirmLabel="Activate" danger busy={kill.isPending} onClose={() => setConfirm(false)} onConfirm={() => kill.mutate(true)} />
    </div>
  )
}
