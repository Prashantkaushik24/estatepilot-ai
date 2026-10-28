import { CheckCircle2, XCircle } from 'lucide-react'
import type { PropertyMatch } from '../types'
import { inr, label } from '../lib/format'
import { Badge } from './ui'

export function MatchCard({ m }: { m: PropertyMatch }) {
  return (
    <article className="card">
      <div className="flex items-start justify-between gap-2">
        <div><h3 className="font-semibold">{m.property.title}</h3><p className="text-sm text-slate-500">{m.property.location} · {inr(m.property.price)} · {m.property.bedrooms ?? '—'} BHK</p></div>
        <Badge color={m.score >= 70 ? 'green' : m.score >= 40 ? 'amber' : 'gray'}>{m.score}% match</Badge>
      </div>
      <p className="mt-2 text-sm">{m.explanation}</p>
      <ul className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
        {m.criteria.map((c) => (
          <li key={c.name} className="flex items-start gap-1" title={c.detail}>
            {c.matched ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-label="matched" /> : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" aria-label="not matched" />}
            <span><b>{label(c.name)}</b> {c.points}/{c.max_points} — {c.detail}</span>
          </li>
        ))}
      </ul>
    </article>
  )
}
