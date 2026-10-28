# EstatePilot AI - Power BI Guide

**Honest status.** No `.pbix` file was created. Nothing in this guide was opened in Power BI Desktop or the Power BI Service. The SQL views are verified (they are created and queried against the real schema by the automated test `test_powerbi_views_valid_in_sqlite`). The DAX measures are written but never executed. Embedding is implemented as a configuration endpoint plus an iframe and has never displayed a real report.

## 1. What is provided

| Item | Path | Verified |
|---|---|---|
| Star-schema SQL views (7) | `powerbi/sql/views.sql` | SQLite: yes (test). PostgreSQL: translation notes only |
| DAX measures (13) | `powerbi/dax_measures.dax` | No |
| Data dictionary | `powerbi/data_dictionary.md` | Reference |
| CSV exports | `GET /api/v1/analytics/export/{leads,emails,tasks,properties,fact_leads}.csv` | Endpoint implemented |
| Embed config endpoint | `GET /api/v1/analytics/powerbi` | Returns `configured:false` when unset (observed) |
| UI iframe | Analytics page | Renders only when configured |

## 2. Views

`dim_date` (2024-01-01 to 2030-12-31), `dim_lead`, `dim_property`, `dim_agent`, `fact_leads` (grain: lead), `fact_emails` (grain: email, no bodies), `fact_tasks` (grain: task). Every fact has `organization_id`; `is_demo` flags mark seeded data. Columns: `powerbi/data_dictionary.md`.

Load into SQLite for a quick local test:

```
sqlite3 backend/estatepilot.db < powerbi/sql/views.sql
```

For PostgreSQL, adapt the dialect-specific functions as documented in the header comment of `views.sql` (`date('now')` -> `CURRENT_DATE`, `strftime` -> `to_char`/`EXTRACT`, `julianday` differences -> `EXTRACT(EPOCH ...)`), run it, and use a read-only database role. This path has not been executed.

## 3. Manual steps in Power BI Desktop

1. Get Data: PostgreSQL (or ODBC for SQLite, or Text/CSV for the exports). Import mode is fine for this size.
2. Select the seven views.
3. Model view relationships (many-to-one, single direction from dimension to fact):

| Many side | One side |
|---|---|
| fact_leads[created_date_key] | dim_date[date_key] |
| fact_leads[lead_id] | dim_lead[lead_id] |
| fact_leads[agent_id] | dim_agent[agent_id] |
| fact_emails[received_date_key] | dim_date[date_key] |
| fact_emails[lead_id] | dim_lead[lead_id] |
| fact_tasks[due_date_key] | dim_date[date_key] (active); created_date_key inactive, use USERELATIONSHIP |
| fact_tasks[lead_id] | dim_lead[lead_id] |
| fact_tasks[agent_id] | dim_agent[agent_id] |

4. Mark `dim_date[date]` as the date table; sort `month_name` by `month_number`; hide key columns and `organization_id`.
5. Create a blank table `_Measures` and paste each measure from `dax_measures.dax` (New measure).
6. Build pages (suggested in `powerbi/README.md`): Executive overview, Lead funnel and sources, Email AI performance, Follow-ups and agents, Inventory. Add slicers for date, agent, source, priority and `is_demo` (default to 0 for real reporting).
7. Save as `.pbix`, then Publish to a workspace.

## 4. DAX measures

Total Leads, New Leads, Qualified Leads, Hot Leads, Total Emails Processed, Average First Response Minutes, Leads Converted, Lead Conversion Rate, Follow-up Completion Rate, Pipeline Value, Won Deal Value, Leads Previous Month, MoM Lead Growth. Definitions are in `powerbi/dax_measures.dax`. Validate each against a known count from the application (for example Total Leads versus `GET /dashboard/metrics`).

## 5. Refresh and security

Service: set data source credentials; on-premises or local databases need a data gateway; schedule refresh. `fact_tasks.is_overdue` is computed when the view is queried. For multi-tenant use apply row-level security on `organization_id` and publish only the views, never base tables. Views exclude password hashes and email bodies.

## 6. Embedding in EstatePilot

Set in `backend/.env`:

```
POWERBI_EMBED_URL=<embed url>
POWERBI_REPORT_ID=<report id>
POWERBI_EMBED_ENABLED=true
```

Restart the backend. `GET /analytics/powerbi` then returns `{configured: true, embed_url, report_id}`; the Analytics page shows the report in an iframe. The backend never issues embed tokens. Options: a Power BI secure embed link (internal), or "app owns data" with an Azure AD service principal and a separate token service (not implemented). `POWERBI_WORKSPACE_ID` is accepted in configuration but unused.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| Panel says "not configured" | all three variables must be set, `POWERBI_EMBED_ENABLED=true` |
| Iframe blank or refused | embed URL not frameable or tenant policy; use a secure embed link |
| Cannot connect to SQLite | install an SQLite ODBC driver or use CSV exports |
| Date relationships ambiguous in tasks | keep `due_date_key` active, use `USERELATIONSHIP` for created date |
| Demo data inflates charts | filter `is_demo = 0` |
