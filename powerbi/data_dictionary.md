# Power BI Data Dictionary

Source: SQL views in `powerbi/sql/views.sql` (SQLite dialect; PostgreSQL notes at the top of the file). All timestamps UTC.
Every row carries `organization_id`; filter or apply RLS on it. `is_demo*` flags mark seeded/demo data (exclude in production reports).

## dim_date (2024-01-01 .. 2030-12-31)
| Column | Type | Description |
|---|---|---|
| date_key | int | YYYYMMDD, PK |
| date | text/date | ISO date |
| year, month_number, quarter | int | calendar parts |
| month_name, year_month | text | `Oct`, `2026-10` (sort month_name by month_number) |
| day_of_week | int | 0 = Sunday |
| is_weekend | 0/1 | |

## dim_lead
lead_id (PK), organization_id, full_name, email, phone, status (New/Contacted/Qualified/Viewing Scheduled/Negotiation/Won/Lost), priority (low/medium/high/hot), source, preferred_location, property_type, bedrooms, transaction_type (buy/rent/sell), timeline, is_archived, is_demo, agent_id (-> dim_agent).

## dim_property
property_id (PK), organization_id, title, property_type, listing_type (sale/rent), location, city, bedrooms, bathrooms, area_sqft, price (INR), units_available, status (available/reserved/sold/rented), is_demo, agent_id.

## dim_agent
agent_id (PK), organization_id, full_name, email, role (admin/manager/agent/analyst), is_active. (Passwords are never exposed.)

## fact_leads (grain: one row per lead)
| Column | Description |
|---|---|
| lead_id (FK dim_lead), agent_id (FK dim_agent), created_date_key (FK dim_date) | keys |
| status, priority, source, score | score is 0-100 deterministic (see backend scoring rules) |
| budget_min, budget_max, deal_value | INR; deal_value = budget_max else budget_min else 0 |
| pipeline_value | deal_value for open leads (not Won/Lost, not archived) else 0 |
| won_value | deal_value for Won, non-archived leads else 0 |
| is_new, is_qualified, is_hot, is_converted, is_open | 0/1 flags (is_qualified = status Qualified; is_hot = priority hot; is_converted = Won) |
| first_response_minutes | minutes from lead's first email to first approved/sent reply draft; NULL if none |
| is_archived, is_demo | flags |

## fact_emails (grain: one row per email)
email_id, organization_id, received_date_key, lead_id (FK dim_lead), source (paste/demo/gmail), classification (property_inquiry, buying_request, ...), processing_status (pending/processing/processed/failed/skipped), priority, is_processed, is_failed, is_unread, is_demo_ai, is_demo. Email bodies are intentionally NOT included.

## fact_tasks (grain: one row per follow-up task)
task_id, organization_id, lead_id, agent_id (owner), due_date_key, created_date_key, status (pending/completed/cancelled), priority, source (manual/ai), is_completed, is_pending, is_overdue (pending and due before now at refresh time), is_demo.
