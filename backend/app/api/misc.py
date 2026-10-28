from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.providers import ai_configured
from app.api.helpers import get_or_404
from app.core.config import get_settings
from app.core.deps import PageParams, admin_only, any_user, get_org, manager_up, paginate
from app.core.security import verify_state
from app.db.session import get_db
from app.integrations import gmail
from app.models import AIProcessingRun, AuditLog, AutomationRule, Notification, Organization, User
from app.schemas.common import Page
from app.schemas.entities import AIRunOut, AuditOut, KillIn, NotificationOut, RuleOut, RulePatch, SettingsPatch
from app.services import analytics
from app.services.audit import audit

router = APIRouter()


# ---- automation ----
def _state(org):
    return {"paused": org.paused, "kill_switch": org.kill_switch, "sending_enabled": get_settings().SENDING_ENABLED}


@router.get("/automation/rules", response_model=list[RuleOut], tags=["automation"])
def rules(user: User = Depends(any_user), db: Session = Depends(get_db)):
    return db.scalars(select(AutomationRule).where(AutomationRule.organization_id == user.organization_id).order_by(AutomationRule.key)).all()


@router.patch("/automation/rules/{rid}", response_model=RuleOut, tags=["automation"])
def patch_rule(rid: str, body: RulePatch, user: User = Depends(manager_up), db: Session = Depends(get_db)):
    r = get_or_404(db, AutomationRule, rid, user.organization_id, "Rule")
    r.enabled = body.enabled
    audit(db, user.organization_id, "automation.rule_toggled", f"Rule {r.key} {'enabled' if r.enabled else 'disabled'}", entity_type="rule", entity_id=r.id, actor_id=user.id)
    db.commit()
    return r


@router.get("/automation/state", tags=["automation"])
def state(user: User = Depends(any_user), org: Organization = Depends(get_org)):
    return _state(org)


