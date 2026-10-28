import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, Plus, Search } from 'lucide-react'
import { api, download } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction, useList } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { validateLead, LeadForm } from '../lib/validation'
import { fromLocalInput, fmtDate, inr, toLocalInput } from '../lib/format'
import { LEAD_STATUSES } from '../types'
import type { ActivityItem, Lead, PropertyMatch } from '../types'
import { LeadTable } from '../components/LeadTable'
import { Badge, Confirm, Drawer, ErrorBox, Field, Modal, PageHeader, Pagination, PriorityBadge, Select, SkeletonRows, ListToArr, useDebounced } from '../components/ui'

const toForm = (l?: Lead): LeadForm & Record<string, string> => ({
  full_name: l?.full_name ?? '', email: l?.email ?? '', phone: l?.phone ?? '', budget_min: l?.budget_min?.toString() ?? '', budget_max: l?.budget_max?.toString() ?? '',
  bedrooms: l?.bedrooms?.toString() ?? '', status: l?.status ?? 'New', priority: l?.priority ?? 'medium', source: l?.source ?? 'manual', preferred_location: l?.preferred_location ?? '',
  property_type: l?.property_type ?? '', transaction_type: l?.transaction_type ?? '', timeline: l?.timeline ?? '', amenities: (l?.amenities ?? []).join(', '), tags: (l?.tags ?? []).join(', '),
  notes: l?.notes ?? '', next_follow_up_at: toLocalInput(l?.next_follow_up_at),
})

