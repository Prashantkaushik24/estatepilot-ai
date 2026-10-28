import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, download } from '../lib/api'
import type { Charts, PowerBI } from '../types'
import { ChartsGrid } from '../components/Charts'
import { ErrorBox, PageHeader, Skeleton } from '../components/ui'
import { useToast } from '../lib/toast'

const EXPORTS = ['leads', 'emails', 'tasks', 'properties', 'fact_leads']
export default function Analytics() {
  const toast = useToast()
  const c = useQuery({ queryKey: ['charts'], queryFn: () => api.get<Charts>('/analytics/charts') })
  const p = useQuery({ queryKey: ['powerbi'], queryFn: () => api.get<PowerBI>('/analytics/powerbi') })
  const exp = async (n: string) => { try { await download(`/analytics/export/${n}.csv`, `${n}.csv`); toast.success(`${n}.csv downloaded`) } catch (e) { toast.error(e) } }
  return (
    <div>
      <PageHeader title="Analytics" subtitle="Charts and exports from the database" />
      <section className="card mb-4" aria-label="CSV exports">
        <h2 className="mb-2 font-semibold">CSV exports</h2>
        <div className="flex flex-wrap gap-2">{EXPORTS.map((n) => <button key={n} className="btn-secondary" onClick={() => exp(n)}><Download className="h-4 w-4" />{n}.csv</button>)}</div>
      </section>
      {c.isError ? <ErrorBox error={c.error} retry={() => c.refetch()} /> : <ChartsGrid data={c.data} loading={c.isLoading} />}
      <section className="card mt-4" aria-label="Power BI">
        <h2 className="mb-2 font-semibold">Power BI</h2>
        {p.isLoading ? <Skeleton className="h-40 w-full" /> : p.isError ? <ErrorBox error={p.error} /> : p.data?.configured && p.data.embed_url ? (
          <iframe title="Power BI report" src={p.data.embed_url} className="h-[500px] w-full rounded-lg border-0" allowFullScreen />
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-500">
            <p className="font-medium text-slate-700 dark:text-slate-300">Power BI is not configured</p>
            <p>{p.data?.message}</p>
            <p className="mt-2">Export the CSVs above (including <code>fact_leads</code>) and import them into Power BI Desktop, or set the Power BI environment variables on the backend to embed a report here.</p>
          </div>
        )}
      </section>
    </div>
  )
}
