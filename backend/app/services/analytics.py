import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Email, EmailDraft, Lead, Property, Task
from app.schemas.entities import LEAD_STATUSES


def _open_leads(org_id):
    return (Lead.organization_id == org_id, Lead.is_archived.is_(False))


def first_response_minutes(db: Session, org_id: str) -> float | None:
    """Mean minutes between a lead's earliest email and the earliest approved/sent reply draft."""
    rows = db.execute(select(Email.lead_id, func.min(Email.received_at)).where(Email.organization_id == org_id, Email.lead_id.is_not(None)).group_by(Email.lead_id)).all()
    first = {r[0]: r[1] for r in rows}
    resp = {}
    for d in db.scalars(select(EmailDraft).where(EmailDraft.organization_id == org_id, EmailDraft.lead_id.is_not(None), EmailDraft.status.in_(("approved", "sent")))):
        t = d.sent_at or d.approved_at
        if t and (d.lead_id not in resp or t < resp[d.lead_id]):
            resp[d.lead_id] = t
    vals = [(resp[l] - first[l]).total_seconds() / 60 for l in resp if l in first and resp[l] >= first[l]]
    return round(sum(vals) / len(vals), 1) if vals else None


def metrics(db: Session, org_id: str) -> dict:
    base = _open_leads(org_id)
    cnt = lambda *c: db.scalar(select(func.count()).select_from(Lead).where(*base, *c)) or 0  # noqa
    total = cnt()
    now = datetime.now(timezone.utc)
    value = lambda *c: float(db.scalar(select(func.coalesce(func.sum(func.coalesce(Lead.budget_max, Lead.budget_min, 0)), 0)).where(*base, *c)) or 0)  # noqa
    won = cnt(Lead.status == "Won")
    ecount = lambda *c: db.scalar(select(func.count()).select_from(Email).where(Email.organization_id == org_id, *c)) or 0  # noqa
    tcount = lambda *c: db.scalar(select(func.count()).select_from(Task).where(Task.organization_id == org_id, *c)) or 0  # noqa
    demo = (db.scalar(select(func.count()).select_from(Lead).where(Lead.organization_id == org_id, Lead.is_demo.is_(True))) or 0) > 0 \
        or (db.scalar(select(func.count()).select_from(Email).where(Email.organization_id == org_id, Email.is_demo_ai.is_(True))) or 0) > 0
    return {
        "total_leads": total,
        "new_leads": cnt(Lead.status == "New"),
        "qualified_leads": cnt(Lead.status == "Qualified"),
        "hot_leads": cnt(Lead.priority == "hot"),
        "emails_processed": ecount(Email.processing_status == "processed"),
        "unread_emails": ecount(Email.is_read.is_(False)),
        "pending_followups": tcount(Task.status == "pending"),
        "overdue_tasks": tcount(Task.status == "pending", Task.due_at < now),
        "avg_first_response_minutes": first_response_minutes(db, org_id),
        "conversion_rate": round(won / total, 4) if total else 0.0,
        "pipeline_value": value(Lead.status.not_in(("Won", "Lost"))),
        "won_value": value(Lead.status == "Won"),
        "data_source": "database",
        "has_demo_data": demo,
    }


def _bucket(v):
    if not v:
        return None
    return ("Under ₹25L" if v < 2.5e6 else "₹25L-50L" if v < 5e6 else "₹50L-1Cr" if v < 1e7 else "₹1Cr-2Cr" if v < 2e7 else "Above ₹2Cr")


BUCKET_ORDER = ["Under ₹25L", "₹25L-50L", "₹50L-1Cr", "₹1Cr-2Cr", "Above ₹2Cr"]


