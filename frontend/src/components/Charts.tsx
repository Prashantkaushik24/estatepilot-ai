import { ReactNode } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Charts, NameValue } from '../types'
import { Empty, Skeleton } from './ui'
import { label } from '../lib/format'

const COLORS = ['#0d9488', '#2563eb', '#f59e0b', '#8b5cf6', '#ef4444', '#10b981', '#64748b', '#ec4899']

function Card({ title, children, empty }: { title: string; children: ReactNode; empty: boolean }) {
  return (
    <section className="card" aria-label={title}>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <div className="h-64">{empty ? <Empty title="No data yet" /> : children}</div>
    </section>
  )
}
const Pie_ = ({ data }: { data: NameValue[] }) => (
  <ResponsiveContainer><PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>{data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend formatter={(v) => label(String(v))} /></PieChart></ResponsiveContainer>
)
const Bar_ = ({ data, horizontal, color = '#0d9488' }: { data: NameValue[]; horizontal?: boolean; color?: string }) => (
  <ResponsiveContainer>
    {horizontal ? (
      <BarChart data={data} layout="vertical" margin={{ left: 20 }}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} /></BarChart>
    ) : (
      <BarChart data={data}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} /></BarChart>
    )}
  </ResponsiveContainer>
)

export function ChartsGrid({ data, loading }: { data?: Charts; loading: boolean }) {
  if (loading || !data) return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-72 w-full" />)}</div>
  const has = (a: unknown[]) => !a || a.length === 0
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div className="md:col-span-2"><Card title="Leads over time" empty={has(data.leads_over_time)}>
        <ResponsiveContainer><LineChart data={data.leads_over_time}><CartesianGrid strokeDasharray="3 3" opacity={0.3} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="count" stroke="#0d9488" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
      </Card></div>
      <Card title="Leads by source" empty={has(data.leads_by_source)}><Pie_ data={data.leads_by_source} /></Card>
      <Card title="Lead status" empty={has(data.lead_status)}><Bar_ data={data.lead_status} /></Card>
      <Card title="Email intent" empty={has(data.email_intent)}><Bar_ data={data.email_intent} horizontal color="#2563eb" /></Card>
      <Card title="Demand by location" empty={has(data.demand_by_location)}><Bar_ data={data.demand_by_location} horizontal color="#8b5cf6" /></Card>
      <Card title="Budget distribution" empty={has(data.budget_distribution)}><Bar_ data={data.budget_distribution} color="#f59e0b" /></Card>
      <Card title="Follow-up status" empty={has(data.followup_status)}><Pie_ data={data.followup_status} /></Card>
      <div className="md:col-span-2 xl:col-span-4"><Card title="Funnel" empty={has(data.funnel)}><Bar_ data={data.funnel} horizontal color="#10b981" /></Card></div>
    </div>
  )
}
