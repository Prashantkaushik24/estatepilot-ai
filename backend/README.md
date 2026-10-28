# EstatePilot AI - Backend (FastAPI)

Contract: `../docs/API_CONTRACT.md`. Base URL `http://localhost:8000/api/v1`, docs at `/docs`.

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head          # create schema (SQLite dev also auto-creates tables)
.venv/bin/python -m app.db.seed         # idempotent demo data (also auto on startup if DB empty & SEED_DEMO=true)
.venv/bin/uvicorn app.main:app --port 8000
.venv/bin/pytest -q
```
Demo logins (password `Passw0rd!demo`): admin@/manager@/agent@/analyst@demo.com.

Notes
- AI: `AI_PROVIDER=demo` uses deterministic rules (flagged `is_demo_ai`). `openai`/`gemini` outputs are pydantic-validated with retries; on failure the run is marked failed and there is NO fallback to demo unless the org's demo mode is on (`DEMO_MODE`, togglable via PATCH /settings).
- Sending: off by default (`SENDING_ENABLED=false`); requires approved draft, kill switch off, connected Gmail, `confirm` + `confirm_recipient`. Gmail code is unverified without real Google credentials.
- Analysts are read-only; `/matches/search` and CSV exports are allowed for them (non-mutating).
- Optional `ProcessResult.run` is null when an email is imported without processing (process=false or automation paused).
- Docker: `docker build -t estatepilot-api .` (runs migrations then uvicorn; unverified here).
- Power BI assets: `../powerbi/`.
