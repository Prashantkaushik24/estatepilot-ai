from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.agents import pipeline
from app.agents.providers import ProviderError, get_provider
from app.api.helpers import get_or_404, result_out
from app.core.config import get_settings
from app.core.deps import PageParams, agent_up, any_user, get_org, like, paginate
from app.db.session import get_db
from app.integrations import gmail
from app.models import Email, EmailDraft, Lead, Organization, User
from app.schemas.common import Page
from app.schemas.entities import DraftIn, DraftOut, EmailImport, EmailOut, EmailPatch, ProcessResult, SendIn
from app.services.audit import audit
from app.services.emails import DEMO_EMAILS, DuplicateEmail, create_email
from app.services.matching import match_lead
from app.api.helpers import result_out  # noqa

router = APIRouter(tags=["emails"])
SORTABLE = {"created_at", "received_at", "subject", "sender_email", "priority", "classification", "processing_status"}


def _process(db, org, email, user) -> ProcessResult:
    try:
        r = pipeline.process_email(db, org, email, actor_id=user.id)
    except pipeline.AutomationPaused:
        db.rollback()
        raise HTTPException(409, "automation paused")
    db.commit()
    return result_out(r)


@router.get("/emails", response_model=Page[EmailOut])
def list_emails(pp: PageParams = Depends(), classification: str | None = None, processing_status: str | None = None,
                lead_id: str | None = None, priority: str | None = None, user: User = Depends(any_user), db: Session = Depends(get_db)):
    stmt = select(Email).where(Email.organization_id == user.organization_id)
    for col, val in ((Email.classification, classification), (Email.processing_status, processing_status), (Email.lead_id, lead_id), (Email.priority, priority)):
        if val:
            stmt = stmt.where(col == val)
    if pp.q:
        p = like(pp.q)
        stmt = stmt.where(or_(Email.subject.ilike(p, escape="\\"), Email.sender_email.ilike(p, escape="\\"), Email.sender_name.ilike(p, escape="\\")))
    return paginate(db, stmt, pp, Email, SORTABLE, "-received_at")


