from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.helpers import get_or_404
from app.core.deps import PageParams, agent_up, any_user, paginate
from app.db.session import get_db
from app.models import Lead, Task, User
from app.schemas.common import Page
from app.schemas.entities import TaskIn, TaskOut, TaskPatch
from app.services.audit import audit

router = APIRouter(prefix="/tasks", tags=["tasks"])
SORTABLE = {"created_at", "due_at", "priority", "status", "title"}


def _check_refs(db, org_id, lead_id, owner_id):
    if lead_id:
        get_or_404(db, Lead, lead_id, org_id, "Lead")
    if owner_id:
        u = db.get(User, owner_id)
        if not u or u.organization_id != org_id:
            raise HTTPException(422, "owner_id not in organization")


@router.get("", response_model=Page[TaskOut])
def list_tasks(pp: PageParams = Depends(), status: str | None = None, lead_id: str | None = None, overdue: bool | None = None,
               owner_id: str | None = None, user: User = Depends(any_user), db: Session = Depends(get_db)):
    stmt = select(Task).where(Task.organization_id == user.organization_id)
    if status:
        stmt = stmt.where(Task.status == status)
    if lead_id:
        stmt = stmt.where(Task.lead_id == lead_id)
    if owner_id:
        stmt = stmt.where(Task.owner_id == owner_id)
    now = datetime.now(timezone.utc)
    if overdue is True:
        stmt = stmt.where(Task.status == "pending", Task.due_at < now)
    elif overdue is False:
        stmt = stmt.where(~((Task.status == "pending") & (Task.due_at < now)))
    if pp.q:
        stmt = stmt.where(Task.title.ilike("%" + pp.q.replace("%", "") + "%"))
    return paginate(db, stmt, pp, Task, SORTABLE, "due_at")


@router.get("/reminders", response_model=list[TaskOut])
def reminders(user: User = Depends(any_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    return db.scalars(select(Task).where(Task.organization_id == user.organization_id, Task.status == "pending",
                                         or_(Task.due_at <= now, Task.reminder_at <= now)).order_by(Task.due_at)).unique().all()


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskIn, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    body.lead_id = body.lead_id or None
    _check_refs(db, user.organization_id, body.lead_id, body.owner_id)
    t = Task(organization_id=user.organization_id, source="manual", owner_id=body.owner_id or user.id, **body.model_dump(exclude={"owner_id"}))
    db.add(t)
    db.flush()
    audit(db, user.organization_id, "task.created", "Task created", entity_type="lead" if t.lead_id else "task", entity_id=t.lead_id or t.id, actor_id=user.id, meta={"task_id": t.id})
    db.commit()
    db.refresh(t)
    return t


@router.get("/{tid}", response_model=TaskOut)
def get_task(tid: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    return get_or_404(db, Task, tid, user.organization_id, "Task")


@router.patch("/{tid}", response_model=TaskOut)
def patch_task(tid: str, body: TaskPatch, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    t = get_or_404(db, Task, tid, user.organization_id, "Task")
    data = body.model_dump(exclude_unset=True)
    _check_refs(db, user.organization_id, data.get("lead_id"), data.get("owner_id"))
    for k, v in data.items():
        if v is None and k in ("title", "status", "due_at", "priority"):
            raise HTTPException(422, f"{k} cannot be null")
        setattr(t, k, v)
    if data.get("status") == "completed" and not t.completed_at:
        t.completed_at = datetime.now(timezone.utc)
    elif data.get("status") in ("pending", "cancelled"):
        t.completed_at = None
    audit(db, user.organization_id, "task.updated", "Task updated", entity_type="task", entity_id=t.id, actor_id=user.id)
    db.commit()
    return t


@router.post("/{tid}/complete", response_model=TaskOut)
def complete(tid: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    t = get_or_404(db, Task, tid, user.organization_id, "Task")
    t.status, t.completed_at = "completed", t.completed_at or datetime.now(timezone.utc)
    audit(db, user.organization_id, "task.completed", "Task completed", entity_type="task", entity_id=t.id, actor_id=user.id)
    db.commit()
    return t


@router.delete("/{tid}", status_code=204)
def delete_task(tid: str, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    t = get_or_404(db, Task, tid, user.organization_id, "Task")
    audit(db, user.organization_id, "task.deleted", "Task deleted", entity_type="task", entity_id=t.id, actor_id=user.id)
    db.delete(t)
    db.commit()
