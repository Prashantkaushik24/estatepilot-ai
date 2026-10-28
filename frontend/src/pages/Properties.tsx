import { useState } from 'react'
import { Plus, Search } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction, useList } from '../lib/hooks'
import { inr, label } from '../lib/format'
import type { Property } from '../types'
import { Badge, Confirm, DemoBadge, Empty, ErrorBox, Field, ListToArr, Modal, PageHeader, Pagination, Select, SkeletonRows, useDebounced } from '../components/ui'

const TYPES = ['apartment', 'villa', 'house', 'plot', 'commercial']
const STATUSES = ['available', 'reserved', 'sold', 'rented']

function PropertyModal({ p, onClose }: { p?: Property; onClose: () => void }) {
  const [f, setF] = useState({
    title: p?.title ?? '', property_type: p?.property_type ?? 'apartment', listing_type: p?.listing_type ?? 'sale', price: p?.price?.toString() ?? '', location: p?.location ?? '', city: p?.city ?? '',
    bedrooms: p?.bedrooms?.toString() ?? '', bathrooms: p?.bathrooms?.toString() ?? '', area_sqft: p?.area_sqft?.toString() ?? '', units_available: p?.units_available?.toString() ?? '1',
    amenities: (p?.amenities ?? []).join(', '), status: p?.status ?? 'available', description: p?.description ?? '', url: p?.url ?? '',
  })
  const [errs, setErrs] = useState<Record<string, string>>({})
  const save = useAction((b: any) => (p ? api.patch(`/properties/${p.id}`, b) : api.post('/properties', b)), { success: p ? 'Property updated' : 'Property created', invalidate: ['properties'], onSuccess: onClose })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const e: Record<string, string> = {}
    if (!f.title.trim()) e.title = 'Title is required'
    if (!f.location.trim()) e.location = 'Location is required'
    if (f.price === '' || isNaN(Number(f.price)) || Number(f.price) < 0) e.price = 'Enter a valid price'
    if (f.units_available === '' || !Number.isInteger(Number(f.units_available)) || Number(f.units_available) < 0) e.units_available = 'Whole number required'
    setErrs(e); if (Object.keys(e).length) return
    const n = (s: string) => (s === '' ? null : Number(s))
    save.mutate({ ...f, price: Number(f.price), bedrooms: n(f.bedrooms), bathrooms: n(f.bathrooms), area_sqft: n(f.area_sqft), units_available: Number(f.units_available), amenities: ListToArr(f.amenities), city: f.city || null, description: f.description || null, url: f.url || null })
  }
  return (
    <Modal open onClose={onClose} title={p ? 'Edit property' : 'New property'} wide footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={save.isPending} onClick={submit}>{save.isPending ? 'Saving…' : 'Save'}</button></>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Title *" htmlFor="p-title" error={errs.title}><input id="p-title" className="input" value={f.title} onChange={set('title')} /></Field>
        <Field label="Price (INR) *" htmlFor="p-price" error={errs.price}><input id="p-price" type="number" className="input" value={f.price} onChange={set('price')} /></Field>
        <Field label="Location *" htmlFor="p-loc" error={errs.location}><input id="p-loc" className="input" value={f.location} onChange={set('location')} /></Field>
        <Field label="City" htmlFor="p-city"><input id="p-city" className="input" value={f.city} onChange={set('city')} /></Field>
        <Field label="Type" htmlFor="p-type"><select id="p-type" className="input" value={f.property_type} onChange={set('property_type')}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select></Field>
        <Field label="Listing" htmlFor="p-list"><select id="p-list" className="input" value={f.listing_type} onChange={set('listing_type')}><option>sale</option><option>rent</option></select></Field>
        <Field label="Bedrooms" htmlFor="p-bed"><input id="p-bed" type="number" className="input" value={f.bedrooms} onChange={set('bedrooms')} /></Field>
        <Field label="Bathrooms" htmlFor="p-bath"><input id="p-bath" type="number" className="input" value={f.bathrooms} onChange={set('bathrooms')} /></Field>
        <Field label="Area (sq ft)" htmlFor="p-area"><input id="p-area" type="number" className="input" value={f.area_sqft} onChange={set('area_sqft')} /></Field>
        <Field label="Units available" htmlFor="p-units" error={errs.units_available}><input id="p-units" type="number" className="input" value={f.units_available} onChange={set('units_available')} /></Field>
        <Field label="Status" htmlFor="p-status"><select id="p-status" className="input" value={f.status} onChange={set('status')}>{STATUSES.map((t) => <option key={t}>{t}</option>)}</select></Field>
        <Field label="Listing URL" htmlFor="p-url"><input id="p-url" className="input" value={f.url} onChange={set('url')} /></Field>
        <div className="sm:col-span-2"><Field label="Amenities (comma separated)" htmlFor="p-am"><input id="p-am" className="input" value={f.amenities} onChange={set('amenities')} /></Field></div>
        <div className="sm:col-span-2"><Field label="Description" htmlFor="p-desc"><textarea id="p-desc" rows={3} className="input" value={f.description} onChange={set('description')} /></Field></div>
      </div>
    </Modal>
  )
}

