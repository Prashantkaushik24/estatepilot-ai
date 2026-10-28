"""AI email pipeline: normalize -> dedupe -> classify -> extract -> validate -> lead upsert -> score ->
property match -> reply draft -> follow-up task -> run record + audit. Honors pause / kill switch / rule toggles."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.nlp import format_inr
from app.agents.providers import DemoProvider, ProviderError, get_provider
from app.models import AIProcessingRun, AutomationRule, Email, EmailDraft, Lead, Organization, Task
from app.services import leads as lead_svc
from app.services.audit import audit, notify
from app.services.emails import content_hash
from app.services.matching import match_lead

log = logging.getLogger("estatepilot.pipeline")
NO_LEAD_CLASSES = {"spam", "other"}


class AutomationPaused(Exception):
    pass


@dataclass
class Result:
    email: Email
    run: AIProcessingRun
    steps: list = field(default_factory=list)
    lead: Lead | None = None
    lead_created: bool = False
    matches: list = field(default_factory=list)
    draft: EmailDraft | None = None
    task: Task | None = None


def rules_map(db: Session, org_id: str) -> dict[str, AutomationRule]:
    return {r.key: r for r in db.scalars(select(AutomationRule).where(AutomationRule.organization_id == org_id))}


def assert_running(org: Organization):
    if org.paused or org.kill_switch:
        raise AutomationPaused("automation paused")


def make_draft(db, org, email, lead, matches, provider, force_new_text=True, steps=None) -> EmailDraft | None:
    ex = email.extraction or {}
    ctx = {"name": (lead.full_name if lead else ex.get("customer_name") or email.sender_name), "subject": email.subject,
           "summary": email.summary, "intent": ex.get("intent"), "missing": ex.get("missing_information", []),
           "matches": [{"title": m.property.title, "location": m.property.location, "price_display": format_inr(m.property.price)} for m in matches]}
    demo_used = provider.info.is_demo
    try:
        d = provider.draft(ctx)
    except ProviderError as e:
        if not org.demo_mode:
            raise
        log.warning("draft fallback to demo: %s", e)
        d, demo_used = DemoProvider().draft(ctx), True
    cur = email.draft
    if cur and cur.status in ("approved", "sending", "sent"):
        return cur
    if cur:
        cur.subject, cur.body, cur.status, cur.is_demo_ai, cur.error = d.subject, d.body, "draft", demo_used, None
        cur.approved_by = cur.approved_at = None
        return cur
    row = EmailDraft(organization_id=org.id, email_id=email.id, lead_id=lead.id if lead else None, subject=d.subject,
                     body=d.body, status="draft", is_demo_ai=demo_used)
    db.add(row)
    db.flush()
    db.refresh(email, ["drafts"])
    return row


def process_email(db: Session, org: Organization, email: Email, actor_id: str | None = None) -> Result:
    assert_running(org)
    rules = rules_map(db, org.id)
    t0 = time.perf_counter()
    steps: list[dict] = []

    def step(name, status, detail=""):
        steps.append({"name": name, "status": status, "detail": detail})

    def rule_on(key):
        r = rules.get(key)
        return r is None or r.enabled

    def touch(key, result):
        r = rules.get(key)
        if r:
            r.run_count += 1
            r.last_run_at = datetime.now(timezone.utc)
            r.last_result = result[:300]

    run = AIProcessingRun(organization_id=org.id, email_id=email.id, status="success", provider="demo", is_demo=True, steps=[])
    db.add(run)
    res = Result(email=email, run=run, steps=steps)

    def finish(status):
        run.status, run.steps = status, list(steps)
        run.duration_ms = int((time.perf_counter() - t0) * 1000)
        db.flush()
        db.refresh(email)
        return res

    if not rule_on("process_incoming_emails"):
        email.processing_status = "skipped"
        step("process_incoming_emails", "skipped", "Rule disabled")
        audit(db, org.id, "email.skipped", "Email processing skipped: rule disabled", entity_type="email", entity_id=email.id, actor_id=actor_id)
        return finish("partial")

    email.processing_status, email.error = "processing", None
    step("normalize", "ok", f"{len(email.body)} chars")
    other = db.scalar(select(Email.id).where(Email.organization_id == org.id, Email.content_hash == content_hash(email.sender_email, email.subject, email.body), Email.id != email.id))
    step("dedupe", "ok" if not other else "failed", "Unique content hash" if not other else "Duplicate content of another email")

    # --- AI analysis (classify + extract + validate) ---
    try:
        provider = get_provider(org.demo_mode)
        try:
            analysis = provider.analyze(email.sender_name, email.subject, email.body, email.sender_email)
        except ProviderError as e:
            if provider.info.is_demo or not org.demo_mode:
                raise
            res_attempts = provider.attempts
            log.warning("AI provider failed, DEMO_MODE fallback: %s", e)
            step("ai_fallback", "ok", "Provider failed; fell back to demo provider (demo mode on)")
            provider = DemoProvider()
            provider.attempts = res_attempts
            analysis = provider.analyze(email.sender_name, email.subject, email.body, email.sender_email)
    except ProviderError as e:
        email.processing_status, email.error = "failed", str(e)[:500]
        run.provider = (get_settings_provider() or "unknown")
        run.is_demo, run.error, run.attempts = False, str(e)[:500], e.attempts
        step("classify", "failed", "AI provider error")
        audit(db, org.id, "email.failed", "Email processing failed: AI provider error", entity_type="email", entity_id=email.id,
              level="error", actor_id=actor_id, meta={"error": str(e)[:200]})
        notify(db, org.id, "Email processing failed", f"Could not process email '{email.subject[:80]}'", "error", "email", email.id)
        return finish("failed")

    run.provider, run.model, run.is_demo = provider.info.name, provider.info.model, provider.info.is_demo
    run.attempts = getattr(provider, "attempts", 1)
    email.is_demo_ai = provider.info.is_demo
    email.classification, email.summary, email.priority = analysis.classification, analysis.summary, analysis.priority
    ex = analysis.extraction.model_dump()
    ex["sender_email"] = ex.get("sender_email") or email.sender_email
    email.extraction = ex
    step("classify", "ok", analysis.classification)
    step("extract", "ok", f"{sum(1 for k, v in ex.items() if v not in (None, [], ''))} fields")
    step("validate", "ok", "Structured output validated")

    lead = None
    cls = analysis.classification
    if rule_on("create_update_leads") and cls not in NO_LEAD_CLASSES:
        lead, created = lead_svc.upsert_from_extraction(db, org.id, ex, email.sender_email, "gmail" if email.source == "gmail" else ("demo" if email.source == "demo" else "email"),
                                                        cls, is_demo=email.is_demo)
        res.lead, res.lead_created = lead, created
        email.lead_id = lead.id
        if email.thread_id:
            from app.models import EmailThread
            t = db.get(EmailThread, email.thread_id)
            if t:
                t.lead_id = lead.id
        step("lead", "ok", "Created new lead" if created else "Updated existing lead (no duplicate)")
        step("score", "ok", f"{lead.score} ({lead.priority})")
        audit(db, org.id, "lead.created" if created else "lead.updated", f"Lead {'created' if created else 'updated'} from email, score {lead.score}",
              entity_type="lead", entity_id=lead.id, actor_id=actor_id, meta={"email_id": email.id, "score": lead.score})
        if created and lead.priority == "hot":
            notify(db, org.id, "New hot lead", f"{lead.full_name} scored {lead.score}", "lead", "lead", lead.id)
        touch("create_update_leads", f"{'created' if created else 'updated'} lead {lead.id[:8]}")
        res.matches = match_lead(db, lead)
        step("match", "ok", f"{len(res.matches)} matching properties" if res.matches else "No matching available properties")
    else:
        why = "Rule disabled" if cls not in NO_LEAD_CLASSES else f"Not a lead ({cls})"
        step("lead", "skipped", why)
        step("score", "skipped", why)
        step("match", "skipped", why)

    status = "success"
    if rule_on("generate_reply_drafts") and cls not in ("spam",) and (lead or cls != "other"):
        try:
            res.draft = make_draft(db, org, email, lead, res.matches, provider)
            step("draft", "ok", f"Draft {res.draft.status}")
            audit(db, org.id, "draft.created", "Reply draft generated (not sent)", entity_type="draft", entity_id=res.draft.id, actor_id=actor_id,
                  meta={"email_id": email.id})
            touch("generate_reply_drafts", "draft ready")
        except ProviderError as e:
            status = "partial"
            step("draft", "failed", "AI provider error while drafting")
            audit(db, org.id, "draft.failed", "Draft generation failed", entity_type="email", entity_id=email.id, level="error", meta={"error": str(e)[:200]})
    else:
        step("draft", "skipped", "Rule disabled or not applicable")

    if lead and rule_on("create_followup_tasks"):
        existing = db.scalar(select(Task).where(Task.organization_id == org.id, Task.lead_id == lead.id, Task.status == "pending", Task.source == "ai"))
        if existing:
            res.task = existing
            step("task", "skipped", "Pending AI follow-up already exists for lead (deduplicated)")
        else:
            res.task = Task(organization_id=org.id, lead_id=lead.id, owner_id=lead.assigned_agent_id, source="ai", status="pending",
                            title=f"Follow up with {lead.full_name}", priority=lead.priority, due_at=lead_svc.followup_due(lead),
                            description=f"Review and approve reply draft; qualify lead. Score {lead.score}.", is_demo=email.is_demo)
            db.add(res.task)
            db.flush()
            lead.next_follow_up_at = res.task.due_at
            step("task", "ok", "Follow-up task created")
            audit(db, org.id, "task.created", "AI follow-up task created", entity_type="task", entity_id=res.task.id, actor_id=actor_id, meta={"lead_id": lead.id})
            touch("create_followup_tasks", "task created")
    else:
        step("task", "skipped", "No lead or rule disabled")

    email.processing_status = "processed"
    touch("process_incoming_emails", f"{cls}")
    audit(db, org.id, "email.processed", f"Email processed as {cls}", entity_type="email", entity_id=email.id, actor_id=actor_id,
          meta={"provider": run.provider, "demo": run.is_demo, "lead_id": lead.id if lead else None})
    return finish(status)


def get_settings_provider():
    from app.core.config import get_settings
    return get_settings().AI_PROVIDER.lower()