@router.post("/emails/import", response_model=ProcessResult)
def import_email(body: EmailImport, user: User = Depends(agent_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    try:
        e = create_email(db, org.id, sender_email=body.sender_email, sender_name=body.sender_name, subject=body.subject, body=body.body,
                         received_at=body.received_at, source=body.source)
    except DuplicateEmail as d:
        return JSONResponse(status_code=409, content={"detail": "duplicate", "existing_email_id": d.existing_id})
    audit(db, org.id, "email.imported", "Email imported", entity_type="email", entity_id=e.id, actor_id=user.id, meta={"source": body.source})
    if body.process and not (org.paused or org.kill_switch):
        return _process(db, org, e, user)
    db.commit()
    db.refresh(e)
    detail = "automation paused" if body.process else "process=false"
    return ProcessResult(email=e, steps=[{"name": "process", "status": "skipped", "detail": detail}])


@router.post("/emails/demo")
def import_demo(user: User = Depends(agent_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    created = []
    for d in DEMO_EMAILS:
        try:
            e = create_email(db, org.id, received_at=None, source="demo", is_demo=True, **d)
        except DuplicateEmail:
            continue
        created.append(e)
        if not (org.paused or org.kill_switch):
            pipeline.process_email(db, org, e, actor_id=user.id)
    audit(db, org.id, "email.demo_imported", f"{len(created)} demo emails imported", actor_id=user.id)
    db.commit()
    return {"created": len(created), "emails": [EmailOut.model_validate(e) for e in created]}


@router.get("/emails/{eid}", response_model=EmailOut)
def get_email(eid: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    return get_or_404(db, Email, eid, user.organization_id, "Email")


@router.patch("/emails/{eid}", response_model=EmailOut)
def patch_email(eid: str, body: EmailPatch, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    e = get_or_404(db, Email, eid, user.organization_id, "Email")
    if body.is_read is not None:
        e.is_read = body.is_read
    db.commit()
    return e


@router.post("/emails/{eid}/process", response_model=ProcessResult)
def process(eid: str, user: User = Depends(agent_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    e = get_or_404(db, Email, eid, user.organization_id, "Email")
    return _process(db, org, e, user)


# ---- drafts ----
def _draft_for(db, org_id, eid) -> tuple[Email, EmailDraft | None]:
    e = get_or_404(db, Email, eid, org_id, "Email")
    return e, e.draft


@router.get("/emails/{eid}/draft", response_model=DraftOut)
def get_draft(eid: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    _, d = _draft_for(db, user.organization_id, eid)
    if not d:
        raise HTTPException(404, "No draft for this email")
    return d


@router.put("/emails/{eid}/draft", response_model=DraftOut)
def put_draft(eid: str, body: DraftIn, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    e, d = _draft_for(db, user.organization_id, eid)
    if d and d.status in ("sent", "sending"):
        raise HTTPException(409, "Draft already sent")
    if d:
        d.subject, d.body, d.status, d.approved_by, d.approved_at = body.subject, body.body, "draft", None, None  # edits require re-approval
    else:
        d = EmailDraft(organization_id=user.organization_id, email_id=e.id, lead_id=e.lead_id, subject=body.subject, body=body.body, is_demo_ai=False)
        db.add(d)
        db.flush()
    audit(db, user.organization_id, "draft.edited", "Draft saved", entity_type="draft", entity_id=d.id, actor_id=user.id)
    db.commit()
    return d


@router.post("/emails/{eid}/draft/regenerate", response_model=DraftOut)
def regenerate(eid: str, user: User = Depends(agent_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    e = get_or_404(db, Email, eid, user.organization_id, "Email")
    try:
        pipeline.assert_running(org)
    except pipeline.AutomationPaused:
        raise HTTPException(409, "automation paused")
    if e.draft and e.draft.status in ("sent", "sending", "approved"):
        raise HTTPException(409, f"Draft is {e.draft.status}; cannot regenerate")
    lead = db.get(Lead, e.lead_id) if e.lead_id else None
    ms = match_lead(db, lead) if lead else []
    try:
        d = pipeline.make_draft(db, org, e, lead, ms, get_provider(org.demo_mode))
    except ProviderError as ex:
        raise HTTPException(502, f"AI provider error: {str(ex)[:150]}")
    audit(db, org.id, "draft.regenerated", "Draft regenerated", entity_type="draft", entity_id=d.id, actor_id=user.id)
    db.commit()
    return d


@router.post("/drafts/{did}/approve", response_model=DraftOut)
def approve(did: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    d = get_or_404(db, EmailDraft, did, user.organization_id, "Draft")
    if d.status in ("sent", "sending"):
        raise HTTPException(409, "Draft already sent")
    if d.status == "discarded":
        raise HTTPException(409, "Draft was discarded")
    if d.status != "approved":
        d.status, d.approved_by, d.approved_at = "approved", user.id, datetime.now(timezone.utc)
        audit(db, user.organization_id, "draft.approved", "Draft approved (not sent)", entity_type="draft", entity_id=d.id, actor_id=user.id)
        db.commit()
    return d


@router.post("/drafts/{did}/send", response_model=DraftOut)
def send(did: str, body: SendIn, user: User = Depends(agent_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    """Send only if: draft approved, kill switch off, SENDING_ENABLED, Gmail connected, explicit confirmation.
    Marked sent only after provider confirmation. Duplicate sends -> 409 (atomic claim)."""
    d = get_or_404(db, EmailDraft, did, user.organization_id, "Draft")
    if d.status in ("sent", "sending"):
        raise HTTPException(409, "Draft already sent (duplicate send blocked)")
    if d.status != "approved":
        raise HTTPException(409, "Draft must be approved before sending")
    if org.kill_switch:
        raise HTTPException(403, "Kill switch is on; sending is disabled")
    if not get_settings().SENDING_ENABLED:
        raise HTTPException(403, "Sending is disabled (SENDING_ENABLED=false)")
    if not body.confirm:
        raise HTTPException(422, "confirm must be true")
    email = db.get(Email, d.email_id)
    if body.confirm_recipient.strip().lower() != email.sender_email.lower():
        raise HTTPException(422, "confirm_recipient does not match the draft recipient")
    if not gmail.get_account(db, org.id):
        raise HTTPException(409, "Gmail is not connected")
    claimed = db.execute(update(EmailDraft).where(EmailDraft.id == d.id, EmailDraft.status == "approved").values(status="sending")).rowcount
    db.commit()
    if claimed != 1:
        raise HTTPException(409, "Draft already sent (duplicate send blocked)")
    try:
        mid = gmail.send(db, org.id, email.sender_email, d.subject, d.body)
    except Exception as ex:
        d.status, d.error = "failed", str(ex)[:300]
        audit(db, org.id, "draft.send_failed", "Send failed", entity_type="draft", entity_id=d.id, level="error", actor_id=user.id)
        db.commit()
        raise HTTPException(502, "Send failed; draft not marked as sent")
    d.status, d.sent_at, d.provider_message_id = "sent", datetime.now(timezone.utc), mid
    audit(db, org.id, "draft.sent", "Draft sent via Gmail", entity_type="draft", entity_id=d.id, actor_id=user.id, meta={"provider_message_id": mid})
    db.commit()
    return d
