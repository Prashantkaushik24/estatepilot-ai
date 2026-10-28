import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import type { Charts, DashboardMetrics } from '../types'
import { ChartsGrid } from '../components/Charts'
import { ErrorBox, PageHeader, Skeleton } from '../components/ui'
import { inrShort } from '../lib/format'

export default function Overview() {
  const m = useQuery({ queryKey: ['metrics'], queryFn: () => api.get<DashboardMetrics>('/dashboard/metrics') })
  const c = useQuery({ queryKey: ['charts'], queryFn: () => api.get<Charts>('/analytics/charts') })
  const d = m.data
  const kpis: [string, string | undefined][] = d ? [
    ['Total leads', String(d.total_leads)], ['New leads', String(d.new_leads)], ['Qualified leads', String(d.qualified_leads)], ['Hot leads', String(d.hot_leads)],
    ['Emails processed', String(d.emails_processed)], ['Unread emails', String(d.unread_emails)], ['Pending follow-ups', String(d.pending_followups)], ['Overdue tasks', String(d.overdue_tasks)],
    ['Avg first response', d.avg_first_response_minutes == null ? 'No data' : `${d.avg_first_response_minutes.toFixed(0)} min`], ['Conversion rate', `${(d.conversion_rate * 100).toFixed(1)}%`],
    ['Pipeline value', inrShort(d.pipeline_value)], ['Won value', inrShort(d.won_value)],
  ] : []
  return (
    <div>
      <PageHeader title="Overview" subtitle="Live metrics from your workspace database" />
      {d?.has_demo_data && (
        <div role="note" className="mb-4 flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          <AlertTriangle className="h-4 w-4" />This workspace contains seeded demo data. Figures include fictional demo leads and properties.
        </div>
      )}
      {m.isError && <ErrorBox error={m.error} retry={() => m.refetch()} />}
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {m.isLoading ? Array.from({ length: 12 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />) : kpis.map(([k, v]) => (
          <div key={k} className="card"><div className="text-xs text-slate-500">{k}</div><div className="mt-1 text-2xl font-semibold">{v}</div></div>
        ))}
      </div>
      {c.isError ? <ErrorBox error={c.error} retry={() => c.refetch()} /> : <ChartsGrid data={c.data} loading={c.isLoading} />}
    </div>
  )
}
