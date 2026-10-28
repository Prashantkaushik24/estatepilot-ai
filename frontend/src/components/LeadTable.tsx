import { ArrowDown, ArrowUp } from 'lucide-react'
import type { Lead } from '../types'
import { Badge, DemoBadge, Empty, PriorityBadge } from './ui'
import { fmtDay, inrShort } from '../lib/format'

export function LeadTable({ leads, sort, onSort, onOpen }: { leads: Lead[]; sort: string; onSort: (s: string) => void; onOpen: (l: Lead) => void }) {
  if (leads.length === 0) return <Empty title="No leads found" hint="Adjust the filters, add a lead, or import an email in the Inbox." />
  const col = (key: string, text: string) => {
    const active = sort === key || sort === `-${key}`
    return (
      <th className="th" aria-sort={active ? (sort.startsWith('-') ? 'descending' : 'ascending') : 'none'}>
        <button className="inline-flex items-center gap-1 uppercase" onClick={() => onSort(sort === key ? `-${key}` : key)}>
          {text}{active && (sort.startsWith('-') ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
        </button>
      </th>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="border-b dark:border-slate-800"><tr>{col('full_name', 'Name')}{col('status', 'Status')}{col('priority', 'Priority')}{col('score', 'Score')}<th className="th">Budget</th><th className="th">Location</th><th className="th">Source</th>{col('next_follow_up_at', 'Follow-up')}</tr></thead>
        <tbody className="divide-y dark:divide-slate-800">
          {leads.map((l) => (
            <tr key={String(l.id)} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50" onClick={() => onOpen(l)}>
              <td className="td font-medium"><button className="text-left hover:underline" onClick={(e) => { e.stopPropagation(); onOpen(l) }}>{l.full_name}</button>{l.is_archived && <> <Badge>archived</Badge></>}{l.is_demo && <> <DemoBadge /></>}</td>
              <td className="td"><Badge color="teal">{l.status}</Badge></td>
              <td className="td"><PriorityBadge p={l.priority} /></td>
              <td className="td">{l.score}</td>
              <td className="td">{l.budget_min == null && l.budget_max == null ? '—' : `${inrShort(l.budget_min)} – ${inrShort(l.budget_max)}`}</td>
              <td className="td">{l.preferred_location || '—'}</td>
              <td className="td">{l.source}</td>
              <td className="td">{fmtDay(l.next_follow_up_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
