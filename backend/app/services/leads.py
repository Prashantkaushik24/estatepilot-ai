from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.nlp import norm_phone
from app.models import Lead
from app.services.scoring import priority_for, score_lead

PREF_FIELDS = ["preferred_location", "property_type", "bedrooms", "budget_min", "budget_max", "timeline", "intent", "transaction_type"]


def find_lead(db: Session, org_id: str, email: str | None, phone: str | None) -> Lead | None:
    if email:
        l = db.scalar(select(Lead).where(Lead.organization_id == org_id, Lead.email == email.lower()).order_by(Lead.created_at))
        if l:
            return l
    np = norm_phone(phone)
    if np:
        for l in db.scalars(select(Lead).where(Lead.organization_id == org_id, Lead.phone.is_not(None))):
            if norm_phone(l.phone) == np:
                return l
    return None


def rescore(lead: Lead, classification: str | None = None):
    score, reasons = score_lead(lead, classification)
    lead.score, lead.score_reasons, lead.priority = score, reasons, priority_for(score)
    return lead


def upsert_from_extraction(db: Session, org_id: str, ex: dict, sender_email: str, source: str, classification: str | None,
                           is_demo: bool = False) -> tuple[Lead, bool]:
    email = (ex.get("sender_email") or sender_email or "").lower() or None
    lead = find_lead(db, org_id, email, ex.get("phone"))
    created = lead is None
    if created:
        lead = Lead(organization_id=org_id, full_name=ex.get("customer_name") or (email or "Unknown"), email=email,
                    phone=ex.get("phone"), source=source if source in ("email", "gmail", "demo") else "email", status="New",
                    is_demo=is_demo, amenities=[], tags=[], score_reasons=[])
        db.add(lead)
    else:
        if not lead.email and email:
            lead.email = email
        if not lead.phone and ex.get("phone"):
            lead.phone = ex["phone"]
    for f in PREF_FIELDS:
        if ex.get(f) not in (None, "", []):
            setattr(lead, f, ex[f])
    if ex.get("amenities"):
        lead.amenities = sorted(set(lead.amenities or []) | set(ex["amenities"]))
    rescore(lead, classification)
    db.flush()
    return lead, created


def followup_due(lead: Lead) -> datetime:
    hrs = {"hot": 4, "high": 24, "medium": 48, "low": 72}[lead.priority]
    return datetime.now(timezone.utc) + timedelta(hours=hrs)
