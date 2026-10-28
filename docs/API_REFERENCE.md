# EstatePilot AI - API Reference

_Generated from the live OpenAPI schema (`EstatePilot AI API` v1.0.0) by `scripts/generate_api_reference.py`. Do not edit by hand; re-run the script._

Base URL: `http://localhost:8000` (versioned routes under `/api/v1`). Interactive docs: `/docs`. 62 operations.

Auth: `Authorization: Bearer <jwt>` from `POST /api/v1/auth/login`. Errors are `{"detail": "..."}` (401/403/404/409/422/429/502). All timestamps are ISO-8601 UTC (`...Z`).

Role hierarchy: `admin > manager > agent > analyst` (analyst is read-only). Minimum roles found in the code:

| Operation | Minimum role |
|---|---|
| Any GET (except `/health`, Gmail callback) | analyst (authenticated) |
| Create/edit leads, properties, tasks; import/process emails; edit/approve/send drafts; `POST /matches/search` | agent (`/matches/search` is non-mutating and is also allowed for analyst per backend README) |
| Delete property; list users; pause/resume automation; toggle rules; PATCH settings; Gmail sync | manager |
| Create/patch users; kill switch; Gmail auth-url / disconnect | admin |

## Examples

```bash
# 1. log in (demo seed user)
curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"agent@demo.com","password":"Passw0rd!demo"}'
# -> {"access_token":"...","token_type":"bearer","user":{...}}

# 2. import + process an email
TOKEN=<access_token>
curl -s -X POST http://localhost:8000/api/v1/emails/import -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sender_email":"neha@example.com","sender_name":"Neha","subject":"3 BHK in Jaipur","body":"Looking for a 3 BHK apartment in Jaipur under 80 lakh. Call 9876501234"}'
# -> {"email":{...,"classification":"buying_request","extraction":{...},"draft":{...}},"lead":{...},"lead_created":true,"matches":[...],"steps":[...],"run":{...}}

# 3. approve a draft (never sends)
curl -s -X POST http://localhost:8000/api/v1/drafts/<draft_id>/approve -H "Authorization: Bearer $TOKEN"

# 4. send (only if SENDING_ENABLED=true, Gmail connected, draft approved)
curl -s -X POST http://localhost:8000/api/v1/drafts/<draft_id>/send -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"confirm":true,"confirm_recipient":"neha@example.com"}'
```

Duplicate import returns `409 {"detail":"duplicate","existing_email_id":"..."}`. Bad login returns `401 {"detail":"Invalid email or password"}`; missing token returns `401 {"detail":"Not authenticated"}`.

## analytics

### `GET /api/v1/analytics/charts`

Charts

Responses: `200`

### `GET /api/v1/analytics/export/{kind}.csv`

Export

| Parameter | In | Type | Required |
|---|---|---|---|
| `kind` | path | string | yes |

Responses: `200`; `422` HTTPValidationError

### `GET /api/v1/analytics/powerbi`

Powerbi

Responses: `200`

### `GET /api/v1/dashboard/metrics`

Dash

Responses: `200`

## audit

### `GET /api/v1/audit`

Audit List

| Parameter | In | Type | Required |
|---|---|---|---|
| `action` | query | string | null | no |
| `entity_type` | query | string | null | no |
| `level` | query | string | null | no |
| `page` | query | integer | no |
| `page_size` | query | integer | no |
| `q` | query | string | null | no |
| `sort` | query | string | null | no |

Responses: `200` Page_AuditOut_; `422` HTTPValidationError

## auth

### `POST /api/v1/auth/login`

Login

Request body: `LoginIn`

Schema `LoginIn`:

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `password` | string | yes |

Responses: `200` LoginOut; `422` HTTPValidationError

### `GET /api/v1/auth/me`

Me

Responses: `200` UserOut

### `GET /api/v1/users`

List Users

Responses: `200` array[UserOut]

### `POST /api/v1/users`

Create User

Request body: `UserCreate`

Schema `UserCreate`:

