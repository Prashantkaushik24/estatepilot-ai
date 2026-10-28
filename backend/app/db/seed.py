"""Idempotent demo seed. Run: python -m app.db.seed"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Lead, Organization, Property, Task, User
from app.services.audit import audit
from app.services.leads import rescore
from app.services.orgs import create_org, ensure_rules

PASSWORD = "Passw0rd!demo"
USERS = [("admin@demo.com", "Aarav Admin", "admin"), ("manager@demo.com", "Meera Manager", "manager"),
         ("agent@demo.com", "Arjun Agent", "agent"), ("analyst@demo.com", "Anika Analyst", "analyst")]

L = 1e5
CR = 1e7
PROPS = [
    ("Demo: Sunrise Heights 3BHK", "apartment", "sale", 7500000, "Vaishali Nagar, Jaipur", "Jaipur", 3, 3, 1650, 4, ["Parking", "Gym", "Near School", "Lift", "Security"]),
    ("Demo: Green Valley 3BHK", "apartment", "sale", 7900000, "Mansarovar, Jaipur", "Jaipur", 3, 2, 1500, 2, ["Parking", "Garden", "Schools nearby", "Clubhouse"]),
    ("Demo: Pink City Residency 2BHK", "apartment", "sale", 4800000, "Malviya Nagar, Jaipur", "Jaipur", 2, 2, 1100, 6, ["Parking", "Lift", "Power backup"]),
    ("Demo: Royal Villa Jagatpura", "villa", "sale", 19500000, "Jagatpura, Jaipur", "Jaipur", 4, 4, 3200, 1, ["Garden", "Parking", "Swimming pool", "Security"]),
    ("Demo: Malviya Garden Villa", "villa", "sale", 21000000, "Malviya Nagar, Jaipur", "Jaipur", 4, 4, 3500, 2, ["Garden", "Parking", "Clubhouse"]),
    ("Demo: Lakeview 2BHK Rental", "apartment", "rent", 22000, "Jagatpura, Jaipur", "Jaipur", 2, 2, 1050, 3, ["Gym", "Lift", "Parking"]),
    ("Demo: Skyline 3BHK Delhi", "apartment", "sale", 14500000, "Dwarka, New Delhi", "New Delhi", 3, 3, 1800, 5, ["Metro nearby", "Gym", "Parking"]),
    ("Demo: Commercial Space C-Scheme", "commercial", "sale", 32000000, "C-Scheme, Jaipur", "Jaipur", None, 2, 2400, 1, ["Parking", "Power backup", "Lift"]),
]


def seed(db) -> bool:
    if db.scalar(select(Organization).where(Organization.name == "Demo Realty")):
        return False
    org = create_org(db, "Demo Realty")
    users = {}
    for email, name, role in USERS:
        u = User(organization_id=org.id, email=email, full_name=name, role=role, hashed_password=hash_password(PASSWORD))
        db.add(u)
        users[role] = u
    db.flush()
    org.default_agent_id = users["agent"].id
    populate_demo(db, org, users["agent"])
    audit(db, org.id, "seed.completed", "Demo data seeded", level="info")
    db.commit()
    return True


def populate_demo(db, org, agent) -> None:
    users = {"agent": agent}
    for t, pt, lt, price, loc, city, bd, ba, area, units, am in PROPS:
        db.add(Property(organization_id=org.id, title=t, property_type=pt, listing_type=lt, price=price, location=loc, city=city, bedrooms=bd,
                        bathrooms=ba, area_sqft=area, units_available=units, amenities=am, status="available", is_demo=True,
                        description="Fictional demo listing", agent_id=users["agent"].id))
    now = datetime.now(timezone.utc)
    leads = [
        dict(full_name="Demo Lead: Kavita Singh", email="kavita.demo@example.com", phone="9811100001", status="Qualified", preferred_location="Jaipur",
             property_type="apartment", bedrooms=3, budget_max=8 * CR / 10, timeline="within 2 months", amenities=["parking"], transaction_type="buy", source="demo", days=6),
        dict(full_name="Demo Lead: Rohan Mehta", email="rohan.demo@example.com", phone="9811100002", status="New", preferred_location="Malviya Nagar, Jaipur",
             property_type="villa", bedrooms=4, budget_max=2 * CR, timeline="in 4 months", amenities=["garden"], transaction_type="buy", source="email", days=3),
        dict(full_name="Demo Lead: Sneha Kapoor", email="sneha.demo@example.com", status="Contacted", preferred_location="Jagatpura, Jaipur",
             property_type="apartment", bedrooms=2, budget_max=25000, transaction_type="rent", source="web", days=10),
        dict(full_name="Demo Lead: Vikram Rao", email="vikram.demo@example.com", phone="9811100004", status="Won", preferred_location="New Delhi",
             property_type="apartment", bedrooms=3, budget_max=1.5 * CR, timeline="asap", transaction_type="buy", source="referral", days=20),
        dict(full_name="Demo Lead: Isha Jain", email="isha.demo@example.com", status="Lost", preferred_location="Jaipur", budget_min=3 * CR, source="manual", days=15),
    ]
    made = []
    for d in leads:
        days = d.pop("days")
        l = Lead(organization_id=org.id, is_demo=True, assigned_agent_id=users["agent"].id, amenities=d.pop("amenities", []), tags=["demo"], score_reasons=[], **d)
        rescore(l)
        l.created_at = now - timedelta(days=days)
        db.add(l)
        made.append(l)
    db.flush()
    for i, (title, off, status) in enumerate([("Call Kavita Singh to schedule viewing", 4, "pending"), ("Send brochure to Rohan Mehta", -6, "pending"),
                                              ("Collect documents from Vikram Rao", -48, "completed")]):
        t = Task(organization_id=org.id, lead_id=made[i].id, owner_id=users["agent"].id, title=title, status=status, priority="high",
                 due_at=now + timedelta(hours=off), source="manual", is_demo=True,
                 completed_at=now - timedelta(hours=40) if status == "completed" else None)
        db.add(t)
    db.flush()


def seed_if_empty():
    with SessionLocal() as db:
        if db.scalar(select(Organization.id).limit(1)) is None:
            seed(db)
        else:
            for o in db.scalars(select(Organization)):
                ensure_rules(db, o.id)
            db.commit()


def main():
    if get_settings().DATABASE_URL.startswith("sqlite"):
        import app.models  # noqa
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print("seeded" if seed(db) else "already seeded (no changes)")


if __name__ == "__main__":
    main()
