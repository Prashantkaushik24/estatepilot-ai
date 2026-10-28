from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.helpers import get_or_404
from app.core.deps import PageParams, agent_up, any_user, like, paginate
from app.db.session import get_db
from app.models import AuditLog, Lead, User
from app.schemas.common import Page
from app.schemas.entities import ActivityOut, LeadIn, LeadOut, LeadPatch, MatchOut
from app.services import analytics, leads as svc
from app.services.audit import audit
from app.services.matching import match_lead

router = APIRouter(prefix="/leads", tags=["leads"])
SORTABLE = {"created_at", "updated_at", "score", "full_name", "status", "priority", "budget_max", "next_follow_up_at"}
PREF = {"preferred_location", "property_type", "bedrooms", "budget_min", "budget_max", "timeline", "amenities", "transaction_type"}


def _check_agent(db, org_id, agent_id):
    if agent_id:
        u = db.get(User, agent_id)
        if not u or u.organization_id != org_id:
            raise HTTPException(422, "assigned_agent_id not in organization")


@router.get("", response_model=Page[LeadOut])
def list_leads(pp: PageParams = Depends(), status: str | None = None, priority: str | None = None, source: str | None = None,
               include_archived: bool = False, user: User = Depends(any_user), db: Session = Depends(get_db)):
    stmt = select(Lead).where(Lead.organization_id == user.organization_id)
    if not include_archived:
        stmt = stmt.where(Lead.is_archived.is_(False))
    if status:
        stmt = stmt.where(Lead.status == status)
    if priority:
        stmt = stmt.where(Lead.priority == priority)
    if source:
        stmt = stmt.where(Lead.source == source)
    if pp.q:
        p = like(pp.q)
        stmt = stmt.where(or_(Lead.full_name.ilike(p, escape="\\"), Lead.email.ilike(p, escape="\\"), Lead.phone.ilike(p, escape="\\"),
                              Lead.preferred_location.ilike(p, escape="\\")))
    return paginate(db, stmt, pp, Lead, SORTABLE)


@router.get("/export.csv")
def export_csv(user: User = Depends(any_user), db: Session = Depends(get_db)):
    return Response(analytics.export(db, user.organization_id, "leads"), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=leads.csv"})


@router.post("", response_model=LeadOut, status_code=201)
def create_lead(body: LeadIn, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    _check_agent(db, user.organization_id, body.assigned_agent_id)
    if svc.find_lead(db, user.organization_id, body.email, body.phone):
        raise HTTPException(409, "A lead with this email or phone already exists")
    data = body.model_dump()
    prio = data.pop("priority")
    data["email"] = data["email"].lower() if data["email"] else None
    lead = Lead(organization_id=user.organization_id, **data)
    svc.rescore(lead)
    if prio:
        lead.priority = prio
    db.add(lead)
    db.flush()
    audit(db, user.organization_id, "lead.created", "Lead created manually", entity_type="lead", entity_id=lead.id, actor_id=user.id)
    db.commit()
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    return get_or_404(db, Lead, lead_id, user.organization_id, "Lead")


@router.patch("/{lead_id}", response_model=LeadOut)
def patch_lead(lead_id: str, body: LeadPatch, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    data = body.model_dump(exclude_unset=True)
    _check_agent(db, user.organization_id, data.get("assigned_agent_id"))
    if data.get("email"):
        data["email"] = data["email"].lower()
    old_status = lead.status
    prio = data.pop("priority", None)
    for k, v in data.items():
        setattr(lead, k, v)
    if PREF & set(data) or "email" in data or "phone" in data:
        svc.rescore(lead)
    if prio:
        lead.priority = prio
    if "status" in data and data["status"] != old_status:
        audit(db, user.organization_id, "lead.status_changed", f"Status {old_status} -> {data['status']}", entity_type="lead", entity_id=lead.id, actor_id=user.id)
    audit(db, user.organization_id, "lead.updated", "Lead updated", entity_type="lead", entity_id=lead.id, actor_id=user.id, meta={"fields": ",".join(data)})
    db.commit()
    return lead


@router.post("/{lead_id}/archive", response_model=LeadOut)
def archive(lead_id: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    lead.is_archived = True
    audit(db, user.organization_id, "lead.archived", "Lead archived", entity_type="lead", entity_id=lead.id, actor_id=user.id)
    db.commit()
    return lead


@router.post("/{lead_id}/restore", response_model=LeadOut)
def restore(lead_id: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    lead.is_archived = False
    audit(db, user.organization_id, "lead.restored", "Lead restored", entity_type="lead", entity_id=lead.id, actor_id=user.id)
    db.commit()
    return lead


@router.post("/{lead_id}/rescore", response_model=LeadOut)
def rescore(lead_id: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    svc.rescore(lead)
    audit(db, user.organization_id, "lead.rescored", f"Lead rescored: {lead.score}", entity_type="lead", entity_id=lead.id, actor_id=user.id)
    db.commit()
    return lead


@router.get("/{lead_id}/activity", response_model=list[ActivityOut])
def activity(lead_id: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    rows = db.scalars(select(AuditLog).where(AuditLog.organization_id == user.organization_id, AuditLog.entity_type == "lead",
                                             AuditLog.entity_id == lead_id).order_by(AuditLog.created_at.desc()).limit(200)).all()
    actors = {u.id: u.full_name for u in db.scalars(select(User).where(User.organization_id == user.organization_id))}
    return [ActivityOut(id=r.id, type=r.action, message=r.message, created_at=r.created_at, actor=actors.get(r.actor_id)) for r in rows]


@router.get("/{lead_id}/matches", response_model=list[MatchOut])
def lead_matches(lead_id: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    lead = get_or_404(db, Lead, lead_id, user.organization_id, "Lead")
    ms = match_lead(db, lead, store=user.role != "analyst")  # analysts are read-only: compute without persisting
    db.commit()
    return ms