| Field | Type | Required |
|---|---|---|
| `email` | string | yes |
| `full_name` | string | yes |
| `password` | string | yes |
| `role` | enum(admin, manager, agent, analyst) | yes |

Responses: `201` UserOut; `422` HTTPValidationError

### `PATCH /api/v1/users/{user_id}`

Patch User

| Parameter | In | Type | Required |
|---|---|---|---|
| `user_id` | path | string | yes |

Request body: `UserPatch`

Schema `UserPatch`:

| Field | Type | Required |
|---|---|---|
| `role` | enum(admin, manager, agent, analyst) | null | no |
| `is_active` | boolean | null | no |
| `full_name` | string | null | no |

Responses: `200` UserOut; `422` HTTPValidationError

## automation

### `POST /api/v1/automation/kill-switch`

Kill

Request body: `KillIn`

Schema `KillIn`:

| Field | Type | Required |
|---|---|---|
| `enabled` | boolean | yes |

Responses: `200`; `422` HTTPValidationError

### `POST /api/v1/automation/pause`

Pause

Responses: `200`

### `POST /api/v1/automation/resume`

Resume

Responses: `200`

### `GET /api/v1/automation/rules`

Rules

Responses: `200` array[RuleOut]

### `PATCH /api/v1/automation/rules/{rid}`

Patch Rule

| Parameter | In | Type | Required |
|---|---|---|---|
| `rid` | path | string | yes |

Request body: `RulePatch`

Schema `RulePatch`:

| Field | Type | Required |
|---|---|---|
| `enabled` | boolean | yes |

Responses: `200` RuleOut; `422` HTTPValidationError

### `GET /api/v1/automation/runs`

Runs

| Parameter | In | Type | Required |
|---|---|---|---|
| `limit` | query | integer | no |

Responses: `200` array[AIRunOut]; `422` HTTPValidationError

### `GET /api/v1/automation/state`

State

Responses: `200`

## emails

### `POST /api/v1/drafts/{did}/approve`

Approve

| Parameter | In | Type | Required |
|---|---|---|---|
| `did` | path | string | yes |

Responses: `200` DraftOut; `422` HTTPValidationError

### `POST /api/v1/drafts/{did}/send`

Send - Send only if: draft approved, kill switch off, SENDING_ENABLED, Gmail connected, explicit confirmation.

| Parameter | In | Type | Required |
|---|---|---|---|
| `did` | path | string | yes |

Request body: `SendIn`

Schema `SendIn`:

| Field | Type | Required |
|---|---|---|
| `confirm` | boolean | yes |
| `confirm_recipient` | string | yes |

Responses: `200` DraftOut; `422` HTTPValidationError

### `GET /api/v1/emails`

List Emails

| Parameter | In | Type | Required |
|---|---|---|---|
| `classification` | query | string | null | no |
| `processing_status` | query | string | null | no |
| `lead_id` | query | string | null | no |
| `priority` | query | string | null | no |
| `page` | query | integer | no |
| `page_size` | query | integer | no |
| `q` | query | string | null | no |
| `sort` | query | string | null | no |

Responses: `200` Page_EmailOut_; `422` HTTPValidationError

### `POST /api/v1/emails/demo`

Import Demo

Responses: `200`

### `POST /api/v1/emails/import`

Import Email

Request body: `EmailImport`

Schema `EmailImport`:

| Field | Type | Required |
|---|---|---|
| `sender_email` | string | yes |
| `sender_name` | string | null | no |
| `subject` | string | yes |
| `body` | string | yes |
| `received_at` | string | null | no |
| `process` | boolean | no |
| `source` | enum(paste, demo) | no |

Responses: `200` ProcessResult; `422` HTTPValidationError

### `GET /api/v1/emails/{eid}`

Get Email

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Responses: `200` EmailOut; `422` HTTPValidationError

### `PATCH /api/v1/emails/{eid}`

Patch Email

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Request body: `EmailPatch`

Schema `EmailPatch`:

| Field | Type | Required |
|---|---|---|
| `is_read` | boolean | null | no |

