# EstatePilot AI - Power BI assets

**No PBIX file was created and nothing here was opened in Power BI Desktop/Service.** The SQL views were tested against the real
schema in SQLite; the DAX is unexecuted and should be validated in Desktop. Embedding is unverified.

## Contents
- `sql/views.sql` - star-schema views: `dim_date, dim_lead, dim_property, dim_agent, fact_leads, fact_emails, fact_tasks`
- `dax_measures.dax` - 12 measures (Total Leads ... MoM Lead Growth)
- `data_dictionary.md` - columns and grain

## Connect
1. Production: use PostgreSQL (`DATABASE_URL`), run `alembic upgrade head`, then adapt `views.sql` per the dialect notes in its header and run it (or have a DBA do so). Create a read-only DB role limited to the views.
2. Power BI Desktop: Get Data -> PostgreSQL (Import mode; DirectQuery optional). For quick demos without a DB, use the CSV exports
   `GET /api/v1/analytics/export/{leads|emails|tasks|properties|fact_leads}.csv` (authenticated).
3. For SQLite demo: apply the file with `sqlite3 backend/estatepilot.db < powerbi/sql/views.sql` and use an SQLite ODBC driver.

## Data model (relationships, all many-to-one, single direction from dim to fact)
| From (many) | To (one) |
|---|---|
| fact_leads[created_date_key] | dim_date[date_key] |
| fact_leads[lead_id] | dim_lead[lead_id] (1:1; or use dim_lead only for slicers) |
| fact_leads[agent_id] | dim_agent[agent_id] |
| fact_emails[received_date_key] | dim_date[date_key] |
| fact_emails[lead_id] | dim_lead[lead_id] |
| fact_tasks[due_date_key] | dim_date[date_key] (set created_date_key as inactive relationship; USERELATIONSHIP when needed) |
| fact_tasks[lead_id] | dim_lead[lead_id] |
| fact_tasks[agent_id] | dim_agent[agent_id] |
Mark `dim_date[date]` as the date table. Hide `*_key` columns and `organization_id` from report view. Sort `month_name` by `month_number`.
`dim_property` is standalone (use for inventory pages). Import `dax_measures.dax` measures into a `_Measures` table.

## Suggested report layout
1. **Executive overview**: cards (Total Leads, Hot Leads, Lead Conversion Rate, Pipeline Value, Won Deal Value, Avg First Response Minutes), line chart Total Leads by month with MoM Lead Growth, donut Lead status.
2. **Lead funnel & sources**: funnel by status, bar by source, bar of demand by preferred_location, budget distribution histogram.
3. **Email AI performance**: Total Emails Processed, stacked column by classification, processing_status breakdown, is_demo_ai slicer.
4. **Follow-ups & agents**: Follow-up Completion Rate, overdue task count, table by agent (leads, converted, response time).
5. **Inventory**: dim_property by status/type/city, price histogram.
Slicers: date, agent, source, priority, is_demo (default to is_demo = 0 in production).

## Refresh
Desktop: Home -> Refresh. Service: configure the gateway (on-prem DB) or direct cloud credentials, then scheduled refresh (e.g. 8x/day). `fact_tasks.is_overdue` is evaluated at refresh time.

## Publish
Desktop: Home -> Publish -> choose workspace. In the Service set dataset credentials and (optional) row-level security on `organization_id` (DAX filter `[organization_id] = "<org uuid>"` mapped per role).

## Embed in EstatePilot
The backend only exposes configuration flags: `GET /api/v1/analytics/powerbi` returns `{configured, embed_url, report_id}` when `POWERBI_EMBED_URL`, `POWERBI_REPORT_ID` and `POWERBI_EMBED_ENABLED=true` are set. It never returns tokens.
- Quick/internal: use a Power BI "Publish to web"/secure embed URL for `POWERBI_EMBED_URL` and render it in an iframe in the frontend.
- App-owns-data: issue embed tokens from a separate secure service using an Azure AD service principal (`POWERBI_*` secrets stay server-side); not implemented in this repo.
