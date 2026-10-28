import { isEmail } from './format'
export type Errors<T extends string = string> = Partial<Record<T, string>>
export interface LeadForm { full_name: string; email: string; phone: string; budget_min: string; budget_max: string; bedrooms: string }
export function validateLead(f: LeadForm): Errors<keyof LeadForm> {
  const e: Errors<keyof LeadForm> = {}
  if (!f.full_name.trim()) e.full_name = 'Name is required'
  if (f.email && !isEmail(f.email)) e.email = 'Enter a valid email'
  if (f.phone && !/^[+\d][\d\s\-()]{6,}$/.test(f.phone)) e.phone = 'Enter a valid phone number'
  const min = f.budget_min === '' ? null : Number(f.budget_min)
  const max = f.budget_max === '' ? null : Number(f.budget_max)
  if (min != null && (isNaN(min) || min < 0)) e.budget_min = 'Must be a positive number'
  if (max != null && (isNaN(max) || max < 0)) e.budget_max = 'Must be a positive number'
  if (min != null && max != null && !e.budget_min && !e.budget_max && min > max) e.budget_max = 'Max must be at least min'
  if (f.bedrooms !== '' && (!Number.isInteger(Number(f.bedrooms)) || Number(f.bedrooms) < 0)) e.bedrooms = 'Whole number required'
  return e
}
