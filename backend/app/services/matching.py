"""Property matching against stored, available properties only.

Points (100): location 30, budget 25, bedrooms 15, property_type 10, amenities 10, availability 10.
Unspecified lead criteria earn half points (neutral). A property is returned only if the lead specified at
least one of location/budget/bedrooms/type and the total score >= MIN_SCORE. Listing type must agree with the
lead's transaction type (buy->sale, rent->rent) when known.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.nlp import amenity_key, format_inr
from app.models import Lead, Property, PropertyMatch

MIN_SCORE = 50


def _crit(name, matched, points, mx, detail):
    return {"name": name, "matched": matched, "points": points, "max_points": mx, "detail": detail}


def score_property(req: dict, p: Property) -> tuple[int, list[dict], str]:
    c = []
    loc = (req.get("location") or "").strip().lower()
    if loc:
        hay = f"{p.location} {p.city or ''}".lower()
        toks = [t.strip() for t in loc.replace(",", " ").split() if len(t) > 2]
        full = loc in hay
        part = any(t in hay for t in toks)
        if full or (toks and all(t in hay for t in toks)):
            c.append(_crit("location", True, 30, 30, f"Located in {p.location} (wanted {req['location']})"))
        elif part:
            c.append(_crit("location", True, 18, 30, f"Partial location match: {p.location} vs {req['location']}"))
        else:
            c.append(_crit("location", False, 0, 30, f"{p.location} is not in {req['location']}"))
    else:
        c.append(_crit("location", True, 15, 30, "No location preference"))

    bmin, bmax = req.get("budget_min"), req.get("budget_max")
    if bmin or bmax:
        hi = bmax or float("inf")
        lo = bmin or 0
        if lo <= p.price <= hi:
            c.append(_crit("budget", True, 25, 25, f"Price {format_inr(p.price)} within budget"))
        elif bmax and p.price <= bmax * 1.1:
            c.append(_crit("budget", True, 12, 25, f"Price {format_inr(p.price)} slightly above budget {format_inr(bmax)} (within 10%)"))
        else:
            c.append(_crit("budget", False, 0, 25, f"Price {format_inr(p.price)} outside budget"))
    else:
        c.append(_crit("budget", True, 12, 25, "No budget stated"))

    bd = req.get("bedrooms")
    if bd:
        if p.bedrooms == bd:
            c.append(_crit("bedrooms", True, 15, 15, f"{p.bedrooms} bedrooms as requested"))
        elif p.bedrooms and abs(p.bedrooms - bd) == 1:
            c.append(_crit("bedrooms", False, 6, 15, f"{p.bedrooms} bedrooms vs {bd} requested (off by one)"))
        else:
            c.append(_crit("bedrooms", False, 0, 15, f"{p.bedrooms or 'n/a'} bedrooms vs {bd} requested"))
    else:
        c.append(_crit("bedrooms", True, 7, 15, "No bedroom preference"))

    pt = req.get("property_type")
    if pt:
        ok = p.property_type == pt
        c.append(_crit("property_type", ok, 10 if ok else 0, 10, f"{p.property_type} vs {pt} requested"))
    else:
        c.append(_crit("property_type", True, 5, 10, "No type preference"))

    wanted = {amenity_key(a) or a.lower() for a in (req.get("amenities") or [])}
    if wanted:
        have = {amenity_key(a) or a.lower() for a in (p.amenities or [])}
        hit = wanted & have
        pts = round(10 * len(hit) / len(wanted))
        c.append(_crit("amenities", len(hit) == len(wanted), pts, 10,
                       f"Has {len(hit)}/{len(wanted)} wanted amenities" + (f" ({', '.join(sorted(hit))})" if hit else "")))
    else:
        c.append(_crit("amenities", True, 5, 10, "No amenity preference"))

    avail = p.status == "available" and p.units_available > 0
    c.append(_crit("availability", avail, 10 if avail else 0, 10, f"{p.units_available} unit(s) available" if avail else "Not available"))

    total = min(100, sum(x["points"] for x in c))
    good = [x["name"].replace("_", " ") for x in c if x["matched"] and x["points"] > 0 and x["name"] != "availability"]
    bad = [x["name"].replace("_", " ") for x in c if not x["matched"]]
    expl = f"Score {total}/100. " + (f"Matches on {', '.join(good)}. " if good else "") + (f"Gaps: {', '.join(bad)}." if bad else "")
    return total, c, expl.strip()


def req_from_lead(lead: Lead) -> dict:
    return {"location": lead.preferred_location, "budget_min": lead.budget_min, "budget_max": lead.budget_max,
            "bedrooms": lead.bedrooms, "property_type": lead.property_type, "amenities": lead.amenities or [],
            "transaction_type": lead.transaction_type}


def search(db: Session, org_id: str, req: dict, limit: int = 10) -> list[tuple[Property, int, list, str]]:
    if not any(req.get(k) for k in ("location", "budget_min", "budget_max", "bedrooms", "property_type")):
        return []
    q = select(Property).where(Property.organization_id == org_id, Property.status == "available", Property.units_available > 0)
    tt = req.get("transaction_type")
    if tt in ("buy", "rent"):
        q = q.where(Property.listing_type == ("sale" if tt == "buy" else "rent"))
    out = []
    for p in db.scalars(q):
        s, c, e = score_property(req, p)
        if s >= MIN_SCORE:
            out.append((p, s, c, e))
    out.sort(key=lambda x: -x[1])
    return out[:limit]


def match_lead(db: Session, lead: Lead, store: bool = True) -> list[PropertyMatch]:
    results = search(db, lead.organization_id, req_from_lead(lead))
    existing = {m.property_id: m for m in db.scalars(select(PropertyMatch).where(PropertyMatch.lead_id == lead.id))}
    keep = set()
    out = []
    for p, s, c, e in results:
        m = existing.get(p.id) or PropertyMatch(organization_id=lead.organization_id, lead_id=lead.id, property_id=p.id)
        m.score, m.criteria, m.explanation, m.property = s, c, e, p
        if store:
            db.add(m)
        keep.add(p.id)
        out.append(m)
    if store:
        for pid, m in existing.items():
            if pid not in keep:
                db.delete(m)
        db.flush()
    return out
