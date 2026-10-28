import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ClipboardPaste, Download, Play, RefreshCw, Search, Send } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useAction, useIntegrations, useList } from '../lib/hooks'
import { useToast } from '../lib/toast'
import { fmtDate, inr, isEmail, label } from '../lib/format'
import type { Draft, Email, EmailImport, IntegrationStatus, ProcessResult, StepResult } from '../types'
import { Badge, DemoAIBadge, Empty, ErrorBox, Field, Modal, PageHeader, Pagination, PriorityBadge, Select, SkeletonRows, useDebounced } from '../components/ui'

const CLASSES = ['property_inquiry', 'buying_request', 'selling_request', 'rental_inquiry', 'property_listing_submission', 'site_visit_request', 'pricing_inquiry', 'follow_up', 'complaint', 'spam', 'other']
const STATUSES = ['pending', 'processing', 'processed', 'failed', 'skipped']

export function sendBlockReason(draft: Draft | null | undefined, integ?: IntegrationStatus, canSend = true): string | null {
  if (!canSend) return 'Your role cannot send emails'
  if (!draft) return 'No draft available'
  if (draft.status === 'sent') return 'This draft was already sent'
  if (!integ) return 'Checking integration status…'
  if (integ.kill_switch) return 'Kill switch is on — sending is disabled'
  if (!integ.sending_enabled) return 'Sending is disabled on the server (SENDING_ENABLED=false)'
  if (!integ.gmail.connected) return 'Gmail is not connected (see Settings)'
  if (draft.status !== 'approved') return 'Approve the draft before sending'
  return null
}

