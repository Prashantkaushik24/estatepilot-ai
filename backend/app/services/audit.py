from sqlalchemy.orm import Session

from app.models import AuditLog, Notification

_SENSITIVE = ("token", "secret", "password", "body", "authorization", "api_key", "code")


def _clean(meta: dict | None) -> dict:
    out = {}
    for k, v in (meta or {}).items():
        if any(s in k.lower() for s in _SENSITIVE):
            continue
        out[k] = v if isinstance(v, (int, float, bool, type(None))) else str(v)[:200]
    return out


def audit(db: Session, org_id: str, action: str, message: str, *, entity_type: str | None = None,
          entity_id: str | None = None, level: str = "info", actor_id: str | None = None, meta: dict | None = None):
    row = AuditLog(organization_id=org_id, action=action, message=message[:1000], entity_type=entity_type,
                   entity_id=entity_id, level=level, actor_id=actor_id, meta=_clean(meta))
    db.add(row)
    return row


def notify(db: Session, org_id: str, title: str, message: str = "", type_: str = "info",
           entity_type: str | None = None, entity_id: str | None = None, user_id: str | None = None):
    db.add(Notification(organization_id=org_id, user_id=user_id, title=title[:300], message=message[:1000],
                        type=type_, entity_type=entity_type, entity_id=entity_id))
