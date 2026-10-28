from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents.pipeline import Result
from app.schemas.entities import ProcessResult


def get_or_404(db: Session, model, id_: str, org_id: str, label: str | None = None):
    obj = db.get(model, id_)
    if not obj or obj.organization_id != org_id:
        raise HTTPException(404, f"{label or model.__name__} not found")
    return obj


def result_out(r: Result) -> ProcessResult:
    return ProcessResult(email=r.email, lead=r.lead, lead_created=r.lead_created, matches=r.matches, draft=r.draft,
                         task=r.task, run=r.run, steps=r.steps)
