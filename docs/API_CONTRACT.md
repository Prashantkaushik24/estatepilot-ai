# API Contract (shared by backend + frontend agents)

Base: `http://localhost:8000/api/v1`. JSON. snake_case fields. All timestamps ISO-8601 UTC (timezone-aware, "Z").
Auth: `Authorization: Bearer <jwt>`. Errors: `{"detail": "..."}` with proper status (401/403/404/409/422/429).
List endpoints return `{"items":[...],"total":int,"page":int,"page_size":int}` and accept `page`(1), `page_size`(20, max 200), `q`, `sort` (e.g. `-created_at`).
All data scoped to the user's organization. Roles: admin > manager > agent > analyst(read-only: GET only; 403 on writes).

Seed (run `python -m app.db.seed`, idempotent; also auto on startup if DB empty and SEED_DEMO=true):
org "Demo Realty"; users (password `Passw0rd!demo`): admin@demo.com (admin), manager@demo.com, agent@demo.com, analyst@demo.com; ~8 fictional properties (Jaipur etc, labelled demo), a few leads/tasks. Seeded data is flagged `is_demo=true` where applicable.

## Health
GET /health -> {status:"ok", db:"ok", version, demo_mode:bool, time}   (no auth, also at /health)

## Auth
POST /auth/login {email,password} -> {access_token, token_type:"bearer", user}
GET /auth/me -> User
User = {id, email, full_name, role, organization_id, is_active}
GET /users (admin/manager) -> list of User; POST /users (admin) {email,full_name,password,role}; PATCH /users/{id} (admin) {role?,is_active?,full_name?}

## Leads
Lead = {id, full_name, email?, phone?, status, priority("low"|"medium"|"high"|"hot"), score:int(0-100), score_reasons:[{factor,points,detail}], source("email"|"manual"|"web"|"referral"|"gmail"|"demo"),
 preferred_location?, property_type?, bedrooms?, budget_min?, budget_max?, timeline?, amenities:[str], intent?, transaction_type?("buy"|"rent"|"sell"),
 assigned_agent_id?, assigned_agent_name?, tags:[str], notes?, next_follow_up_at?, is_archived:bool, is_demo:bool, created_at, updated_at}
status ∈ New|Contacted|Qualified|Viewing Scheduled|Negotiation|Won|Lost
GET /leads?q&status&priority&source&include_archived&sort&page&page_size
POST /leads (agent+) ; GET /leads/{id} ; PATCH /leads/{id} ; POST /leads/{id}/archive ; POST /leads/{id}/restore
GET /leads/{id}/activity -> [{id, type, message, created_at, actor?}]   (timeline from audit logs)
GET /leads/export.csv -> text/csv
POST /leads/{id}/rescore -> Lead

## Properties
Property = {id, title, property_type("apartment"|"villa"|"house"|"plot"|"commercial"), listing_type("sale"|"rent"), price, location, city?, bedrooms?, bathrooms?, area_sqft?, units_available:int, amenities:[str], status("available"|"reserved"|"sold"|"rented"), description?, url?, agent_id?, is_demo, created_at, updated_at}
GET /properties?q&status&property_type&location&sort&page&page_size ; POST ; GET /{id} ; PATCH /{id} ; DELETE /{id} (manager+)
GET /leads/{id}/matches -> [PropertyMatch]  (computes+stores)
PropertyMatch = {id?, lead_id, property:Property, score:int(0-100), criteria:[{name:"location"|"budget"|"bedrooms"|"property_type"|"amenities"|"availability", matched:bool, points:int, max_points:int, detail:str}], explanation:str}
POST /matches/search {location?,budget_min?,budget_max?,bedrooms?,property_type?,amenities?[]} -> [PropertyMatch] (ad-hoc, not stored)

## Tasks (follow-ups)
Task = {id, title, description?, lead_id?, lead_name?, owner_id?, owner_name?, priority, status("pending"|"completed"|"cancelled"), due_at, reminder_at?, completed_at?, is_overdue:bool, source("manual"|"ai"), created_at}
GET /tasks?status&lead_id&overdue(bool)&owner_id&page&page_size ; POST ; GET /{id} ; PATCH /{id} ; POST /{id}/complete ; DELETE /{id}
GET /tasks/reminders -> tasks due/reminder-time passed & pending

