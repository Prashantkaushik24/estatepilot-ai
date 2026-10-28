from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.helpers import get_or_404
from app.core.deps import PageParams, agent_up, any_user, like, manager_up, paginate
from app.db.session import get_db
from app.models import Property, User
from app.schemas.common import Page
from app.schemas.entities import MatchOut, MatchSearchIn, PropertyIn, PropertyOut, PropertyPatch
from app.services.audit import audit
from app.services.matching import search

router = APIRouter(tags=["properties"])
SORTABLE = {"created_at", "updated_at", "price", "title", "location", "bedrooms", "status"}


@router.get("/properties", response_model=Page[PropertyOut])
def list_properties(pp: PageParams = Depends(), status: str | None = None, property_type: str | None = None, location: str | None = None,
                    user: User = Depends(any_user), db: Session = Depends(get_db)):
    stmt = select(Property).where(Property.organization_id == user.organization_id)
    if status:
        stmt = stmt.where(Property.status == status)
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    if location:
        stmt = stmt.where(or_(Property.location.ilike(like(location), escape="\\"), Property.city.ilike(like(location), escape="\\")))
    if pp.q:
        stmt = stmt.where(or_(Property.title.ilike(like(pp.q), escape="\\"), Property.location.ilike(like(pp.q), escape="\\")))
    return paginate(db, stmt, pp, Property, SORTABLE)


@router.post("/properties", response_model=PropertyOut, status_code=201)
def create_property(body: PropertyIn, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    p = Property(organization_id=user.organization_id, **body.model_dump())
    db.add(p)
    db.flush()
    audit(db, user.organization_id, "property.created", "Property created", entity_type="property", entity_id=p.id, actor_id=user.id)
    db.commit()
    return p


@router.get("/properties/{pid}", response_model=PropertyOut)
def get_property(pid: str, user: User = Depends(any_user), db: Session = Depends(get_db)):
    return get_or_404(db, Property, pid, user.organization_id, "Property")


@router.patch("/properties/{pid}", response_model=PropertyOut)
def patch_property(pid: str, body: PropertyPatch, user: User = Depends(agent_up), db: Session = Depends(get_db)):
    p = get_or_404(db, Property, pid, user.organization_id, "Property")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is None and k in ("title", "location", "price", "units_available", "status", "property_type", "listing_type"):
            raise HTTPException(422, f"{k} cannot be null")
        setattr(p, k, v)
    audit(db, user.organization_id, "property.updated", "Property updated", entity_type="property", entity_id=p.id, actor_id=user.id)
    db.commit()
    return p


@router.delete("/properties/{pid}", status_code=204)
def delete_property(pid: str, user: User = Depends(manager_up), db: Session = Depends(get_db)):
    p = get_or_404(db, Property, pid, user.organization_id, "Property")
    audit(db, user.organization_id, "property.deleted", "Property deleted", entity_type="property", entity_id=p.id, actor_id=user.id)
    db.delete(p)
    db.commit()


@router.post("/matches/search", response_model=list[MatchOut])
def matches_search(body: MatchSearchIn, user: User = Depends(any_user), db: Session = Depends(get_db)):
    """Ad-hoc, read-only (not stored) so analysts may use it."""
    res = search(db, user.organization_id, body.model_dump())
    return [MatchOut(property=p, score=s, criteria=c, explanation=e) for p, s, c, e in res]
