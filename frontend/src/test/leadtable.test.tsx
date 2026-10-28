import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { LeadTable } from '../components/LeadTable'
import type { Lead } from '../types'
import { sendBlockReason } from '../pages/Inbox'

const lead = { id: 1, full_name: 'Asha Rao', status: 'New', priority: 'hot', score: 88, score_reasons: [], source: 'email', amenities: [], tags: [], is_archived: false, is_demo: true, created_at: '', updated_at: '', budget_max: 8000000 } as Lead
describe('LeadTable', () => {
  it('renders rows and opens a lead', () => {
    const open = vi.fn(); render(<LeadTable leads={[lead]} sort="-created_at" onSort={() => {}} onOpen={open} />)
    expect(screen.getByText('Asha Rao')).toBeInTheDocument(); expect(screen.getByText('88')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Asha Rao')); expect(open).toHaveBeenCalledWith(lead)
  })
  it('shows empty state', () => { render(<LeadTable leads={[]} sort="" onSort={() => {}} onOpen={() => {}} />); expect(screen.getByText('No leads found')).toBeInTheDocument() })
})
describe('sendBlockReason', () => {
  const integ: any = { kill_switch: false, sending_enabled: true, gmail: { connected: true } }
  const d: any = { status: 'approved' }
  it('allows when everything is ready', () => expect(sendBlockReason(d, integ)).toBeNull())
  it('blocks unapproved, disabled, and kill switch', () => {
    expect(sendBlockReason({ status: 'draft' } as any, integ)).toMatch(/Approve/)
    expect(sendBlockReason(d, { ...integ, sending_enabled: false })).toMatch(/disabled/)
    expect(sendBlockReason(d, { ...integ, kill_switch: true })).toMatch(/Kill/)
  })
})
