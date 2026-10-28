import hashlib
import html
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Email, EmailThread


def normalize_text(s: str, limit: int = 20000) -> str:
    s = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", s or "")
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s).replace("\r\n", "\n")
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s[:limit]


def content_hash(sender: str, subject: str, body: str) -> str:
    key = "|".join([sender.strip().lower(), re.sub(r"\s+", " ", subject.strip().lower()), re.sub(r"\s+", " ", body.strip().lower())])
    return hashlib.sha256(key.encode()).hexdigest()


class DuplicateEmail(Exception):
    def __init__(self, existing_id: str):
        self.existing_id = existing_id


def create_email(db: Session, org_id: str, *, sender_email: str, sender_name: str | None, subject: str, body: str,
                 received_at: datetime | None, source: str, external_id: str | None = None,
                 recipient_email: str | None = None, thread_external_id: str | None = None, is_demo: bool = False) -> Email:
    body_n = normalize_text(body)
    subject_n = normalize_text(subject, 500)
    h = content_hash(sender_email, subject_n, body_n)
    q = select(Email).where(Email.organization_id == org_id)
    ex = db.scalar(q.where(Email.content_hash == h)) or (db.scalar(q.where(Email.external_id == external_id)) if external_id else None)
    if ex:
        raise DuplicateEmail(ex.id)
    thread_id = None
    if thread_external_id:
        t = db.scalar(select(EmailThread).where(EmailThread.organization_id == org_id, EmailThread.external_id == thread_external_id))
        if not t:
            t = EmailThread(organization_id=org_id, external_id=thread_external_id, subject=subject_n)
            db.add(t)
            db.flush()
        thread_id = t.id
    e = Email(organization_id=org_id, thread_id=thread_id, external_id=external_id, content_hash=h, sender_name=sender_name,
              sender_email=sender_email.lower(), recipient_email=recipient_email, subject=subject_n, body=body_n,
              received_at=received_at or datetime.now(timezone.utc), source=source, processing_status="pending", is_demo=is_demo)
    db.add(e)
    db.flush()
    return e


DEMO_EMAILS = [
    dict(sender_email="priya.sharma@example.com", sender_name="Priya Sharma", subject="Looking for 3 BHK in Jaipur",
         body="Hello, I am looking for a 3 BHK apartment in Jaipur under ₹80 lakh. I prefer a location near schools and would like to move within two months."),
    dict(sender_email="rahul.verma@example.com", sender_name="Rahul Verma", subject="Site visit request - villa",
         body="Hi, I saw your listing for a villa in Malviya Nagar. Budget is around ₹2 crore. Please arrange a site visit this week. My number is 9876543210. Need parking and a garden."),
    dict(sender_email="anita.desai@example.com", sender_name="Anita Desai", subject="2 BHK flat for rent",
         body="Hello, I want to rent a 2 BHK flat in Jagatpura Jaipur, budget 25k per month. Looking to move in next month. Gym and lift preferred."),
]
