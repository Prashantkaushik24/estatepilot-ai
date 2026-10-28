from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AutomationRule, Organization

DEFAULT_RULES = [
    ("process_incoming_emails", "Process incoming emails", "Classify and extract data from new emails with AI."),
    ("create_update_leads", "Create / update leads", "Create or update leads (deduplicated by email/phone) from processed emails."),
    ("create_followup_tasks", "Create follow-up tasks", "Create one pending follow-up task per lead."),
    ("generate_reply_drafts", "Generate reply drafts", "Draft replies for review. Never sent without approval."),
]


def create_org(db: Session, name: str) -> Organization:
    org = Organization(name=name, demo_mode=get_settings().DEMO_MODE)
    db.add(org)
    db.flush()
    ensure_rules(db, org.id)
    return org


def ensure_rules(db: Session, org_id: str):
    have = set(db.scalars(select(AutomationRule.key).where(AutomationRule.organization_id == org_id)))
    for key, name, desc in DEFAULT_RULES:
        if key not in have:
            db.add(AutomationRule(organization_id=org_id, key=key, name=name, description=desc, enabled=True))