## Emails
Email = {id, thread_id?, external_id?, sender_name?, sender_email, recipient_email?, subject, body, received_at, source("paste"|"demo"|"gmail"), is_read, classification?(one of: property_inquiry, buying_request, selling_request, rental_inquiry, property_listing_submission, site_visit_request, pricing_inquiry, follow_up, complaint, spam, other), processing_status("pending"|"processing"|"processed"|"failed"|"skipped"), priority?, lead_id?, lead_name?, summary?, extraction?:Extraction, draft?:Draft, is_demo_ai:bool, error?, created_at}
Extraction = {customer_name?, sender_email?, phone?, intent?, preferred_location?, property_type?, bedrooms?:int, budget_min?:number, budget_max?:number, transaction_type?("buy"|"rent"|"sell"), timeline?, amenities:[str], urgency?("low"|"medium"|"high"), missing_information:[str]}   (budgets in INR rupees; "80 lakh"=8000000)
Draft = {id, email_id, lead_id?, subject, body, status("draft"|"approved"|"sent"|"failed"|"discarded"), approved_by?, approved_at?, sent_at?, provider_message_id?, is_demo_ai, created_at, updated_at}
GET /emails?q&classification&processing_status&lead_id&priority&page&page_size ; GET /emails/{id}
POST /emails/import {sender_email, sender_name?, subject, body, received_at?, process:bool=true, source:"paste"} -> ProcessResult (409 if duplicate content hash for org — response detail "duplicate", includes existing email id in `existing_email_id`)
POST /emails/demo -> imports 3 canned demo emails (idempotent) -> {created:int, emails:[Email]}
POST /emails/{id}/process -> ProcessResult (safe retry; reprocess allowed for failed)
ProcessResult = {email:Email, lead?:Lead, lead_created:bool, matches:[PropertyMatch], draft?:Draft, task?:Task, run:AIRun, steps:[{name,status("ok"|"skipped"|"failed"),detail}]}
PATCH /emails/{id} {is_read?}
Drafts: GET /emails/{id}/draft ; PUT /emails/{id}/draft {subject,body} (save/edit) ; POST /emails/{id}/draft/regenerate
POST /drafts/{id}/approve (manager+/agent) -> Draft status approved
POST /drafts/{id}/send {confirm:true, confirm_recipient:str} -> sends only if: draft approved, global kill switch off, SENDING_ENABLED=true, Gmail connected; otherwise 409/403 with clear detail. Duplicate send -> 409. Never marks sent without provider confirmation.

## Automation
Rule = {id, key("process_incoming_emails"|"create_update_leads"|"create_followup_tasks"|"generate_reply_drafts"), name, description, enabled:bool, last_run_at?, last_result?, run_count:int}
GET /automation/rules ; PATCH /automation/rules/{id} {enabled} (manager+)
GET /automation/state -> {paused:bool, kill_switch:bool, sending_enabled:bool}
POST /automation/pause ; POST /automation/resume ; POST /automation/kill-switch {enabled:bool} (admin)
GET /automation/runs -> list[AIRun]
AIRun = {id, email_id?, status("success"|"failed"|"partial"), provider("demo"|"openai"|"gemini"), model?, is_demo:bool, attempts:int, error?, duration_ms, steps:[...], created_at}
When paused or kill switch on: import still stores email as `pending`, processing returns 409 "automation paused".
Rules disabled: respective pipeline step is skipped (step status "skipped").

## Audit
AuditLog = {id, action, entity_type?, entity_id?, message, level("info"|"warning"|"error"), actor_id?, metadata:{}, created_at}
GET /audit?action&entity_type&level&page&page_size  (no secrets/tokens/full email bodies)

## Dashboard / Analytics
GET /dashboard/metrics -> {total_leads,new_leads,qualified_leads,hot_leads,emails_processed,unread_emails,pending_followups,overdue_tasks,avg_first_response_minutes:number|null,conversion_rate:number(0-1),pipeline_value:number,won_value:number, data_source:"database", has_demo_data:bool}
GET /analytics/charts -> {leads_over_time:[{date,count}], leads_by_source:[{name,value}], lead_status:[{name,value}], email_intent:[{name,value}], demand_by_location:[{name,value}], budget_distribution:[{name,value}], followup_status:[{name,value}], funnel:[{name,value}]}
GET /analytics/export/{leads|emails|tasks|properties|fact_leads}.csv
GET /analytics/powerbi -> {configured:bool, embed_url?, report_id?, message}  (never tokens; embed token only via server env flag)
Pipeline value = sum(budget_max or budget_min) of open leads (not Won/Lost/archived); won_value same for Won.

## Integrations
GET /integrations/status -> {backend:"ok", ai:{provider, configured:bool, demo_mode:bool, model?}, gmail:{configured:bool, connected:bool, account_email?, last_sync_at?}, powerbi:{configured:bool}, sending_enabled:bool, kill_switch:bool, paused:bool}
GET /integrations/gmail/auth-url -> {url} (501-style 400 w/ detail "Gmail OAuth not configured" if no client id)
GET /integrations/gmail/callback?code&state (validates state) -> redirects to FRONTEND_URL/settings?gmail=connected|error
POST /integrations/gmail/sync -> {imported:int, skipped_duplicates:int} ; POST /integrations/gmail/disconnect
GET/PATCH /settings -> {demo_mode, sending_enabled(read-only here, env-controlled), default_agent_id?, timezone, theme?}  (PATCH admin/manager: demo_mode? only)

## Notifications
GET /notifications ; POST /notifications/{id}/read
