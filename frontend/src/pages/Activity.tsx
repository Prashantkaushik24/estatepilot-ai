import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useList } from '../lib/hooks'
import { fmtDate } from '../lib/format'
import type { AIRun, AuditLog } from '../types'
import { Badge, DemoAIBadge, Empty, ErrorBox, PageHeader, Pagination, Select, SkeletonRows, useDebounced } from '../components/ui'

export default function Activity() {
  const [tab, setTab] = useState<'logs' | 'runs'>('logs')
  const [action, setAction] = useState(''); const [entity, setEntity] = useState(''); const [level, setLevel] = useState(''); const [page, setPage] = useState(1)
  const da = useDebounced(action); const de = useDebounced(entity)
  const logs = useList<AuditLog>('audit', '/audit', { action: da, entity_type: de, level, page, page_size: 25 }, tab === 'logs')
  const [runStatus, setRunStatus] = useState('')
  const runs = useQuery({ queryKey: ['runs'], queryFn: () => api.get<AIRun[] | { items: AIRun[] }>('/automation/runs'), enabled: tab === 'runs' })
  const runList = (Array.isArray(runs.data) ? runs.data : runs.data?.items ?? []).filter((r) => !runStatus || r.status === runStatus)
  return (
    <div>
      <PageHeader title="Activity" subtitle="AI audit logs and runs" />
      <div role="tablist" className="mb-3 flex gap-2">
        {(['logs', 'runs'] as const).map((t) => <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab(t)}>{t === 'logs' ? 'Audit logs' : 'AI runs'}</button>)}
      </div>
      <div className="card">
        {tab === 'logs' ? (
          <>
            <div className="mb-3 flex flex-wrap gap-2">
              <input aria-label="Action filter" placeholder="Action" className="input !w-44" value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} />
              <input aria-label="Entity type filter" placeholder="Entity type" className="input !w-44" value={entity} onChange={(e) => { setEntity(e.target.value); setPage(1) }} />
              <Select label="Level filter" value={level} onChange={(v) => { setLevel(v); setPage(1) }} options={['info', 'warning', 'error']} placeholder="All levels" />
            </div>
            {logs.isLoading ? <SkeletonRows /> : logs.isError ? <ErrorBox error={logs.error} retry={() => logs.refetch()} /> : logs.data!.items.length === 0 ? <Empty title="No audit logs" hint="No activity matches these filters." /> : (
              <>
                <div className="overflow-x-auto"><table className="w-full"><thead className="border-b dark:border-slate-800"><tr>{['When', 'Level', 'Action', 'Entity', 'Message'].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                  <tbody className="divide-y dark:divide-slate-800">{logs.data!.items.map((l) => <tr key={String(l.id)}><td className="td whitespace-nowrap">{fmtDate(l.created_at)}</td><td className="td"><Badge color={l.level === 'error' ? 'red' : l.level === 'warning' ? 'amber' : 'gray'}>{l.level}</Badge></td><td className="td">{l.action}</td><td className="td">{l.entity_type ?? '—'}{l.entity_id ? ` #${l.entity_id}` : ''}</td><td className="td">{l.message}</td></tr>)}</tbody></table></div>
                <Pagination page={page} pageSize={25} total={logs.data!.total} onPage={setPage} />
              </>
            )}
          </>
        ) : (
          <>
            <div className="mb-3"><Select label="Run status filter" value={runStatus} onChange={setRunStatus} options={['success', 'partial', 'failed']} placeholder="All statuses" /></div>
            {runs.isLoading ? <SkeletonRows /> : runs.isError ? <ErrorBox error={runs.error} retry={() => runs.refetch()} /> : runList.length === 0 ? <Empty title="No AI runs" /> : (
              <ul className="divide-y dark:divide-slate-800">{runList.map((r) => (
                <li key={String(r.id)} className="py-2 text-sm"><div className="flex flex-wrap items-center gap-2"><Badge color={r.status === 'success' ? 'green' : r.status === 'failed' ? 'red' : 'amber'}>{r.status}</Badge><span>{r.provider}{r.model ? ` / ${r.model}` : ''}</span>{r.is_demo && <DemoAIBadge />}<span className="text-slate-500">{fmtDate(r.created_at)} · {r.duration_ms} ms · {r.attempts} attempt(s)</span></div>
                  {r.error && <p className="text-red-600">{r.error}</p>}
                  <details className="mt-1"><summary className="cursor-pointer text-slate-500">Steps ({r.steps?.length ?? 0})</summary><ul className="pl-4">{r.steps?.map((s, i) => <li key={i}>{s.name}: {s.status}{s.detail ? ` — ${s.detail}` : ''}</li>)}</ul></details></li>))}</ul>
            )}
          </>
        )}
      </div>
    </div>
  )
}
