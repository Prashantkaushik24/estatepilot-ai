from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import admin_only, get_current_user, manager_up
from app.core.security import create_access_token, hash_password, login_limiter, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.entities import LoginIn, LoginOut, UserCreate, UserOut, UserPatch
from app.services.audit import audit

router = APIRouter(tags=["auth"])

_DUMMY = hash_password("dummy-password")


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    s = get_settings()
    key = f"{request.client.host if request.client else '?'}|{body.email.lower()}"
    if not login_limiter.allow(key, s.LOGIN_RATE_LIMIT, s.LOGIN_RATE_WINDOW_SECONDS):
        raise HTTPException(429, "Too many login attempts. Try again later.")
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    ok = verify_password(body.password, user.hashed_password if user else _DUMMY)
    if not user or not ok or not user.is_active:
        if user:
            audit(db, user.organization_id, "auth.login_failed", "Failed login attempt", entity_type="user", entity_id=user.id, level="warning")
            db.commit()
        raise HTTPException(401, "Invalid email or password")
    audit(db, user.organization_id, "auth.login", "User logged in", entity_type="user", entity_id=user.id, actor_id=user.id)
    db.commit()
    return LoginOut(access_token=create_access_token(user.id, user.organization_id, user.role), user=user)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(user: User = Depends(manager_up), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.organization_id == user.organization_id).order_by(User.full_name)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(409, "Email already registered")
    u = User(organization_id=user.organization_id, email=body.email.lower(), full_name=body.full_name, role=body.role,
             hashed_password=hash_password(body.password))
    db.add(u)
    db.flush()
    audit(db, user.organization_id, "user.created", f"User created with role {body.role}", entity_type="user", entity_id=u.id, actor_id=user.id)
    db.commit()
    return u


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(user_id: str, body: UserPatch, user: User = Depends(admin_only), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u or u.organization_id != user.organization_id:
        raise HTTPException(404, "User not found")
    data = body.model_dump(exclude_unset=True)
    if u.id == user.id and (data.get("is_active") is False or ("role" in data and data["role"] != "admin")):
        raise HTTPException(409, "You cannot demote or deactivate yourself")
    for k, v in data.items():
        setattr(u, k, v)
    audit(db, user.organization_id, "user.updated", "User updated", entity_type="user", entity_id=u.id, actor_id=user.id, meta={"fields": ",".join(data)})
    db.commit()
    return u