def charts(db: Session, org_id: str) -> dict:
    leads = db.scalars(select(Lead).where(Lead.organization_id == org_id, Lead.is_archived.is_(False))).unique().all()
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    by_day = Counter(l.created_at.date() for l in leads)
    pairs = lambda c: [{"name": k, "value": v} for k, v in c.most_common()]  # noqa
    stat = Counter(l.status for l in leads)
    reached = {}
    run = 0
    for s in reversed([x for x in LEAD_STATUSES if x != "Lost"]):
        run += stat.get(s, 0)
        reached[s] = run
    n_emails = db.scalar(select(func.count()).select_from(Email).where(Email.organization_id == org_id)) or 0
    bud = Counter(b for l in leads if (b := _bucket(l.budget_max or l.budget_min)))
    tasks = Counter(t.status if not t.is_overdue else "overdue" for t in db.scalars(select(Task).where(Task.organization_id == org_id)).unique())
    emails = Counter(e.classification for e in db.scalars(select(Email).where(Email.organization_id == org_id)) if e.classification)
    return {
        "leads_over_time": [{"date": d.isoformat(), "count": by_day.get(d, 0)} for d in days],
        "leads_by_source": pairs(Counter(l.source for l in leads)),
        "lead_status": [{"name": s, "value": stat.get(s, 0)} for s in LEAD_STATUSES],
        "email_intent": pairs(emails),
        "demand_by_location": pairs(Counter(l.preferred_location for l in leads if l.preferred_location))[:10],
        "budget_distribution": [{"name": b, "value": bud.get(b, 0)} for b in BUCKET_ORDER],
        "followup_status": pairs(tasks),
        "funnel": [{"name": "Emails", "value": n_emails}, {"name": "Leads", "value": len(leads)}] +
                  [{"name": s, "value": reached[s]} for s in ["Contacted", "Qualified", "Viewing Scheduled", "Negotiation", "Won"]],
    }


def _safe(v):
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        v = ", ".join(map(str, v)) if isinstance(v, list) else str(v)
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    v = str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v  # CSV/formula injection guard


def to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(columns)
    for r in rows:
        w.writerow([_safe(r.get(c)) for c in columns])
    return buf.getvalue()


LEAD_COLS = ["id", "full_name", "email", "phone", "status", "priority", "score", "source", "preferred_location", "property_type", "bedrooms",
             "budget_min", "budget_max", "timeline", "amenities", "transaction_type", "assigned_agent_name", "is_demo", "created_at"]


def lead_rows(db, org_id, include_archived=False):
    q = select(Lead).where(Lead.organization_id == org_id)
    if not include_archived:
        q = q.where(Lead.is_archived.is_(False))
    return [{c: getattr(l, c) for c in LEAD_COLS} for l in db.scalars(q.order_by(Lead.created_at)).unique()]


def export(db: Session, org_id: str, kind: str) -> str:
    if kind in ("leads", "fact_leads"):
        rows = lead_rows(db, org_id)
        cols = LEAD_COLS
        if kind == "fact_leads":
            for r, l in zip(rows, db.scalars(select(Lead).where(Lead.organization_id == org_id, Lead.is_archived.is_(False)).order_by(Lead.created_at)).unique()):
                r["pipeline_value"] = (l.budget_max or l.budget_min or 0) if l.status not in ("Won", "Lost") else 0
                r["won_value"] = (l.budget_max or l.budget_min or 0) if l.status == "Won" else 0
                r["is_converted"] = int(l.status == "Won")
            cols = LEAD_COLS + ["pipeline_value", "won_value", "is_converted"]
        return to_csv(rows, cols)
    if kind == "emails":
        cols = ["id", "sender_email", "subject", "received_at", "source", "classification", "processing_status", "priority", "lead_id", "is_demo_ai"]
        return to_csv([{c: getattr(e, c) for c in cols} for e in db.scalars(select(Email).where(Email.organization_id == org_id).order_by(Email.received_at))], cols)
    if kind == "tasks":
        cols = ["id", "title", "lead_id", "lead_name", "owner_name", "priority", "status", "due_at", "completed_at", "is_overdue", "source", "created_at"]
        return to_csv([{c: getattr(t, c) for c in cols} for t in db.scalars(select(Task).where(Task.organization_id == org_id).order_by(Task.created_at)).unique()], cols)
    if kind == "properties":
        cols = ["id", "title", "property_type", "listing_type", "price", "location", "city", "bedrooms", "bathrooms", "area_sqft", "units_available", "amenities", "status", "is_demo", "created_at"]
        return to_csv([{c: getattr(p, c) for c in cols} for p in db.scalars(select(Property).where(Property.organization_id == org_id).order_by(Property.created_at))], cols)
    raise KeyError(kind)
