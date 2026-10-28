-- EstatePilot AI: Power BI star-schema views (SQLite dialect; tested against the real schema).
-- PostgreSQL: replace date('now') with CURRENT_DATE, date(x,'+1 day') with (x + 1), julianday diffs with
-- EXTRACT(EPOCH FROM (a-b))/60, strftime() with to_char()/EXTRACT(), and the BOOLEAN literals (1/0) as needed.
-- All timestamps are stored in UTC. Every fact carries organization_id: filter / RLS on it in Power BI.

DROP VIEW IF EXISTS fact_tasks;
DROP VIEW IF EXISTS fact_emails;
DROP VIEW IF EXISTS fact_leads;
DROP VIEW IF EXISTS dim_agent;
DROP VIEW IF EXISTS dim_property;
DROP VIEW IF EXISTS dim_lead;
DROP VIEW IF EXISTS dim_date;

CREATE VIEW dim_date AS
WITH RECURSIVE d(dt) AS (
  SELECT date('2024-01-01')
  UNION ALL
  SELECT date(dt, '+1 day') FROM d WHERE dt < date('2030-12-31')
)
SELECT
  CAST(strftime('%Y%m%d', dt) AS INTEGER)            AS date_key,
  dt                                                 AS date,
  CAST(strftime('%Y', dt) AS INTEGER)                AS year,
  CAST(strftime('%m', dt) AS INTEGER)                AS month_number,
  CASE strftime('%m', dt) WHEN '01' THEN 'Jan' WHEN '02' THEN 'Feb' WHEN '03' THEN 'Mar' WHEN '04' THEN 'Apr'
    WHEN '05' THEN 'May' WHEN '06' THEN 'Jun' WHEN '07' THEN 'Jul' WHEN '08' THEN 'Aug' WHEN '09' THEN 'Sep'
    WHEN '10' THEN 'Oct' WHEN '11' THEN 'Nov' ELSE 'Dec' END AS month_name,
  strftime('%Y-%m', dt)                              AS year_month,
  (CAST(strftime('%m', dt) AS INTEGER) + 2) / 3      AS quarter,
  CAST(strftime('%w', dt) AS INTEGER)                AS day_of_week,   -- 0 = Sunday
  CASE WHEN strftime('%w', dt) IN ('0','6') THEN 1 ELSE 0 END AS is_weekend
FROM d;

CREATE VIEW dim_lead AS
SELECT id AS lead_id, organization_id, full_name, email, phone, status, priority, source,
       preferred_location, property_type, bedrooms, transaction_type, timeline,
       is_archived, is_demo, assigned_agent_id AS agent_id
FROM leads;

CREATE VIEW dim_property AS
SELECT id AS property_id, organization_id, title, property_type, listing_type, location, city, bedrooms,
       bathrooms, area_sqft, price, units_available, status, is_demo, agent_id
FROM properties;

CREATE VIEW dim_agent AS
SELECT id AS agent_id, organization_id, full_name, email, role, is_active
FROM users;

CREATE VIEW fact_leads AS
SELECT
  l.id                                                        AS lead_id,
  l.organization_id,
  CAST(strftime('%Y%m%d', l.created_at) AS INTEGER)           AS created_date_key,
  l.assigned_agent_id                                         AS agent_id,
  l.status, l.priority, l.source, l.score,
  l.budget_min, l.budget_max,
  COALESCE(l.budget_max, l.budget_min, 0)                     AS deal_value,
  CASE WHEN l.status NOT IN ('Won','Lost') AND l.is_archived = 0 THEN COALESCE(l.budget_max, l.budget_min, 0) ELSE 0 END AS pipeline_value,
  CASE WHEN l.status = 'Won' AND l.is_archived = 0 THEN COALESCE(l.budget_max, l.budget_min, 0) ELSE 0 END AS won_value,
  CASE WHEN l.status = 'New' THEN 1 ELSE 0 END                AS is_new,
  CASE WHEN l.status = 'Qualified' THEN 1 ELSE 0 END          AS is_qualified,
  CASE WHEN l.priority = 'hot' THEN 1 ELSE 0 END              AS is_hot,
  CASE WHEN l.status = 'Won' THEN 1 ELSE 0 END                AS is_converted,
  CASE WHEN l.status NOT IN ('Won','Lost') THEN 1 ELSE 0 END  AS is_open,
  l.is_archived, l.is_demo,
  (SELECT ROUND((julianday(MIN(COALESCE(dr.sent_at, dr.approved_at))) - julianday(MIN(e.received_at))) * 1440.0, 1)
     FROM emails e JOIN email_drafts dr ON dr.lead_id = e.lead_id AND dr.status IN ('approved','sent')
    WHERE e.lead_id = l.id)                                   AS first_response_minutes
FROM leads l;

CREATE VIEW fact_emails AS
SELECT
  e.id                                                        AS email_id,
  e.organization_id,
  CAST(strftime('%Y%m%d', e.received_at) AS INTEGER)          AS received_date_key,
  e.lead_id, e.source, e.classification, e.processing_status, e.priority,
  CASE WHEN e.processing_status = 'processed' THEN 1 ELSE 0 END AS is_processed,
  CASE WHEN e.processing_status = 'failed' THEN 1 ELSE 0 END    AS is_failed,
  CASE WHEN e.is_read = 0 THEN 1 ELSE 0 END                   AS is_unread,
  e.is_demo_ai, e.is_demo
FROM emails e;

CREATE VIEW fact_tasks AS
SELECT
  t.id                                                        AS task_id,
  t.organization_id,
  t.lead_id,
  t.owner_id                                                  AS agent_id,
  CAST(strftime('%Y%m%d', t.due_at) AS INTEGER)               AS due_date_key,
  CAST(strftime('%Y%m%d', t.created_at) AS INTEGER)           AS created_date_key,
  t.status, t.priority, t.source,
  CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END          AS is_completed,
  CASE WHEN t.status = 'pending' THEN 1 ELSE 0 END            AS is_pending,
  CASE WHEN t.status = 'pending' AND t.due_at < datetime('now') THEN 1 ELSE 0 END AS is_overdue,
  t.is_demo
FROM tasks t;
