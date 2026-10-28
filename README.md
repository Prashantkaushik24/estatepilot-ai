# EstatePilot AI

AI-assisted lead management for real-estate agencies: customer emails become classified, extracted, deduplicated, scored leads with explained property matches and approval-gated reply drafts.

Stack: React + Vite + TypeScript + Tailwind (frontend), FastAPI + SQLAlchemy + Alembic (backend, SQLite by default), Power BI SQL/DAX assets.

## Honest status

| Verified (run on 2026-10-27, macOS) | Implemented but UNVERIFIED (no credentials / not run) |
|---|---|
| Backend: 23 pytest tests pass | OpenAI and Gemini providers (live calls) |
| Frontend: 11 Vitest tests pass; `npm run build` succeeds | Gmail OAuth, sync, send (mocked in tests only) |
| `alembic upgrade head` creates all 14 tables | Docker / docker-compose, Windows commands, PostgreSQL |
| Demo (rule-based) AI pipeline end to end | Power BI: views tested in SQLite; DAX unexecuted; **no PBIX file** |

Not production-ready: see "Security and privacy" in the guide. The default AI is a deterministic demo provider (flagged "Demo AI"), not a language model. No accuracy has been measured. All timestamps are stored in UTC.

## Quick start (macOS / Linux)

```
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/python -m app.db.seed
.venv/bin/uvicorn app.main:app --port 8000
```

In a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Demo logins (password `Passw0rd!demo`): `admin@demo.com`, `manager@demo.com`, `agent@demo.com`, `analyst@demo.com`. API docs: http://localhost:8000/docs.

Windows PowerShell (not run on Windows): `py -3.13 -m venv .venv`, `.\.venv\Scripts\pip install -r requirements.txt`, `Copy-Item .env.example .env`, `.\.venv\Scripts\alembic upgrade head`, `.\.venv\Scripts\python -m app.db.seed`, `.\.venv\Scripts\uvicorn app.main:app --port 8000`.

Tests: `cd backend && .venv/bin/pytest -q` and `cd frontend && npm test`.

## Documentation

| File | Content |
|---|---|
| `docs/ESTATEPILOT_AI_COMPLETE_GUIDE.md` | 20-chapter complete guide (also generated as DOCX) |
| `docs/ARCHITECTURE.md` | Architecture and pipeline |
| `docs/API_REFERENCE.md` | Generated from OpenAPI, with examples |
| `docs/API_CONTRACT.md` | Original frontend/backend contract |
| `docs/POWER_BI_GUIDE.md`, `powerbi/` | Power BI assets and manual steps |

### Generating the Word document

Uses an isolated virtual environment so nothing is installed globally.

```
python3 -m venv scripts/.venv
scripts/.venv/bin/pip install -r scripts/requirements.txt
scripts/.venv/bin/python scripts/generate_documentation.py
```

Output: `docs/ESTATEPILOT_AI_COMPLETE_GUIDE.docx` (cover page, table of contents field, headings, tables, code blocks, header/footer, page numbers). Options: `--input`, `--output`. If `python-docx` is missing the script prints an install hint and exits. In Word, right-click the table of contents and choose Update Field to populate page numbers.

Regenerate the API reference (backend running): `python3 scripts/generate_api_reference.py` (also supports `--file openapi.json` and `--from-app`).

## Configuration

See `backend/.env.example` and chapter 14 of the guide. Key variables: `AI_PROVIDER` (demo/openai/gemini), `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID/SECRET`, `SENDING_ENABLED` (default false), `SECRET_KEY`, `CORS_ORIGINS`.