Responses: `200` EmailOut; `422` HTTPValidationError

### `GET /api/v1/emails/{eid}/draft`

Get Draft

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Responses: `200` DraftOut; `422` HTTPValidationError

### `PUT /api/v1/emails/{eid}/draft`

Put Draft

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Request body: `DraftIn`

Schema `DraftIn`:

| Field | Type | Required |
|---|---|---|
| `subject` | string | yes |
| `body` | string | yes |

Responses: `200` DraftOut; `422` HTTPValidationError

### `POST /api/v1/emails/{eid}/draft/regenerate`

Regenerate

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Responses: `200` DraftOut; `422` HTTPValidationError

### `POST /api/v1/emails/{eid}/process`

Process

| Parameter | In | Type | Required |
|---|---|---|---|
| `eid` | path | string | yes |

Responses: `200` ProcessResult; `422` HTTPValidationError

## health

### `GET /api/v1/health`

 Health

Responses: `200`

### `GET /health`

 Health

Responses: `200`

## integrations

### `GET /api/v1/integrations/gmail/auth-url`

Gmail Auth Url

Responses: `200`

### `GET /api/v1/integrations/gmail/callback`

Gmail Callback

| Parameter | In | Type | Required |
|---|---|---|---|
| `code` | query | string | null | no |
| `state` | query | string | null | no |
| `error` | query | string | null | no |

Responses: `200`; `422` HTTPValidationError

### `POST /api/v1/integrations/gmail/disconnect`

Gmail Disconnect

Responses: `200`

### `POST /api/v1/integrations/gmail/sync`

Gmail Sync

Responses: `200`

### `GET /api/v1/integrations/status`

Status

Responses: `200`

## leads

### `GET /api/v1/leads`

List Leads

| Parameter | In | Type | Required |
|---|---|---|---|
| `status` | query | string | null | no |
| `priority` | query | string | null | no |
| `source` | query | string | null | no |
| `include_archived` | query | boolean | no |
| `page` | query | integer | no |
| `page_size` | query | integer | no |
| `q` | query | string | null | no |
| `sort` | query | string | null | no |

Responses: `200` Page_LeadOut_; `422` HTTPValidationError

### `POST /api/v1/leads`

Create Lead

Request body: `LeadIn`

Schema `LeadIn`:

| Field | Type | Required |
|---|---|---|
| `full_name` | string | yes |
| `email` | string | null | no |
| `phone` | string | null | no |
| `status` | enum(New, Contacted, Qualified, Viewing Scheduled, Negotiation, Won, Lost) | no |
| `priority` | enum(low, medium, high, hot) | null | no |
| `source` | enum(email, manual, web, referral, gmail, demo) | no |
| `preferred_location` | string | null | no |
| `property_type` | enum(apartment, villa, house, plot, commercial) | null | no |
| `bedrooms` | integer | null | no |
| `budget_min` | number | null | no |
| `budget_max` | number | null | no |
| `timeline` | string | null | no |
| `amenities` | array[string] | no |
| `intent` | string | null | no |
| `transaction_type` | enum(buy, rent, sell) | null | no |
| `assigned_agent_id` | string | null | no |
| `tags` | array[string] | no |
| `notes` | string | null | no |
| `next_follow_up_at` | string | null | no |

Responses: `201` LeadOut; `422` HTTPValidationError

### `GET /api/v1/leads/export.csv`

Export Csv

Responses: `200`

### `GET /api/v1/leads/{lead_id}`

