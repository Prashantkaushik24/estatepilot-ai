import { useState } from 'react'
import { Bell, Check, Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction, useList } from '../lib/hooks'
import { fmtDate, fromLocalInput, toLocalInput } from '../lib/format'
import type { Lead, Task } from '../types'
import { Badge, Confirm, Empty, ErrorBox, Field, Modal, PageHeader, Pagination, PriorityBadge, Select, SkeletonRows } from '../components/ui'

function TaskModal({ t, onClose }: { t?: Task; onClose: () => void }) {
  const [f, setF] = useState({ title: t?.title ?? '', description: t?.description ?? '', lead_id: t?.lead_id ? String(t.lead_id) : '', priority: t?.priority ?? 'medium', due_at: toLocalInput(t?.due_at), reminder_at: toLocalInput(t?.reminder_at) })
  const [errs, setErrs] = useState<Record<string, string>>({})
  const leads = useList<Lead>('leads', '/leads', { page_size: 200, sort: 'full_name' })
  const save = useAction((b: any) => (t ? api.patch(`/tasks/${t.id}`, b) : api.post('/tasks', b)), { success: t ? 'Task updated' : 'Task created', invalidate: ['tasks', 'metrics', 'reminders'], onSuccess: onClose })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const e: Record<string, string> = {}
    if (!f.title.trim()) e.title = 'Title is required'
    if (!f.due_at) e.due_at = 'Due date is required'
    if (f.reminder_at && f.due_at && new Date(f.reminder_at) > new Date(f.due_at)) e.reminder_at = 'Reminder must be before the due date'
    setErrs(e); if (Object.keys(e).length) return
    save.mutate({ title: f.title.trim(), description: f.description || null, lead_id: f.lead_id || null, priority: f.priority, due_at: fromLocalInput(f.due_at), reminder_at: fromLocalInput(f.reminder_at) ?? null })
  }
  return (
    <Modal open onClose={onClose} title={t ? 'Edit task' : 'New follow-up task'} footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={save.isPending} onClick={submit}>{save.isPending ? 'Saving…' : 'Save'}</button></>}>
      <div className="space-y-3">
        <Field label="Title *" htmlFor="t-title" error={errs.title}><input id="t-title" className="input" value={f.title} onChange={set('title')} /></Field>
        <Field label="Description" htmlFor="t-desc"><textarea id="t-desc" rows={2} className="input" value={f.description} onChange={set('description')} /></Field>
        <Field label="Lead" htmlFor="t-lead"><select id="t-lead" className="input" value={f.lead_id} onChange={set('lead_id')}><option value="">None</option>{leads.data?.items.map((l) => <option key={String(l.id)} value={String(l.id)}>{l.full_name}</option>)}</select></Field>
        <Field label="Priority" htmlFor="t-pri"><select id="t-pri" className="input" value={f.priority} onChange={set('priority')}>{['low', 'medium', 'high', 'hot'].map((p) => <option key={p}>{p}</option>)}</select></Field>
        <Field label="Due *" htmlFor="t-due" error={errs.due_at}><input id="t-due" type="datetime-local" className="input" value={f.due_at} onChange={set('due_at')} /></Field>
        <Field label="Reminder" htmlFor="t-rem" error={errs.reminder_at}><input id="t-rem" type="datetime-local" className="input" value={f.reminder_at} onChange={set('reminder_at')} /></Field>
      </div>
    </Modal>
  )
}

export default function Followups() {
  const { can } = useAuth()
  const [status, setStatus] = useState('pending'); const [overdue, setOverdue] = useState(false); const [page, setPage] = useState(1)
  const list = useList<Task>('tasks', '/tasks', { status, overdue: overdue || undefined, page, page_size: 20 })
  const rem = useQuery({ queryKey: ['reminders'], queryFn: () => api.get<Task[] | { items: Task[] }>('/tasks/reminders') })
  const reminders = Array.isArray(rem.data) ? rem.data : rem.data?.items ?? []
  const [edit, setEdit] = useState<{ t?: Task } | null>(null); const [del, setDel] = useState<Task | null>(null)
  const done = useAction((id: Task['id']) => api.post(`/tasks/${id}/complete`), { success: 'Task completed', invalidate: ['tasks', 'metrics', 'reminders'] })
  const rm = useAction((id: Task['id']) => api.del(`/tasks/${id}`), { success: 'Task deleted', invalidate: ['tasks', 'metrics', 'reminders'], onSuccess: () => setDel(null) })
  const ro = can('agent') ? undefined : 'Your role is read-only'
  return (
    <div>
      <PageHeader title="Follow-ups" subtitle="Tasks and reminders" actions={<button className="btn-primary" disabled={!can('agent')} title={ro} onClick={() => setEdit({})}><Plus className="h-4 w-4" />New task</button>} />
      {reminders.length > 0 && (
        <section className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950" aria-label="Reminders">
          <h2 className="mb-1 flex items-center gap-1 font-semibold"><Bell className="h-4 w-4" />Reminders ({reminders.length})</h2>
          <ul className="list-disc pl-5">{reminders.map((t) => <li key={String(t.id)}>{t.title}{t.lead_name ? ` — ${t.lead_name}` : ''} (due {fmtDate(t.due_at)})</li>)}</ul>
        </section>
      )}
      <div className="card">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Select label="Status filter" value={status} onChange={(v) => { setStatus(v); setPage(1) }} options={['pending', 'completed', 'cancelled']} placeholder="All statuses" />
          <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={overdue} onChange={(e) => { setOverdue(e.target.checked); setPage(1) }} />Overdue only</label>
        </div>
        {list.isLoading ? <SkeletonRows /> : list.isError ? <ErrorBox error={list.error} retry={() => list.refetch()} /> : list.data!.items.length === 0 ? <Empty title="No tasks" hint="No tasks match the current filters." /> : (
          <>
            <div className="overflow-x-auto"><table className="w-full"><thead className="border-b dark:border-slate-800"><tr>{['Task', 'Lead', 'Priority', 'Due', 'Status', ''].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody className="divide-y dark:divide-slate-800">{list.data!.items.map((t) => (
                <tr key={String(t.id)}>
                  <td className="td font-medium">{t.title} {t.source === 'ai' && <Badge color="purple">AI</Badge>}</td><td className="td">{t.lead_name ?? '—'}</td><td className="td"><PriorityBadge p={t.priority} /></td>
                  <td className="td">{fmtDate(t.due_at)} {t.is_overdue && t.status === 'pending' && <Badge color="red">Overdue</Badge>}</td><td className="td">{t.status}</td>
                  <td className="td whitespace-nowrap">
                    <button className="btn-ghost" disabled={!can('agent') || t.status !== 'pending' || done.isPending} title={!can('agent') ? ro : t.status !== 'pending' ? 'Task is not pending' : undefined} onClick={() => done.mutate(t.id)}><Check className="h-4 w-4" />Complete</button>
                    <button className="btn-ghost" disabled={!can('agent')} title={ro} onClick={() => setEdit({ t })}>Edit</button>
                    <button className="btn-ghost text-red-600" disabled={!can('agent')} title={ro} onClick={() => setDel(t)}>Delete</button>
                  </td>
                </tr>))}</tbody></table></div>
            <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
          </>
        )}
      </div>
      {edit && <TaskModal key={String(edit.t?.id ?? 'new')} t={edit.t} onClose={() => setEdit(null)} />}
      <Confirm open={!!del} title="Delete task?" message={`Delete "${del?.title}"?`} confirmLabel="Delete" danger busy={rm.isPending} onClose={() => setDel(null)} onConfirm={() => del && rm.mutate(del.id)} />
    </div>
  )
}
