import { describe, expect, it } from 'vitest'
import { validateLead } from '../lib/validation'
const base = { full_name: 'A', email: '', phone: '', budget_min: '', budget_max: '', bedrooms: '' }
describe('validateLead', () => {
  it('accepts a minimal lead', () => expect(validateLead(base)).toEqual({}))
  it('requires name', () => expect(validateLead({ ...base, full_name: ' ' }).full_name).toBeTruthy())
  it('validates email and budget order', () => {
    const e = validateLead({ ...base, email: 'bad', budget_min: '10', budget_max: '5' })
    expect(e.email).toBeTruthy(); expect(e.budget_max).toBeTruthy()
  })
})