export function LeadFormModal({ lead, open, onClose }: { lead?: Lead; open: boolean; onClose: () => void }) {
  const [f, setF] = useState(toForm(lead)); const [errs, setErrs] = useState<Record<string, string | undefined>>({})
  const save = useAction((body: any) => (lead ? api.patch<Lead>(`/leads/${lead.id}`, body) : api.post<Lead>('/leads', body)), { success: lead ? 'Lead updated' : 'Lead created', invalidate: ['leads', 'metrics', 'charts'], onSuccess: onClose })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const v = validateLead(f); setErrs(v); if (Object.keys(v).length) return
    const num = (s: string) => (s === '' ? null : Number(s))
    save.mutate({
      full_name: f.full_name.trim(), email: f.email || null, phone: f.phone || null, status: f.status, priority: f.priority, ...(lead ? {} : { source: f.source }),
      preferred_location: f.preferred_location || null, property_type: f.property_type || null, transaction_type: f.transaction_type || null, timeline: f.timeline || null,
      bedrooms: num(f.bedrooms), budget_min: num(f.budget_min), budget_max: num(f.budget_max), amenities: ListToArr(f.amenities), tags: ListToArr(f.tags), notes: f.notes || null,
      next_follow_up_at: fromLocalInput(f.next_follow_up_at) ?? null,
    })
  }
  return (
    <Modal open={open} onClose={onClose} title={lead ? 'Edit lead' : 'New lead'} wide footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={save.isPending} onClick={submit}>{save.isPending ? 'Saving…' : 'Save'}</button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Full name *" htmlFor="l-name" error={errs.full_name}><input id="l-name" className="input" value={f.full_name} onChange={set('full_name')} /></Field>
        <Field label="Email" htmlFor="l-email" error={errs.email}><input id="l-email" className="input" value={f.email} onChange={set('email')} /></Field>
        <Field label="Phone" htmlFor="l-phone" error={errs.phone}><input id="l-phone" className="input" value={f.phone} onChange={set('phone')} /></Field>
        <Field label="Preferred location" htmlFor="l-loc"><input id="l-loc" className="input" value={f.preferred_location} onChange={set('preferred_location')} /></Field>
        <Field label="Budget min (INR)" htmlFor="l-bmin" error={errs.budget_min}><input id="l-bmin" type="number" className="input" value={f.budget_min} onChange={set('budget_min')} /></Field>
        <Field label="Budget max (INR)" htmlFor="l-bmax" error={errs.budget_max}><input id="l-bmax" type="number" className="input" value={f.budget_max} onChange={set('budget_max')} /></Field>
        <Field label="Bedrooms" htmlFor="l-bed" error={errs.bedrooms}><input id="l-bed" type="number" className="input" value={f.bedrooms} onChange={set('bedrooms')} /></Field>
        <Field label="Property type" htmlFor="l-pt"><input id="l-pt" className="input" value={f.property_type} onChange={set('property_type')} /></Field>
        <Field label="Status" htmlFor="l-status"><select id="l-status" className="input" value={f.status} onChange={set('status')}>{LEAD_STATUSES.map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label="Priority" htmlFor="l-pri"><select id="l-pri" className="input" value={f.priority} onChange={set('priority')}>{['low', 'medium', 'high', 'hot'].map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label="Transaction" htmlFor="l-tx"><select id="l-tx" className="input" value={f.transaction_type} onChange={set('transaction_type')}><option value="">—</option>{['buy', 'rent', 'sell'].map((s) => <option key={s}>{s}</option>)}</select></Field>
        {!lead && <Field label="Source" htmlFor="l-src"><select id="l-src" className="input" value={f.source} onChange={set('source')}>{['manual', 'web', 'referral'].map((s) => <option key={s}>{s}</option>)}</select></Field>}
        <Field label="Timeline" htmlFor="l-tl"><input id="l-tl" className="input" value={f.timeline} onChange={set('timeline')} /></Field>
        <Field label="Next follow-up" htmlFor="l-fu"><input id="l-fu" type="datetime-local" className="input" value={f.next_follow_up_at} onChange={set('next_follow_up_at')} /></Field>
        <Field label="Amenities (comma separated)" htmlFor="l-am"><input id="l-am" className="input" value={f.amenities} onChange={set('amenities')} /></Field>
        <Field label="Tags (comma separated)" htmlFor="l-tags"><input id="l-tags" className="input" value={f.tags} onChange={set('tags')} /></Field>
        <div className="sm:col-span-2"><Field label="Notes" htmlFor="l-notes"><textarea id="l-notes" rows={3} className="input" value={f.notes} onChange={set('notes')} /></Field></div>
      </div>
    </Modal>
  )
}

function LeadDetail({ lead, onClose, onEdit }: { lead: Lead; onClose: () => void; onEdit: () => void }) {
  const { can } = useAuth()
  const act = useQuery({ queryKey: ['lead-activity', lead.id], queryFn: () => api.get<ActivityItem[]>(`/leads/${lead.id}/activity`) })
  const mt = useQuery({ queryKey: ['lead-matches', lead.id], queryFn: () => api.get<PropertyMatch[]>(`/leads/${lead.id}/matches`) })
  const archive = useAction(() => api.post<Lead>(`/leads/${lead.id}/${lead.is_archived ? 'restore' : 'archive'}`), { success: lead.is_archived ? 'Lead restored' : 'Lead archived', invalidate: ['leads', 'metrics'], onSuccess: onClose })
  const rescore = useAction(() => api.post<Lead>(`/leads/${lead.id}/rescore`), { success: 'Lead rescored', invalidate: ['leads'], onSuccess: onClose })
  const [confirm, setConfirm] = useState(false)
  const noWrite = can('agent') ? undefined : 'Read-only role'
  return (
    <div className="space-y-5 text-sm">
      <div className="flex flex-wrap items-center gap-2"><Badge color="teal">{lead.status}</Badge><PriorityBadge p={lead.priority} /><span className="font-semibold">Score {lead.score}/100</span></div>
      <div className="flex flex-wrap gap-2">
        <button className="btn-secondary" disabled={!can('agent')} title={noWrite} onClick={onEdit}>Edit</button>
        <button className="btn-secondary" disabled={!can('agent') || rescore.isPending} title={noWrite} onClick={() => rescore.mutate(undefined)}>Rescore</button>
        <button className="btn-secondary" disabled={!can('agent')} title={noWrite} onClick={() => (lead.is_archived ? archive.mutate(undefined) : setConfirm(true))}>{lead.is_archived ? 'Restore' : 'Archive'}</button>
      </div>
      <dl className="grid grid-cols-2 gap-2">
        {([['Email', lead.email], ['Phone', lead.phone], ['Location', lead.preferred_location], ['Type', lead.property_type], ['Bedrooms', lead.bedrooms], ['Budget', lead.budget_min == null && lead.budget_max == null ? null : `${inr(lead.budget_min)} – ${inr(lead.budget_max)}`], ['Timeline', lead.timeline], ['Intent', lead.intent], ['Transaction', lead.transaction_type], ['Source', lead.source], ['Agent', lead.assigned_agent_name], ['Next follow-up', lead.next_follow_up_at ? fmtDate(lead.next_follow_up_at) : null]] as [string, unknown][]).map(([k, v]) => (
          <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd>{v == null || v === '' ? '—' : String(v)}</dd></div>
        ))}
      </dl>
      {lead.amenities.length > 0 && <div className="flex flex-wrap gap-1">{lead.amenities.map((a) => <Badge key={a}>{a}</Badge>)}</div>}
      {lead.notes && <p className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800">{lead.notes}</p>}
      <section><h3 className="mb-1 font-semibold">Score reasons</h3>
        {lead.score_reasons.length === 0 ? <p className="text-slate-500">No scoring detail available.</p> : <ul className="space-y-1">{lead.score_reasons.map((r, i) => <li key={i} className="flex justify-between gap-2 rounded bg-slate-50 px-2 py-1 dark:bg-slate-800"><span><b>{r.factor}</b> — {r.detail}</span><span className="font-mono">{r.points > 0 ? '+' : ''}{r.points}</span></li>)}</ul>}
      </section>
      <section><h3 className="mb-1 font-semibold">Matching properties</h3>
        {mt.isLoading ? <SkeletonRows rows={2} /> : mt.isError ? <ErrorBox error={mt.error} /> : !mt.data?.length ? <p className="text-slate-500">No matching properties found for this lead.</p> :
          <ul className="space-y-1">{mt.data.map((m) => <li key={String(m.property.id)} className="rounded bg-slate-50 p-2 dark:bg-slate-800"><div className="flex justify-between"><b>{m.property.title}</b><span>{m.score}%</span></div><p className="text-xs text-slate-500">{m.explanation}</p></li>)}</ul>}
      </section>
      <section><h3 className="mb-1 font-semibold">Activity timeline</h3>
        {act.isLoading ? <SkeletonRows rows={3} /> : act.isError ? <ErrorBox error={act.error} /> : !act.data?.length ? <p className="text-slate-500">No activity recorded yet.</p> :
          <ol className="space-y-2 border-l pl-4 dark:border-slate-700">{act.data.map((a) => <li key={String(a.id)}><p>{a.message}</p><p className="text-xs text-slate-500">{fmtDate(a.created_at)}{a.actor ? ` · ${a.actor}` : ''}</p></li>)}</ol>}
      </section>
      <Confirm open={confirm} title="Archive lead?" message={`Archive ${lead.full_name}? You can restore it later.`} confirmLabel="Archive" danger busy={archive.isPending} onClose={() => setConfirm(false)} onConfirm={() => archive.mutate(undefined)} />
    </div>
  )
}

export default function Leads() {
  const { can } = useAuth(); const toast = useToast()
  const [q, setQ] = useState(''); const [status, setStatus] = useState(''); const [priority, setPriority] = useState(''); const [source, setSource] = useState('')
  const [archived, setArchived] = useState(false); const [sort, setSort] = useState('-created_at'); const [page, setPage] = useState(1)
  const dq = useDebounced(q)
  const list = useList<Lead>('leads', '/leads', { q: dq, status, priority, source, include_archived: archived || undefined, sort, page, page_size: 20 })
  const [sel, setSel] = useState<Lead | null>(null); const [form, setForm] = useState<{ lead?: Lead } | null>(null)
  const reset = <T,>(fn: (v: T) => void) => (v: T) => { fn(v); setPage(1) }
  const exportCsv = async () => { try { await download('/leads/export.csv', 'leads.csv'); toast.success('Leads exported') } catch (e) { toast.error(e) } }
  return (
    <div>
      <PageHeader title="Leads" subtitle="Track and score prospects" actions={<>
        <button className="btn-secondary" onClick={exportCsv}><Download className="h-4 w-4" />Export CSV</button>
        <button className="btn-primary" disabled={!can('agent')} title={can('agent') ? undefined : 'Your role is read-only'} onClick={() => setForm({})}><Plus className="h-4 w-4" />New lead</button>
      </>} />
      <div className="card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search leads" placeholder="Search leads…" className="input !w-60 !pl-8" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
          <Select label="Status filter" value={status} onChange={reset(setStatus)} options={LEAD_STATUSES.map((s) => ({ value: s, label: s }))} placeholder="All statuses" />
          <Select label="Priority filter" value={priority} onChange={reset(setPriority)} options={['low', 'medium', 'high', 'hot']} placeholder="All priorities" />
          <Select label="Source filter" value={source} onChange={reset(setSource)} options={['email', 'manual', 'web', 'referral', 'gmail', 'demo']} placeholder="All sources" />
          <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={archived} onChange={(e) => { setArchived(e.target.checked); setPage(1) }} />Show archived</label>
        </div>
        {list.isLoading ? <SkeletonRows /> : list.isError ? <ErrorBox error={list.error} retry={() => list.refetch()} /> : (
          <>
            <LeadTable leads={list.data!.items} sort={sort} onSort={setSort} onOpen={setSel} />
            <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
          </>
        )}
      </div>
      <Drawer open={!!sel && !form} onClose={() => setSel(null)} title={sel?.full_name ?? ''}>{sel && <LeadDetail lead={sel} onClose={() => setSel(null)} onEdit={() => setForm({ lead: sel })} />}</Drawer>
      {form && <LeadFormModal key={String(form.lead?.id ?? 'new')} lead={form.lead} open onClose={() => { setForm(null); setSel(null) }} />}
    </div>
  )
}