function ImportDialog({ onClose, onDone }: { onClose: () => void; onDone: (e: Email) => void }) {
  const [f, setF] = useState({ sender_email: '', sender_name: '', subject: '', body: '' }); const [process, setProcess] = useState(true)
  const [errs, setErrs] = useState<Record<string, string>>({}); const [dup, setDup] = useState<string | null>(null)
  const imp = useAction((b: EmailImport) => api.post<ProcessResult>('/emails/import', b), {
    success: (r) => (r.email.processing_status === 'processed' ? 'Email imported and processed' : 'Email imported'), invalidate: ['emails', 'metrics', 'leads'],
    onSuccess: (r) => { onDone(r.email); onClose() },
    onError: (e) => { if (e instanceof ApiError && e.status === 409 && String(e.message).toLowerCase().includes('duplicate')) setDup(`This email was already imported${e.body?.existing_email_id ? ` (email #${e.body.existing_email_id})` : ''}.`); else if (e instanceof ApiError && e.status === 409) setDup(e.message); else setDup(e instanceof Error ? e.message : 'Import failed') },
  })
  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const submit = () => {
    const e: Record<string, string> = {}
    if (!isEmail(f.sender_email)) e.sender_email = 'Valid sender email required'
    if (!f.subject.trim()) e.subject = 'Subject is required'
    if (!f.body.trim()) e.body = 'Body is required'
    setErrs(e); setDup(null); if (Object.keys(e).length) return
    imp.mutate({ sender_email: f.sender_email, sender_name: f.sender_name || undefined, subject: f.subject, body: f.body, process, source: 'paste' })
  }
  return (
    <Modal open onClose={onClose} title="Paste email" wide footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={imp.isPending} onClick={submit}>{imp.isPending ? 'Importing…' : 'Import'}</button></>}>
      <div className="space-y-3">
        {dup && <div role="alert" className="rounded-lg bg-amber-50 p-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200">{dup}</div>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Sender email *" htmlFor="i-email" error={errs.sender_email}><input id="i-email" className="input" value={f.sender_email} onChange={set('sender_email')} /></Field>
          <Field label="Sender name" htmlFor="i-name"><input id="i-name" className="input" value={f.sender_name} onChange={set('sender_name')} /></Field>
        </div>
        <Field label="Subject *" htmlFor="i-sub" error={errs.subject}><input id="i-sub" className="input" value={f.subject} onChange={set('subject')} /></Field>
        <Field label="Body *" htmlFor="i-body" error={errs.body}><textarea id="i-body" rows={8} className="input" value={f.body} onChange={set('body')} /></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={process} onChange={(e) => setProcess(e.target.checked)} />Process with AI after import</label>
      </div>
    </Modal>
  )
}

function SendDialog({ draft, to, onClose }: { draft: Draft; to: string; onClose: () => void }) {
  const send = useAction(() => api.post(`/drafts/${draft.id}/send`, { confirm: true, confirm_recipient: to }), { success: 'Email sent', invalidate: ['emails', 'email'], onSuccess: onClose })
  return (
    <Modal open onClose={onClose} title="Confirm send" wide footer={<><button className="btn-secondary" onClick={onClose}>Cancel</button><button className="btn-primary" disabled={send.isPending} onClick={() => send.mutate(undefined)}><Send className="h-4 w-4" />{send.isPending ? 'Sending…' : 'Send email'}</button></>}>
      <dl className="space-y-2 text-sm">
        <div><dt className="text-xs text-slate-500">To</dt><dd className="font-medium">{to}</dd></div>
        <div><dt className="text-xs text-slate-500">Subject</dt><dd className="font-medium">{draft.subject}</dd></div>
        <div><dt className="text-xs text-slate-500">Body</dt><dd className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 dark:bg-slate-800">{draft.body}</dd></div>
      </dl>
      <p className="mt-3 text-xs text-slate-500">This will send a real email through the connected Gmail account.</p>
    </Modal>
  )
}

function StepsList({ steps }: { steps: StepResult[] }) {
  return <ol className="space-y-1 text-sm">{steps.map((s, i) => <li key={i} className="flex items-start gap-2"><Badge color={s.status === 'ok' ? 'green' : s.status === 'failed' ? 'red' : 'gray'}>{s.status}</Badge><span><b>{label(s.name)}</b>{s.detail ? ` — ${s.detail}` : ''}</span></li>)}</ol>
}

function Composer({ email, can, integ, onSaved }: { email: Email; can: (r: any) => boolean; integ?: IntegrationStatus; onSaved: () => void }) {
  const dq = useQuery({ queryKey: ['draft', email.id, email.draft?.updated_at], queryFn: () => api.get<Draft>(`/emails/${email.id}/draft`), enabled: !!email.draft, retry: false })
  const draft = dq.data ?? email.draft ?? null
  const [subject, setSubject] = useState(''); const [body, setBody] = useState(''); const [send, setSend] = useState(false)
  useEffect(() => { if (draft) { setSubject(draft.subject); setBody(draft.body) } }, [draft?.id, draft?.updated_at]) // eslint-disable-line
  const dirty = !!draft && (subject !== draft.subject || body !== draft.body)
  const inv = { invalidate: ['emails', 'email', 'draft'], onSuccess: onSaved }
  const save = useAction(() => api.put<Draft>(`/emails/${email.id}/draft`, { subject, body }), { success: 'Draft saved', ...inv })
  const regen = useAction(() => api.post<Draft>(`/emails/${email.id}/draft/regenerate`), { success: 'Draft regenerated', ...inv })
  const approve = useAction(() => api.post<Draft>(`/drafts/${draft!.id}/approve`), { success: 'Draft approved', ...inv })
  const ro = can('agent') ? undefined : 'Your role is read-only'
  const block = sendBlockReason(draft, integ, can('agent'))
  if (!draft) return <Empty title="No draft yet" hint={email.processing_status === 'processed' ? 'No reply draft was generated (the drafting rule may be disabled).' : 'Process the email to generate a reply draft.'} />
  const editable = draft.status === 'draft' || draft.status === 'approved'
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2"><h3 className="font-semibold">Reply draft</h3><Badge color={draft.status === 'sent' ? 'green' : draft.status === 'approved' ? 'teal' : 'gray'}>{draft.status}</Badge>{draft.is_demo_ai && <DemoAIBadge />}</div>
      <input aria-label="Draft subject" className="input" value={subject} disabled={!editable || !can('agent')} onChange={(e) => setSubject(e.target.value)} />
      <textarea aria-label="Draft body" rows={10} className="input font-mono" value={body} disabled={!editable || !can('agent')} onChange={(e) => setBody(e.target.value)} />
      {draft.status === 'approved' && dirty && <p className="text-xs text-amber-600">Saving edits may reset approval; re-approve before sending.</p>}
      <div className="flex flex-wrap gap-2">
        <button className="btn-secondary" disabled={!can('agent') || !editable || !dirty || save.isPending} title={ro ?? (!dirty ? 'No changes to save' : undefined)} onClick={() => save.mutate(undefined)}>Save draft</button>
        <button className="btn-secondary" disabled={!can('agent') || !editable || regen.isPending} title={ro} onClick={() => regen.mutate(undefined)}><RefreshCw className="h-4 w-4" />{regen.isPending ? 'Regenerating…' : 'Regenerate'}</button>
        <button className="btn-secondary" disabled={!can('agent') || draft.status !== 'draft' || dirty || approve.isPending} title={ro ?? (dirty ? 'Save your edits first' : draft.status !== 'draft' ? `Draft is already ${draft.status}` : undefined)} onClick={() => approve.mutate(undefined)}>Approve</button>
        <span title={block ?? undefined}><button className="btn-primary" disabled={!!block || dirty} onClick={() => setSend(true)}><Send className="h-4 w-4" />Send</button></span>
      </div>
      {(block || dirty) && <p className="text-xs text-slate-500">Send disabled: {dirty && !block ? 'save your edits first' : block}</p>}
      {send && <SendDialog draft={draft} to={email.sender_email} onClose={() => setSend(false)} />}
    </div>
  )
}

function EmailDetail({ id, integ }: { id: Email['id']; integ?: IntegrationStatus }) {
  const { can } = useAuth(); const qc = useQueryClient(); const toast = useToast()
  const q = useQuery({ queryKey: ['email', id], queryFn: () => api.get<Email>(`/emails/${id}`) })
  const [result, setResult] = useState<ProcessResult | null>(null)
  useEffect(() => { setResult(null) }, [id])
  const proc = useAction(() => api.post<ProcessResult>(`/emails/${id}/process`), {
    success: 'Email processed', invalidate: ['emails', 'email', 'metrics', 'leads', 'draft'], onSuccess: setResult,
  })
  useEffect(() => { if (q.data && !q.data.is_read && can('agent')) api.patch(`/emails/${id}`, { is_read: true }).then(() => qc.invalidateQueries({ queryKey: ['emails'] })).catch(() => {}) }, [id, q.data?.is_read]) // eslint-disable-line
  if (q.isLoading) return <SkeletonRows rows={6} />
  if (q.isError) return <ErrorBox error={q.error} retry={() => q.refetch()} />
  const e = q.data!
  const x = e.extraction
  const matches = result?.matches
  const steps = result?.steps ?? result?.run?.steps
  const canProc = can('agent') && e.processing_status !== 'processing' && e.processing_status !== 'processed'
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><h2 className="text-lg font-semibold">{e.subject}</h2><p className="text-sm text-slate-500">{e.sender_name ? `${e.sender_name} ` : ''}&lt;{e.sender_email}&gt; · {fmtDate(e.received_at)}</p></div>
        <div className="flex flex-wrap items-center gap-1">
          {e.classification && <Badge color="blue">{label(e.classification)}</Badge>}<PriorityBadge p={e.priority} /><Badge color={e.processing_status === 'failed' ? 'red' : e.processing_status === 'processed' ? 'green' : 'gray'}>{e.processing_status}</Badge>{e.is_demo_ai && <DemoAIBadge />}
        </div>
      </div>
      {e.error && <ErrorBox error={new Error(e.error)} />}
      <div className="flex gap-2">
        <button className="btn-primary" disabled={!canProc || proc.isPending} title={!can('agent') ? 'Your role is read-only' : e.processing_status === 'processed' ? 'Already processed' : undefined} onClick={() => proc.mutate(undefined)}>
          <Play className="h-4 w-4" />{proc.isPending ? 'Processing…' : e.processing_status === 'failed' ? 'Retry' : 'Process'}
        </button>
        {e.processing_status === 'processed' && can('agent') && <button className="btn-secondary" disabled={proc.isPending} onClick={() => proc.mutate(undefined)} title="Run the pipeline again">Reprocess</button>}
        {e.lead_name && <Badge color="teal">Lead: {e.lead_name}</Badge>}
      </div>
      <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800">{e.body}</pre>
      {e.summary && <section><h3 className="mb-1 font-semibold">Summary</h3><p className="text-sm">{e.summary}</p></section>}
      {x && (
        <section><h3 className="mb-1 font-semibold">Extraction</h3>
          <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            {([['Customer', x.customer_name], ['Email', x.sender_email], ['Phone', x.phone], ['Intent', x.intent], ['Location', x.preferred_location], ['Type', x.property_type], ['Bedrooms', x.bedrooms], ['Budget', x.budget_min == null && x.budget_max == null ? null : `${inr(x.budget_min)} – ${inr(x.budget_max)}`], ['Transaction', x.transaction_type], ['Timeline', x.timeline], ['Urgency', x.urgency], ['Amenities', x.amenities?.join(', ')]] as [string, unknown][]).map(([k, v]) => <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd>{v == null || v === '' ? '—' : String(v)}</dd></div>)}
          </dl>
          {x.missing_information?.length > 0 && <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">Missing: {x.missing_information.join(', ')}</p>}
        </section>
      )}
      {steps && steps.length > 0 && <section><h3 className="mb-1 font-semibold">Processing steps</h3><StepsList steps={steps} /></section>}
      {matches && <section><h3 className="mb-1 font-semibold">Matched properties</h3>{matches.length === 0 ? <p className="text-sm text-slate-500">No matching properties found.</p> : <ul className="space-y-1 text-sm">{matches.map((m) => <li key={String(m.property.id)} className="rounded bg-slate-50 p-2 dark:bg-slate-800"><b>{m.property.title}</b> — {m.score}% · {inr(m.property.price)}<p className="text-xs text-slate-500">{m.explanation}</p></li>)}</ul>}</section>}
      {!matches && e.lead_id && <p className="text-xs text-slate-500">Matched properties are shown after processing, or open the lead in Leads.</p>}
      <section><Composer email={e} can={can} integ={integ} onSaved={() => toast.info('Updated')} /></section>
    </div>
  )
}

export default function Inbox() {
  const { can } = useAuth(); const toast = useToast()
  const integ = useIntegrations()
  const [q, setQ] = useState(''); const [cls, setCls] = useState(''); const [ps, setPs] = useState(''); const [page, setPage] = useState(1); const dq = useDebounced(q)
  const list = useList<Email>('emails', '/emails', { q: dq, classification: cls, processing_status: ps, page, page_size: 20, sort: '-received_at' })
  const [sel, setSel] = useState<Email['id'] | null>(null); const [paste, setPaste] = useState(false)
  const demo = useAction(() => api.post<{ created: number; emails: Email[] }>('/emails/demo'), { success: (r) => (r.created ? `Loaded ${r.created} demo emails` : 'Demo emails already loaded'), invalidate: ['emails'], onSuccess: (r) => r.emails?.[0] && setSel(r.emails[0].id) })
  const ro = can('agent') ? undefined : 'Your role is read-only'
  void toast
  return (
    <div>
      <PageHeader title="Inbox" subtitle="Customer emails, AI extraction and reply drafts" actions={<>
        <button className="btn-secondary" disabled={!can('agent') || demo.isPending} title={ro} onClick={() => demo.mutate(undefined)}><Download className="h-4 w-4" />Load demo emails</button>
        <button className="btn-primary" disabled={!can('agent')} title={ro} onClick={() => setPaste(true)}><ClipboardPaste className="h-4 w-4" />Paste email</button>
      </>} />
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="card self-start">
          <div className="mb-3 space-y-2">
            <div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search emails" placeholder="Search emails…" className="input !pl-8" value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }} /></div>
            <div className="flex gap-2"><Select label="Classification filter" value={cls} onChange={(v) => { setCls(v); setPage(1) }} options={CLASSES} placeholder="All types" /><Select label="Status filter" value={ps} onChange={(v) => { setPs(v); setPage(1) }} options={STATUSES} placeholder="All statuses" /></div>
          </div>
          {list.isLoading ? <SkeletonRows /> : list.isError ? <ErrorBox error={list.error} retry={() => list.refetch()} /> : list.data!.items.length === 0 ? <Empty title="No emails" hint="Paste an email or load the demo emails to get started." /> : (
            <>
              <ul className="divide-y dark:divide-slate-800">{list.data!.items.map((m) => (
                <li key={String(m.id)}><button onClick={() => setSel(m.id)} className={`w-full rounded px-2 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800 ${sel === m.id ? 'bg-teal-50 dark:bg-teal-950/40' : ''}`}>
                  <div className="flex items-center justify-between gap-2"><span className={`truncate text-sm ${m.is_read ? '' : 'font-bold'}`}>{m.sender_name || m.sender_email}</span><span className="shrink-0 text-xs text-slate-500">{fmtDate(m.received_at)}</span></div>
                  <div className="truncate text-sm">{m.subject}</div>
                  <div className="mt-1 flex flex-wrap gap-1">{m.classification && <Badge color="blue">{label(m.classification)}</Badge>}<Badge color={m.processing_status === 'failed' ? 'red' : m.processing_status === 'processed' ? 'green' : 'gray'}>{m.processing_status}</Badge>{m.is_demo_ai && <DemoAIBadge />}</div>
                </button></li>))}</ul>
              <Pagination page={page} pageSize={20} total={list.data!.total} onPage={setPage} />
            </>
          )}
        </div>
        <div className="card min-h-[300px]">{sel == null ? <Empty title="Select an email" hint="Choose an email from the list to view its details and reply draft." /> : <EmailDetail key={String(sel)} id={sel} integ={integ.data} />}</div>
      </div>
      {paste && <ImportDialog onClose={() => setPaste(false)} onDone={(e) => setSel(e.id)} />}
    </div>
  )
}
