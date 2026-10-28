"""Gmail integration (OAuth, sync, send). UNVERIFIED without real Google credentials.

Tokens are Fernet-encrypted at rest. OAuth `state` is a signed, short-lived JWT carrying org/user ids.
Scopes: gmail.readonly (sync) + gmail.send (only used after explicit approval and when SENDING_ENABLED).
"""
import base64
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret, sign_state, verify_state
from app.models import EmailAccount
from app.services.emails import DuplicateEmail, create_email

log = logging.getLogger("estatepilot.gmail")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send",
          "openid", "https://www.googleapis.com/auth/userinfo.email"]


class GmailError(Exception):
    pass


def configured() -> bool:
    s = get_settings()
    return bool(s.GOOGLE_CLIENT_ID and s.GOOGLE_CLIENT_SECRET)


def _flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    s = get_settings()
    cfg = {"web": {"client_id": s.GOOGLE_CLIENT_ID, "client_secret": s.GOOGLE_CLIENT_SECRET,
                   "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token",
                   "redirect_uris": [s.GOOGLE_REDIRECT_URI]}}
    return Flow.from_client_config(cfg, scopes=SCOPES, state=state, redirect_uri=s.GOOGLE_REDIRECT_URI)


def auth_url(org_id: str, user_id: str) -> str:
    if not configured():
        raise GmailError("Gmail OAuth not configured")
    state = sign_state({"org": org_id, "user": user_id})
    url, _ = _flow(state).authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true", state=state)
    return url


def get_account(db: Session, org_id: str) -> EmailAccount | None:
    return db.scalar(select(EmailAccount).where(EmailAccount.organization_id == org_id, EmailAccount.provider == "gmail",
                                                EmailAccount.connected.is_(True)))


def handle_callback(db: Session, code: str, state: str) -> EmailAccount:
    data = verify_state(state)  # raises on tampering/expiry
    if not configured():
        raise GmailError("Gmail OAuth not configured")
    flow = _flow(state)
    flow.fetch_token(code=code)
    creds = flow.credentials
    from googleapiclient.discovery import build
    profile = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()
    addr = profile["emailAddress"]
    acc = db.scalar(select(EmailAccount).where(EmailAccount.organization_id == data["org"], EmailAccount.provider == "gmail",
                                               EmailAccount.account_email == addr))
    if not acc:
        acc = EmailAccount(organization_id=data["org"], provider="gmail", account_email=addr)
        db.add(acc)
    acc.access_token_enc = encrypt_secret(creds.token)
    if creds.refresh_token:
        acc.refresh_token_enc = encrypt_secret(creds.refresh_token)
    acc.token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
    acc.connected = True
    db.flush()
    return acc


def _service(acc: EmailAccount):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    s = get_settings()
    creds = Credentials(token=decrypt_secret(acc.access_token_enc), refresh_token=decrypt_secret(acc.refresh_token_enc),
                        token_uri="https://oauth2.googleapis.com/token", client_id=s.GOOGLE_CLIENT_ID,
                        client_secret=s.GOOGLE_CLIENT_SECRET, scopes=SCOPES)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _body(payload: dict) -> str:
    def walk(p):
        if p.get("mimeType", "").startswith("text/plain") and p.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(p["body"]["data"] + "==").decode("utf-8", "replace")
        for sub in p.get("parts", []) or []:
            r = walk(sub)
            if r:
                return r
        return None
    return walk(payload) or ""


def sync(db: Session, org_id: str, max_results: int = 25) -> tuple[list, int]:
    """Import recent inbox messages. Dedupe by Gmail message id (and content hash). Returns (new_emails, skipped)."""
    acc = get_account(db, org_id)
    if not acc:
        raise GmailError("Gmail not connected")
    svc = _service(acc)
    msgs = svc.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=max_results).execute().get("messages", [])
    created, skipped = [], 0
    for m in msgs:
        try:
            full = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
            h = {x["name"].lower(): x["value"] for x in full["payload"].get("headers", [])}
            name, addr = parseaddr(h.get("from", ""))
            if not addr:
                continue
            try:
                when = parsedate_to_datetime(h["date"]).astimezone(timezone.utc) if h.get("date") else None
            except (TypeError, ValueError):
                when = None
            e = create_email(db, org_id, sender_email=addr, sender_name=name or None, subject=h.get("subject", "(no subject)"),
                             body=_body(full["payload"]) or full.get("snippet", ""), received_at=when, source="gmail",
                             external_id=m["id"], recipient_email=h.get("to"), thread_external_id=full.get("threadId"))
            created.append(e)
        except DuplicateEmail:
            skipped += 1
        except Exception as ex:  # one bad message must not abort the sync
            log.warning("gmail message import failed: %s", type(ex).__name__)
    acc.last_sync_at = datetime.now(timezone.utc)
    return created, skipped


def send(db: Session, org_id: str, to: str, subject: str, body: str) -> str:
    """Send through Gmail API. Returns provider message id; raises on failure (caller must not mark sent)."""
    acc = get_account(db, org_id)
    if not acc:
        raise GmailError("Gmail not connected")
    msg = MIMEText(body, "plain", "utf-8")
    msg["to"], msg["from"], msg["subject"] = to, acc.account_email, subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        r = _service(acc).users().messages().send(userId="me", body={"raw": raw}).execute()
    except Exception as e:
        raise GmailError(f"Gmail send failed: {type(e).__name__}") from e
    if not r.get("id"):
        raise GmailError("Gmail did not confirm the send")
    return r["id"]


def disconnect(db: Session, org_id: str):
    for acc in db.scalars(select(EmailAccount).where(EmailAccount.organization_id == org_id, EmailAccount.provider == "gmail")):
        acc.connected = False
        acc.access_token_enc = acc.refresh_token_enc = None