export default function Properties() {
  const { can } = useAuth()
  const [q, setQ] = useState(''); const [status, setStatus] = useState(''); const [type, setType] = useState(''); const [location, setLocation] = useState(''); const [page, setPage] = useState(1)
  const dq = useDebounced(q); const dl = useDebounced(location)
  const list = useList<Property>('properties', '/properties', { q: dq, status, property_type: type, location: dl, page, page_size: 20, sort: '-created_at' })
  const [edit, setEdit] = useState<{ p?: Property } | null>(null); const [del, setDel] = useState<Property | null>(null)
  const rm = useAction((id: Property['id']) => api.del(`/properties/${id}`), { success: 'Property deleted', invalidate: ['properties'], onSuccess: () => setDel(null) })
  return (
    <div>
      <PageHeader title="Properties" subtitle="Inventory used for matching" actions={<button className="btn-primary" disabled={!can('agent')} title={can('agent') ? undefined : 'Your role is read-only'} onClick={() => setEdit({})}><Plus className="h-4 w-4" />New property</button>} />
      <div className="card">
        <div className="mb-3 flex flex-wrap gap-2">
          <div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search properties" placeholder="Search…" className="input !w-56 !pl-8" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
          <input aria-label="Location filter" placeholder="Location" className="input !w-40" value={location} onChange={(e) => { setLocation(e.target.value); setPage(1) }} />
          <Select label="Type filter" value={type} onChange={(v) => { setType(v); setPage(1) }} options={TYPES} placeholder="All types" />
          <Select label="Status filter" value={status} onChange={(v) => { setStatus(v); setPage(1) }} options={STATUSES} placeholder="All statuses" />
        </div>
        {list.isLoading ? <SkeletonRows /> : list.isError ? <ErrorBox error={list.error} retry={() => list.refetch()} /> : list.data!.items.length === 0 ? <Empty title="No properties found" hint="Add a property or change the filters." /> : (
          <>
            <div className="overflow-x-auto"><table className="w-full"><thead className="border-b dark:border-slate-800"><tr>{['Title', 'Type', 'Price', 'Location', 'Beds', 'Units', 'Status', ''].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody className="divide-y dark:divide-slate-800">{list.data!.items.map((p) => (
                <tr key={String(p.id)}>
                  <td className="td font-medium">{p.title} {p.is_demo && <DemoBadge />}</td><td className="td">{label(p.property_type)} · {p.listing_type}</td><td className="td">{inr(p.price)}</td><td className="td">{p.location}</td><td className="td">{p.bedrooms ?? '—'}</td><td className="td">{p.units_available}</td>
                  <td className="td"><Badge color={p.status === 'available' ? 'green' : 'gray'}>{p.status}</Badge></td>
                  <td className="td whitespace-nowrap"><button className="btn-ghost" disabled={!can('agent')} title={can('agent') ? undefined : 'Your role is read-only'} onClick={() => setEdit({ p })}>Edit</button><button className="btn-ghost text-red-600" disabled={!can('manager')} title={can('manager') ? undefined : 'Deleting requires manager or admin role'} onClick={() => setDel(p)}>Delete</button></td>
                </tr>))}</tbody></table></div>
            <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
          </>
        )}
      </div>
      {edit && <PropertyModal key={String(edit.p?.id ?? 'new')} p={edit.p} onClose={() => setEdit(null)} />}
      <Confirm open={!!del} title="Delete property?" message={`Permanently delete "${del?.title}"?`} confirmLabel="Delete" danger busy={rm.isPending} onClose={() => setDel(null)} onConfirm={() => del && rm.mutate(del.id)} />
    </div>
  )
}