Get Lead

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` LeadOut; `422` HTTPValidationError

### `PATCH /api/v1/leads/{lead_id}`

Patch Lead

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Request body: `LeadPatch`

Schema `LeadPatch`:

| Field | Type | Required |
|---|---|---|
| `full_name` | string | null | no |
| `email` | string | null | no |
| `phone` | string | null | no |
| `status` | enum(New, Contacted, Qualified, Viewing Scheduled, Negotiation, Won, Lost) | null | no |
| `priority` | enum(low, medium, high, hot) | null | no |
| `source` | enum(email, manual, web, referral, gmail, demo) | null | no |
| `preferred_location` | string | null | no |
| `property_type` | enum(apartment, villa, house, plot, commercial) | null | no |
| `bedrooms` | integer | null | no |
| `budget_min` | number | null | no |
| `budget_max` | number | null | no |
| `timeline` | string | null | no |
| `amenities` | array[string] | null | no |
| `intent` | string | null | no |
| `transaction_type` | enum(buy, rent, sell) | null | no |
| `assigned_agent_id` | string | null | no |
| `tags` | array[string] | null | no |
| `notes` | string | null | no |
| `next_follow_up_at` | string | null | no |

Responses: `200` LeadOut; `422` HTTPValidationError

### `GET /api/v1/leads/{lead_id}/activity`

Activity

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` array[ActivityOut]; `422` HTTPValidationError

### `POST /api/v1/leads/{lead_id}/archive`

Archive

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` LeadOut; `422` HTTPValidationError

### `GET /api/v1/leads/{lead_id}/matches`

Lead Matches

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` array[MatchOut]; `422` HTTPValidationError

### `POST /api/v1/leads/{lead_id}/rescore`

