from typing import Callable

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Organization, User

bearer = HTTPBearer(auto_error=False)
ROLE_LEVEL = {"analyst": 1, "agent": 2, "manager": 3, "admin": 4}


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        data = decode_access_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User inactive or not found")
    return user


def require_role(minimum: str) -> Callable:
    """Server-side RBAC: admin > manager > agent > analyst (read-only)."""
    def dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL[minimum]:
            raise HTTPException(403, f"Requires role '{minimum}' or higher")
        return user
    return dep


any_user = require_role("analyst")
agent_up = require_role("agent")
manager_up = require_role("manager")
admin_only = require_role("admin")


def get_org(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Organization:
    return db.get(Organization, user.organization_id)


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
                 q: str | None = None, sort: str | None = None):
        self.page, self.page_size, self.q, self.sort = page, page_size, q, sort


def paginate(db: Session, stmt, pp: PageParams, model, sortable: set[str], default_sort: str = "-created_at"):
    """Apply sort + pagination; returns {items,total,page,page_size}."""
    sort = pp.sort or default_sort
    desc = sort.startswith("-")
    col = sort.lstrip("-+")
    if col not in sortable:
        raise HTTPException(422, f"Cannot sort by '{col}'")
    c = getattr(model, col)
    stmt = stmt.order_by(c.desc() if desc else c.asc(), model.id)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    items = db.scalars(stmt.offset((pp.page - 1) * pp.page_size).limit(pp.page_size)).unique().all()
    return {"items": items, "total": total, "page": pp.page, "page_size": pp.page_size}


def like(q: str) -> str:
    return "%" + q.replace("%", r"\%").replace("_", r"\_") + "%"
