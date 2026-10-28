#!/usr/bin/env python3
"""Generate docs/API_REFERENCE.md from the FastAPI OpenAPI schema (stdlib only).

Usage:
  python scripts/generate_api_reference.py                       # fetch http://localhost:8000/openapi.json
  python scripts/generate_api_reference.py --url http://host:8000/openapi.json
  python scripts/generate_api_reference.py --file openapi.json
  cd backend && .venv/bin/python ../scripts/generate_api_reference.py --from-app   # import the app directly
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "API_REFERENCE.md"

# Minimum role per mutating route, taken from backend/app/api/*.py (Depends(...)). Reads need any authenticated user.
ROLE_NOTE = """Role hierarchy: `admin > manager > agent > analyst` (analyst is read-only). Minimum roles found in the code:

| Operation | Minimum role |
|---|---|
| Any GET (except `/health`, Gmail callback) | analyst (authenticated) |
| Create/edit leads, properties, tasks; import/process emails; edit/approve/send drafts; `POST /matches/search` | agent (`/matches/search` is non-mutating and is also allowed for analyst per backend README) |
| Delete property; list users; pause/resume automation; toggle rules; PATCH settings; Gmail sync | manager |
| Create/patch users; kill switch; Gmail auth-url / disconnect | admin |
"""


def load(args):
    if args.file:
        return json.loads(Path(args.file).read_text())
    if args.from_app:
        sys.path.insert(0, str(ROOT / "backend"))
        from app.main import app  # type: ignore
        return app.openapi()
    try:
        with urllib.request.urlopen(args.url, timeout=10) as r:
            return json.load(r)
    except Exception as e:  # noqa
        sys.exit(f"Could not fetch {args.url} ({e}).\nStart the backend, or use --file / --from-app.")


def ref_name(s):
    return s.get("$ref", "").split("/")[-1] if isinstance(s, dict) else ""


def type_of(s, comps):
    if not isinstance(s, dict):
        return "any"
    if "$ref" in s:
        return ref_name(s)
    if "anyOf" in s:
        return " | ".join(type_of(x, comps) for x in s["anyOf"])
    if "enum" in s:
        return "enum(" + ", ".join(map(str, s["enum"])) + ")"
    if s.get("type") == "array":
        return f"array[{type_of(s.get('items', {}), comps)}]"
    return s.get("type", "object")


def schema_table(name, comps):
    sch = comps.get(name)
    if not sch or "properties" not in sch:
        return []
    req = set(sch.get("required", []))
    rows = [f"| `{k}` | {type_of(v, comps)} | {'yes' if k in req else 'no'} |" for k, v in sch["properties"].items()]
    return ["", f"Schema `{name}`:", "", "| Field | Type | Required |", "|---|---|---|"] + rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/openapi.json")
    ap.add_argument("--file")
    ap.add_argument("--from-app", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    spec = load(a)
    comps = spec.get("components", {}).get("schemas", {})
    by_tag = {}
    for path, ops in sorted(spec["paths"].items()):
        for method, op in ops.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            by_tag.setdefault((op.get("tags") or ["other"])[0], []).append((path, method, op))
    n = sum(len(v) for v in by_tag.values())
    L = [f"# EstatePilot AI - API Reference", "",
         f"_Generated from the live OpenAPI schema (`{spec['info']['title']}` v{spec['info']['version']}) by "
         "`scripts/generate_api_reference.py`. Do not edit by hand; re-run the script._", "",
         f"Base URL: `http://localhost:8000` (versioned routes under `/api/v1`). Interactive docs: `/docs`. {n} operations.", "",
         "Auth: `Authorization: Bearer <jwt>` from `POST /api/v1/auth/login`. Errors are `{\"detail\": \"...\"}` (401/403/404/409/422/429/502). "
         "All timestamps are ISO-8601 UTC (`...Z`).", "", ROLE_NOTE, "## Examples", "",
         "```bash", "# 1. log in (demo seed user)",
         "curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \\",
         "  -d '{\"email\":\"agent@demo.com\",\"password\":\"Passw0rd!demo\"}'", "# -> {\"access_token\":\"...\",\"token_type\":\"bearer\",\"user\":{...}}", "",
         "# 2. import + process an email", "TOKEN=<access_token>",
         "curl -s -X POST http://localhost:8000/api/v1/emails/import -H \"Authorization: Bearer $TOKEN\" -H 'Content-Type: application/json' \\",
         "  -d '{\"sender_email\":\"neha@example.com\",\"sender_name\":\"Neha\",\"subject\":\"3 BHK in Jaipur\",\"body\":\"Looking for a 3 BHK apartment in Jaipur under 80 lakh. Call 9876501234\"}'",
         "# -> {\"email\":{...,\"classification\":\"buying_request\",\"extraction\":{...},\"draft\":{...}},\"lead\":{...},\"lead_created\":true,\"matches\":[...],\"steps\":[...],\"run\":{...}}", "",
         "# 3. approve a draft (never sends)", "curl -s -X POST http://localhost:8000/api/v1/drafts/<draft_id>/approve -H \"Authorization: Bearer $TOKEN\"", "",
         "# 4. send (only if SENDING_ENABLED=true, Gmail connected, draft approved)",
         "curl -s -X POST http://localhost:8000/api/v1/drafts/<draft_id>/send -H \"Authorization: Bearer $TOKEN\" -H 'Content-Type: application/json' \\",
         "  -d '{\"confirm\":true,\"confirm_recipient\":\"neha@example.com\"}'", "```", "",
         "Duplicate import returns `409 {\"detail\":\"duplicate\",\"existing_email_id\":\"...\"}`. Bad login returns `401 {\"detail\":\"Invalid email or password\"}`; "
         "missing token returns `401 {\"detail\":\"Not authenticated\"}`.", ""]
    for tag in sorted(by_tag):
        L += [f"## {tag}", ""]
        for path, method, op in by_tag[tag]:
            L += [f"### `{method.upper()} {path}`", "", op.get("summary", "") + (f" - {op['description'].strip().splitlines()[0]}" if op.get("description") else ""), ""]
            params = [p for p in op.get("parameters", [])]
            if params:
                L += ["| Parameter | In | Type | Required |", "|---|---|---|---|"]
                L += [f"| `{p['name']}` | {p['in']} | {type_of(p.get('schema', {}), comps)} | {'yes' if p.get('required') else 'no'} |" for p in params]
                L.append("")
            rb = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
            if rb:
                L.append(f"Request body: `{type_of(rb, comps)}`")
                L += schema_table(ref_name(rb), comps)
                L.append("")
            resp = []
            for code, r in op.get("responses", {}).items():
                sc = r.get("content", {}).get("application/json", {}).get("schema")
                resp.append(f"`{code}`" + (f" {type_of(sc, comps)}" if sc else ""))
            L += ["Responses: " + "; ".join(resp), ""]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {a.out} ({n} operations)")


if __name__ == "__main__":
    main()
