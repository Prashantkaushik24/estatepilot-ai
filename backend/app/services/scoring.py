"""Deterministic, explainable lead scoring.

Rules (max 100, capped):
  contact_email    +10  email present
  contact_phone    +10  phone present
  budget           +15  budget stated (min or max)
  location         +10  preferred location stated
  requirements     +10  bedrooms or property type stated (+5 more if both)
  timeline         +20 within <=3 months / +12 <=6 months / +5 longer / +0 none  (asap counts as <=3)
  intent           +10  clear transaction intent (buy/rent) stated
  amenities         +5  amenity preferences stated
  site_visit       +10  email classified as a site visit request
Priority: >=75 hot, >=55 high, >=35 medium, else low.
"""
from app.agents.nlp import timeline_months

MAX_SCORE = 100


def priority_for(score: int) -> str:
    return "hot" if score >= 75 else "high" if score >= 55 else "medium" if score >= 35 else "low"


def score_lead(lead, classification: str | None = None) -> tuple[int, list[dict]]:
    r: list[dict] = []

    def add(factor, points, detail):
        r.append({"factor": factor, "points": points, "detail": detail})

    if lead.email:
        add("contact_email", 10, "Email address provided")
    if lead.phone:
        add("contact_phone", 10, "Phone number provided")
    if lead.budget_max or lead.budget_min:
        add("budget", 15, "Budget stated")
    if lead.preferred_location:
        add("location", 10, f"Preferred location: {lead.preferred_location}")
    if lead.bedrooms or lead.property_type:
        pts = 10 + (5 if lead.bedrooms and lead.property_type else 0)
        add("requirements", pts, "Specific property requirements stated")
    m = timeline_months(lead.timeline)
    if m is not None:
        if m <= 3:
            add("timeline", 20, f"Urgent timeline ({lead.timeline})")
        elif m <= 6:
            add("timeline", 12, f"Near-term timeline ({lead.timeline})")
        else:
            add("timeline", 5, f"Longer timeline ({lead.timeline})")
    elif lead.timeline:
        add("timeline", 5, f"Timeline mentioned ({lead.timeline})")
    if lead.transaction_type in ("buy", "rent"):
        add("intent", 10, f"Clear intent to {lead.transaction_type}")
    if lead.amenities:
        add("amenities", 5, "Amenity preferences stated")
    if classification == "site_visit_request":
        add("site_visit", 10, "Requested a site visit")
    total = min(MAX_SCORE, sum(x["points"] for x in r))
    if not r:
        add("none", 0, "No qualifying information yet")
    return total, r
