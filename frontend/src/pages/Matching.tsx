import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAction, useList } from '../lib/hooks'
import { ListToArr, Empty, ErrorBox, Field, PageHeader, SkeletonRows } from '../components/ui'
import { MatchCard } from '../components/MatchCard'
import type { Lead, MatchSearch, PropertyMatch } from '../types'

export default function Matching() {
  const [f, setF] = useState({ location: '', budget_min: '', budget_max: '', bedrooms: '', property_type: '', amenities: '' })
  const [errs, setErrs] = useState<Record<string, string>>({})
  const [results, setResults] = useState<PropertyMatch[] | null>(null)
  const search = useAction((b: MatchSearch) => api.post<PropertyMatch[]>('/matches/search', b), { onSuccess: setResults })
  const submit = () => {
    const e: Record<string, string> = {}
    const min = f.budget_min === '' ? undefined : Number(f.budget_min), max = f.budget_max === '' ? undefined : Number(f.budget_max)
    if (min != null && (isNaN(min) || min < 0)) e.budget_min = 'Invalid'
    if (max != null && (isNaN(max) || max < 0)) e.budget_max = 'Invalid'
    if (min != null && max != null && min > max) e.budget_max = 'Max must be at least min'
    setErrs(e); if (Object.keys(e).length) return
    search.mutate({ location: f.location || undefined, budget_min: min, budget_max: max, bedrooms: f.bedrooms === '' ? undefined : Number(f.bedrooms), property_type: f.property_type || undefined, amenities: ListToArr(f.amenities) })
  }
  const [leadId, setLeadId] = useState('')
  const leads = useList<Lead>('leads', '/leads', { page_size: 200, sort: 'full_name' })
  const lm = useQuery({ queryKey: ['lead-matches', leadId], queryFn: () => api.get<PropertyMatch[]>(`/leads/${leadId}/matches`), enabled: !!leadId })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  return (
    <div>
      <PageHeader title="Matching" subtitle="Find properties for a search or a lead" />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card" aria-label="Ad-hoc search">
          <h2 className="mb-3 font-semibold">Ad-hoc search</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Location" htmlFor="m-loc"><input id="m-loc" className="input" value={f.location} onChange={set('location')} /></Field>
            <Field label="Property type" htmlFor="m-type"><select id="m-type" className="input" value={f.property_type} onChange={set('property_type')}><option value="">Any</option>{['apartment', 'villa', 'house', 'plot', 'commercial'].map((t) => <option key={t}>{t}</option>)}</select></Field>
            <Field label="Budget min (INR)" htmlFor="m-min" error={errs.budget_min}><input id="m-min" type="number" className="input" value={f.budget_min} onChange={set('budget_min')} /></Field>
            <Field label="Budget max (INR)" htmlFor="m-max" error={errs.budget_max}><input id="m-max" type="number" className="input" value={f.budget_max} onChange={set('budget_max')} /></Field>
            <Field label="Bedrooms" htmlFor="m-bed"><input id="m-bed" type="number" className="input" value={f.bedrooms} onChange={set('bedrooms')} /></Field>
            <Field label="Amenities (comma separated)" htmlFor="m-am"><input id="m-am" className="input" value={f.amenities} onChange={set('amenities')} /></Field>
          </div>
          <button className="btn-primary mt-3" disabled={search.isPending} onClick={submit}>{search.isPending ? 'Searching…' : 'Search'}</button>
          <div className="mt-4 space-y-3">
            {search.isPending ? <SkeletonRows rows={2} /> : results && (results.length === 0 ? <Empty title="No matching properties" hint="No available property fits these criteria. Try relaxing budget, location or bedrooms." /> : results.map((m) => <MatchCard key={String(m.property.id)} m={m} />))}
          </div>
        </section>
        <section className="card" aria-label="Lead matches">
          <h2 className="mb-3 font-semibold">Matches for a lead</h2>
          <select aria-label="Select lead" className="input mb-3" value={leadId} onChange={(e) => setLeadId(e.target.value)}>
            <option value="">{leads.isLoading ? 'Loading leads…' : 'Select a lead'}</option>
            {leads.data?.items.map((l) => <option key={String(l.id)} value={String(l.id)}>{l.full_name}</option>)}
          </select>
          {!leadId ? <Empty title="Select a lead" hint="Matches are computed from the lead's saved requirements." /> : lm.isLoading ? <SkeletonRows rows={2} /> : lm.isError ? <ErrorBox error={lm.error} retry={() => lm.refetch()} /> :
            lm.data!.length === 0 ? <Empty title="No matching properties" hint="No available property fits this lead's requirements." /> : <div className="space-y-3">{lm.data!.map((m) => <MatchCard key={String(m.property.id)} m={m} />)}</div>}
        </section>
      </div>
    </div>
  )
}