@router.post("/automation/pause", tags=["automation"])
def pause(user: User = Depends(manager_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    org.paused = True
    audit(db, org.id, "automation.paused", "Automation paused", actor_id=user.id, level="warning")
    db.commit()
    return _state(org)


@router.post("/automation/resume", tags=["automation"])
def resume(user: User = Depends(manager_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    org.paused = False
    audit(db, org.id, "automation.resumed", "Automation resumed", actor_id=user.id)
    db.commit()
    return _state(org)


@router.post("/automation/kill-switch", tags=["automation"])
def kill(body: KillIn, user: User = Depends(admin_only), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    org.kill_switch = body.enabled
    audit(db, org.id, "automation.kill_switch", f"Kill switch {'ON' if body.enabled else 'off'}", actor_id=user.id, level="warning" if body.enabled else "info")
    db.commit()
    return _state(org)


@router.get("/automation/runs", response_model=list[AIRunOut], tags=["automation"])
def runs(limit: int = Query(50, ge=1, le=200), user: User = Depends(any_user), db: Session = Depends(get_db)):
    return db.scalars(select(AIProcessingRun).where(AIProcessingRun.organization_id == user.organization_id)
                      .order_by(AIProcessingRun.created_at.desc()).limit(limit)).all()


# ---- audit / notifications / settings ----
@router.get("/audit", response_model=Page[AuditOut], tags=["audit"])
def audit_list(pp: PageParams = Depends(), action: str | None = None, entity_type: str | None = None, level: str | None = None,
               user: User = Depends(any_user), db: Session = Depends(get_db)):
    stmt = select(AuditLog).where(AuditLog.organization_id == user.organization_id)
    for col, v in ((AuditLog.action, action), (AuditLog.entity_type, entity_type), (AuditLog.level, level)):
        if v:
            stmt = stmt.where(col == v)
    page = paginate(db, stmt, pp, AuditLog, {"created_at", "action", "level"})
    page["items"] = [AuditOut(id=r.id, action=r.action, entity_type=r.entity_type, entity_id=r.entity_id, message=r.message, level=r.level,
                              actor_id=r.actor_id, metadata=r.meta or {}, created_at=r.created_at) for r in page["items"]]
    return page


@router.get("/notifications", response_model=list[NotificationOut], tags=["notifications"])
def notifications(user: User = Depends(any_user), db: Session = Depends(get_db)):
    return db.scalars(select(Notification).where(Notification.organization_id == user.organization_id,
                                                 (Notification.user_id.is_(None)) | (Notification.user_id == user.id))
                      .order_by(Notification.created_at.desc()).limit(100)).all()


@router.post("/notifications/{nid}/read", response_model=NotificationOut, tags=["notifications"])
def read_notification(nid: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    n = get_or_404(db, Notification, nid, user.organization_id, "Notification")  # marking own-read state is not a data write
    n.is_read = True
    db.commit()
    return n


def _settings(org):
    s = get_settings()
    return {"demo_mode": org.demo_mode, "sending_enabled": s.SENDING_ENABLED, "default_agent_id": org.default_agent_id,
            "timezone": s.TIMEZONE, "theme": org.theme}


@router.get("/settings", tags=["settings"])
def get_settings_ep(user: User = Depends(any_user), org: Organization = Depends(get_org)):
    return _settings(org)


@router.patch("/settings", tags=["settings"])
def patch_settings(body: SettingsPatch, user: User = Depends(manager_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    if body.demo_mode is not None:
        org.demo_mode = body.demo_mode
        audit(db, org.id, "settings.updated", f"demo_mode set to {body.demo_mode}", actor_id=user.id)
    db.commit()
    return _settings(org)


# ---- analytics ----
@router.get("/dashboard/metrics", tags=["analytics"])
def dash(user: User = Depends(any_user), db: Session = Depends(get_db)):
    return analytics.metrics(db, user.organization_id)


@router.get("/analytics/charts", tags=["analytics"])
def charts(user: User = Depends(any_user), db: Session = Depends(get_db)):
    return analytics.charts(db, user.organization_id)


@router.get("/analytics/export/{kind}.csv", tags=["analytics"])
def export(kind: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    if kind not in ("leads", "emails", "tasks", "properties", "fact_leads"):
        raise HTTPException(404, "Unknown export")
    return Response(analytics.export(db, user.organization_id, kind), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={kind}.csv"})


@router.get("/analytics/powerbi", tags=["analytics"])
def powerbi(user: User = Depends(any_user)):
    s = get_settings()
    if s.POWERBI_EMBED_URL and s.POWERBI_REPORT_ID and s.POWERBI_EMBED_ENABLED:
        return {"configured": True, "embed_url": s.POWERBI_EMBED_URL, "report_id": s.POWERBI_REPORT_ID,
                "message": "Power BI embed configured. Embed tokens must be issued by a separate secure service; none is returned here."}
    return {"configured": False, "message": "Power BI not configured. See powerbi/README.md; use CSV exports or SQL views meanwhile."}


# ---- integrations ----
@router.get("/integrations/status", tags=["integrations"])
def status(user: User = Depends(any_user), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    s = get_settings()
    acc = gmail.get_account(db, org.id)
    p = s.AI_PROVIDER.lower()
    model = {"openai": s.OPENAI_MODEL, "gemini": s.GEMINI_MODEL}.get(p, "demo-rules-v1")
    return {"backend": "ok", "ai": {"provider": p, "configured": ai_configured(), "demo_mode": org.demo_mode, "model": model},
            "gmail": {"configured": gmail.configured(), "connected": bool(acc), "account_email": acc.account_email if acc else None,
                      "last_sync_at": acc.last_sync_at.isoformat().replace("+00:00", "Z") if acc and acc.last_sync_at else None},
            "powerbi": {"configured": bool(s.POWERBI_EMBED_URL and s.POWERBI_REPORT_ID)},
            "sending_enabled": s.SENDING_ENABLED, "kill_switch": org.kill_switch, "paused": org.paused}


@router.get("/integrations/gmail/auth-url", tags=["integrations"])
def gmail_auth_url(user: User = Depends(admin_only)):
    try:
        return {"url": gmail.auth_url(user.organization_id, user.id)}
    except gmail.GmailError as e:
        raise HTTPException(400, str(e))


@router.get("/integrations/gmail/callback", tags=["integrations"])
def gmail_callback(code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    base = get_settings().FRONTEND_URL.rstrip("/") + "/settings?gmail="
    if error or not code or not state:
        return RedirectResponse(base + "error")
    try:
        verify_state(state)
        acc = gmail.handle_callback(db, code, state)
        audit(db, acc.organization_id, "gmail.connected", "Gmail account connected", entity_type="email_account", entity_id=acc.id)
        db.commit()
        return RedirectResponse(base + "connected")
    except Exception:
        db.rollback()
        return RedirectResponse(base + "error")


@router.post("/integrations/gmail/sync", tags=["integrations"])
def gmail_sync(user: User = Depends(manager_up), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    from app.agents import pipeline
    try:
        emails, skipped = gmail.sync(db, org.id)
    except gmail.GmailError as e:
        raise HTTPException(409, str(e))
    for e in emails:
        if not (org.paused or org.kill_switch):
            pipeline.process_email(db, org, e, actor_id=user.id)
    audit(db, org.id, "gmail.synced", f"Gmail sync: {len(emails)} imported, {skipped} duplicates", actor_id=user.id)
    db.commit()
    return {"imported": len(emails), "skipped_duplicates": skipped}


@router.post("/integrations/gmail/disconnect", tags=["integrations"])
def gmail_disconnect(user: User = Depends(admin_only), org: Organization = Depends(get_org), db: Session = Depends(get_db)):
    gmail.disconnect(db, org.id)
    audit(db, org.id, "gmail.disconnected", "Gmail disconnected", actor_id=user.id)
    db.commit()
    return {"connected": False}


# ---- demo reset ----
@router.post("/admin/reset-demo", tags=["admin"])
def reset_demo(body: dict, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Wipe this org's business data (emails, leads, tasks, ...) and restore the original demo data.
    Keeps users, automation rules and the Gmail account link. Requires {"confirm": true}."""
    from sqlalchemy import delete

    from app.db.seed import populate_demo
    from app.models import (AIProcessingRun, AuditLog, Email, EmailDraft, EmailThread, Lead, Notification,
                            Property, PropertyMatch, Task)
    if body.get("confirm") is not True:
        raise HTTPException(400, "confirm must be true")
    oid = user.organization_id
    for m in (PropertyMatch, EmailDraft, AIProcessingRun, Task, Email, EmailThread, Lead, Property, Notification, AuditLog):
        db.execute(delete(m).where(m.organization_id == oid))
    org = db.get(Organization, oid)
    org.paused = False
    org.kill_switch = False
    agent = db.scalar(select(User).where(User.organization_id == oid, User.role == "agent")) or user
    populate_demo(db, org, agent)
    audit(db, oid, "admin.demo_reset", "Demo data reset to original", actor_id=user.id)
    db.commit()
    return {"status": "ok", "message": "Demo data restored"}