Rescore

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` LeadOut; `422` HTTPValidationError

### `POST /api/v1/leads/{lead_id}/restore`

Restore

| Parameter | In | Type | Required |
|---|---|---|---|
| `lead_id` | path | string | yes |

Responses: `200` LeadOut; `422` HTTPValidationError

## notifications

### `GET /api/v1/notifications`

Notifications

Responses: `200` array[NotificationOut]

### `POST /api/v1/notifications/{nid}/read`

Read Notification

| Parameter | In | Type | Required |
|---|---|---|---|
| `nid` | path | string | yes |

Responses: `200` NotificationOut; `422` HTTPValidationError

## properties

### `POST /api/v1/matches/search`

Matches Search - Ad-hoc, read-only (not stored) so analysts may use it.

Request body: `MatchSearchIn`

Schema `MatchSearchIn`:

| Field | Type | Required |
|---|---|---|
| `location` | string | null | no |
| `budget_min` | number | null | no |
| `budget_max` | number | null | no |
| `bedrooms` | integer | null | no |
| `property_type` | enum(apartment, villa, house, plot, commercial) | null | no |
| `amenities` | array[string] | no |
| `transaction_type` | enum(buy, rent, sell) | null | no |

Responses: `200` array[MatchOut]; `422` HTTPValidationError

### `GET /api/v1/properties`

List Properties

| Parameter | In | Type | Required |
|---|---|---|---|
| `status` | query | string | null | no |
| `property_type` | query | string | null | no |
| `location` | query | string | null | no |
| `page` | query | integer | no |
| `page_size` | query | integer | no |
| `q` | query | string | null | no |
| `sort` | query | string | null | no |

Responses: `200` Page_PropertyOut_; `422` HTTPValidationError

### `POST /api/v1/properties`

Create Property

Request body: `PropertyIn`

Schema `PropertyIn`:

| Field | Type | Required |
|---|---|---|
| `title` | string | yes |
| `property_type` | enum(apartment, villa, house, plot, commercial) | no |
| `listing_type` | enum(sale, rent) | no |
| `price` | number | yes |
| `location` | string | yes |
| `city` | string | null | no |
| `bedrooms` | integer | null | no |
| `bathrooms` | integer | null | no |
| `area_sqft` | number | null | no |
| `units_available` | integer | no |
| `amenities` | array[string] | no |
| `status` | enum(available, reserved, sold, rented) | no |
| `description` | string | null | no |
| `url` | string | null | no |
| `agent_id` | string | null | no |

Responses: `201` PropertyOut; `422` HTTPValidationError

### `GET /api/v1/properties/{pid}`

Get Property

| Parameter | In | Type | Required |
|---|---|---|---|
| `pid` | path | string | yes |

Responses: `200` PropertyOut; `422` HTTPValidationError

### `PATCH /api/v1/properties/{pid}`

Patch Property

| Parameter | In | Type | Required |
|---|---|---|---|
| `pid` | path | string | yes |

Request body: `PropertyPatch`

Schema `PropertyPatch`:

| Field | Type | Required |
|---|---|---|
| `title` | string | null | no |
| `property_type` | enum(apartment, villa, house, plot, commercial) | null | no |
| `listing_type` | enum(sale, rent) | null | no |
| `price` | number | null | no |
| `location` | string | null | no |
| `city` | string | null | no |
| `bedrooms` | integer | null | no |
| `bathrooms` | integer | null | no |
| `area_sqft` | number | null | no |
| `units_available` | integer | null | no |
| `amenities` | array[string] | null | no |
| `status` | enum(available, reserved, sold, rented) | null | no |
| `description` | string | null | no |
| `url` | string | null | no |
| `agent_id` | string | null | no |

Responses: `200` PropertyOut; `422` HTTPValidationError

### `DELETE /api/v1/properties/{pid}`

Delete Property

| Parameter | In | Type | Required |
|---|---|---|---|
| `pid` | path | string | yes |

Responses: `204`; `422` HTTPValidationError

## settings

### `GET /api/v1/settings`

Get Settings Ep

Responses: `200`

### `PATCH /api/v1/settings`

Patch Settings

Request body: `SettingsPatch`

Schema `SettingsPatch`:

| Field | Type | Required |
|---|---|---|
| `demo_mode` | boolean | null | no |

Responses: `200`; `422` HTTPValidationError

## tasks

### `GET /api/v1/tasks`

List Tasks

| Parameter | In | Type | Required |
|---|---|---|---|
| `status` | query | string | null | no |
| `lead_id` | query | string | null | no |
| `overdue` | query | boolean | null | no |
| `owner_id` | query | string | null | no |
| `page` | query | integer | no |
| `page_size` | query | integer | no |
| `q` | query | string | null | no |
| `sort` | query | string | null | no |

Responses: `200` Page_TaskOut_; `422` HTTPValidationError

### `POST /api/v1/tasks`

Create Task

Request body: `TaskIn`

Schema `TaskIn`:

| Field | Type | Required |
|---|---|---|
| `title` | string | yes |
| `description` | string | null | no |
| `lead_id` | string | null | no |
| `owner_id` | string | null | no |
| `priority` | enum(low, medium, high, hot) | no |
| `due_at` | string | yes |
| `reminder_at` | string | null | no |

Responses: `201` TaskOut; `422` HTTPValidationError

### `GET /api/v1/tasks/reminders`

Reminders

Responses: `200` array[TaskOut]

### `GET /api/v1/tasks/{tid}`

Get Task

| Parameter | In | Type | Required |
|---|---|---|---|
| `tid` | path | string | yes |

Responses: `200` TaskOut; `422` HTTPValidationError

### `PATCH /api/v1/tasks/{tid}`

Patch Task

| Parameter | In | Type | Required |
|---|---|---|---|
| `tid` | path | string | yes |

Request body: `TaskPatch`

Schema `TaskPatch`:

| Field | Type | Required |
|---|---|---|
| `title` | string | null | no |
| `description` | string | null | no |
| `lead_id` | string | null | no |
| `owner_id` | string | null | no |
| `priority` | enum(low, medium, high, hot) | null | no |
| `status` | enum(pending, completed, cancelled) | null | no |
| `due_at` | string | null | no |
| `reminder_at` | string | null | no |

Responses: `200` TaskOut; `422` HTTPValidationError

### `DELETE /api/v1/tasks/{tid}`

Delete Task

| Parameter | In | Type | Required |
|---|---|---|---|
| `tid` | path | string | yes |

Responses: `204`; `422` HTTPValidationError

### `POST /api/v1/tasks/{tid}/complete`

Complete

| Parameter | In | Type | Required |
|---|---|---|---|
| `tid` | path | string | yes |

Responses: `200` TaskOut; `422` HTTPValidationError
