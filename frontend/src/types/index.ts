export type Role = 'admin' | 'manager' | 'agent' | 'analyst'
export interface User { id: string | number; email: string; full_name: string; role: Role; organization_id: string | number; is_active: boolean }
export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number }
export type Id = string | number

export type LeadStatus = 'New' | 'Contacted' | 'Qualified' | 'Viewing Scheduled' | 'Negotiation' | 'Won' | 'Lost'
export const LEAD_STATUSES: LeadStatus[] = ['New', 'Contacted', 'Qualified', 'Viewing Scheduled', 'Negotiation', 'Won', 'Lost']
export type Priority = 'low' | 'medium' | 'high' | 'hot'
export type LeadSource = 'email' | 'manual' | 'web' | 'referral' | 'gmail' | 'demo'
export type TransactionType = 'buy' | 'rent' | 'sell'
export interface ScoreReason { factor: string; points: number; detail: string }
export interface Lead {
  id: Id; full_name: string; email?: string | null; phone?: string | null; status: LeadStatus; priority: Priority
  score: number; score_reasons: ScoreReason[]; source: LeadSource
  preferred_location?: string | null; property_type?: string | null; bedrooms?: number | null
  budget_min?: number | null; budget_max?: number | null; timeline?: string | null; amenities: string[]
  intent?: string | null; transaction_type?: TransactionType | null
  assigned_agent_id?: Id | null; assigned_agent_name?: string | null; tags: string[]; notes?: string | null
  next_follow_up_at?: string | null; is_archived: boolean; is_demo: boolean; created_at: string; updated_at: string
}
export interface ActivityItem { id: Id; type: string; message: string; created_at: string; actor?: string | null }

export type PropertyType = 'apartment' | 'villa' | 'house' | 'plot' | 'commercial'
export type PropertyStatus = 'available' | 'reserved' | 'sold' | 'rented'
export interface Property {
  id: Id; title: string; property_type: PropertyType; listing_type: 'sale' | 'rent'; price: number; location: string
  city?: string | null; bedrooms?: number | null; bathrooms?: number | null; area_sqft?: number | null
  units_available: number; amenities: string[]; status: PropertyStatus; description?: string | null; url?: string | null
  agent_id?: Id | null; is_demo: boolean; created_at: string; updated_at: string
}
export interface MatchCriterion { name: 'location' | 'budget' | 'bedrooms' | 'property_type' | 'amenities' | 'availability'; matched: boolean; points: number; max_points: number; detail: string }
export interface PropertyMatch { id?: Id; lead_id: Id; property: Property; score: number; criteria: MatchCriterion[]; explanation: string }
export interface MatchSearch { location?: string; budget_min?: number; budget_max?: number; bedrooms?: number; property_type?: string; amenities?: string[] }

export interface Task {
  id: Id; title: string; description?: string | null; lead_id?: Id | null; lead_name?: string | null
  owner_id?: Id | null; owner_name?: string | null; priority: Priority; status: 'pending' | 'completed' | 'cancelled'
  due_at: string; reminder_at?: string | null; completed_at?: string | null; is_overdue: boolean; source: 'manual' | 'ai'; created_at: string
}

export type Classification = 'property_inquiry' | 'buying_request' | 'selling_request' | 'rental_inquiry' | 'property_listing_submission' | 'site_visit_request' | 'pricing_inquiry' | 'follow_up' | 'complaint' | 'spam' | 'other'
export interface Extraction {
  customer_name?: string | null; sender_email?: string | null; phone?: string | null; intent?: string | null
  preferred_location?: string | null; property_type?: string | null; bedrooms?: number | null
  budget_min?: number | null; budget_max?: number | null; transaction_type?: TransactionType | null
  timeline?: string | null; amenities: string[]; urgency?: 'low' | 'medium' | 'high' | null; missing_information: string[]
}
export interface Draft {
  id: Id; email_id: Id; lead_id?: Id | null; subject: string; body: string
  status: 'draft' | 'approved' | 'sent' | 'failed' | 'discarded'
  approved_by?: Id | null; approved_at?: string | null; sent_at?: string | null; provider_message_id?: string | null
  is_demo_ai: boolean; created_at: string; updated_at: string
}
export type ProcessingStatus = 'pending' | 'processing' | 'processed' | 'failed' | 'skipped'
export interface Email {
  id: Id; thread_id?: string | null; external_id?: string | null; sender_name?: string | null; sender_email: string
  recipient_email?: string | null; subject: string; body: string; received_at: string; source: 'paste' | 'demo' | 'gmail'
  is_read: boolean; classification?: Classification | null; processing_status: ProcessingStatus; priority?: Priority | null
  lead_id?: Id | null; lead_name?: string | null; summary?: string | null; extraction?: Extraction | null
  draft?: Draft | null; is_demo_ai: boolean; error?: string | null; created_at: string
}
export interface StepResult { name: string; status: 'ok' | 'skipped' | 'failed'; detail?: string | null }
export interface AIRun {
  id: Id; email_id?: Id | null; status: 'success' | 'failed' | 'partial'; provider: 'demo' | 'openai' | 'gemini'; model?: string | null
  is_demo: boolean; attempts: number; error?: string | null; duration_ms: number; steps: StepResult[]; created_at: string
}
export interface ProcessResult { email: Email; lead?: Lead | null; lead_created: boolean; matches: PropertyMatch[]; draft?: Draft | null; task?: Task | null; run: AIRun; steps: StepResult[] }
export interface EmailImport { sender_email: string; sender_name?: string; subject: string; body: string; received_at?: string; process: boolean; source: 'paste' }

export interface Rule { id: Id; key: 'process_incoming_emails' | 'create_update_leads' | 'create_followup_tasks' | 'generate_reply_drafts'; name: string; description: string; enabled: boolean; last_run_at?: string | null; last_result?: string | null; run_count: number }
export interface AutomationState { paused: boolean; kill_switch: boolean; sending_enabled: boolean }
export interface AuditLog { id: Id; action: string; entity_type?: string | null; entity_id?: Id | null; message: string; level: 'info' | 'warning' | 'error'; actor_id?: Id | null; metadata: Record<string, unknown>; created_at: string }

export interface DashboardMetrics {
  total_leads: number; new_leads: number; qualified_leads: number; hot_leads: number; emails_processed: number; unread_emails: number
  pending_followups: number; overdue_tasks: number; avg_first_response_minutes: number | null; conversion_rate: number
  pipeline_value: number; won_value: number; data_source: 'database'; has_demo_data: boolean
}
export interface NameValue { name: string; value: number }
export interface Charts {
  leads_over_time: { date: string; count: number }[]; leads_by_source: NameValue[]; lead_status: NameValue[]; email_intent: NameValue[]
  demand_by_location: NameValue[]; budget_distribution: NameValue[]; followup_status: NameValue[]; funnel: NameValue[]
}
export interface PowerBI { configured: boolean; embed_url?: string | null; report_id?: string | null; message: string }
export interface IntegrationStatus {
  backend: 'ok'; ai: { provider: string; configured: boolean; demo_mode: boolean; model?: string | null }
  gmail: { configured: boolean; connected: boolean; account_email?: string | null; last_sync_at?: string | null }
  powerbi: { configured: boolean }; sending_enabled: boolean; kill_switch: boolean; paused: boolean
}
export interface AppSettings { demo_mode: boolean; sending_enabled: boolean; default_agent_id?: Id | null; timezone: string; theme?: string | null }
export interface Health { status: 'ok'; db: string; version: string; demo_mode: boolean; time: string }
export interface Notification { id: Id; [k: string]: unknown }
