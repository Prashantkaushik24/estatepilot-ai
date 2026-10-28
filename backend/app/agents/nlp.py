"""Deterministic text helpers shared by the demo provider, scoring and matching."""
import re

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "twelve": 12, "a": 1, "an": 1}

# canonical amenity key -> keyword regexes
AMENITY_PATTERNS = {
    "schools nearby": r"\bschools?\b",
    "parking": r"\bparking\b|\bgarage\b",
    "gym": r"\bgym\b|\bfitness\b",
    "swimming pool": r"\bswimming\b|\bpool\b",
    "garden": r"\bgarden\b|\bpark\b|\bgreen\b",
    "clubhouse": r"\bclub ?house\b",
    "security": r"\bsecurity\b|\bgated\b",
    "lift": r"\blift\b|\belevator\b",
    "metro nearby": r"\bmetro\b",
    "hospital nearby": r"\bhospitals?\b",
    "mall nearby": r"\bmalls?\b|\bshopping\b",
    "power backup": r"\bpower backup\b|\bgenerator\b",
    "balcony": r"\bbalcon(?:y|ies)\b",
}


def amenity_key(text: str) -> str | None:
    t = (text or "").lower()
    for key, pat in AMENITY_PATTERNS.items():
        if re.search(pat, t):
            return key
    return None


def extract_amenities(text: str) -> list[str]:
    t = (text or "").lower()
    return [k for k, p in AMENITY_PATTERNS.items() if re.search(p, t)]


def timeline_months(timeline: str | None) -> float | None:
    """Parse a timeline phrase into approximate months. None if unknown."""
    if not timeline:
        return None
    t = timeline.lower()
    if re.search(r"asap|immediate|urgent|right away|this week|right now", t):
        return 0.25
    if "next month" in t or "this month" in t:
        return 1
    m = re.search(r"(\d+|" + "|".join(NUM_WORDS) + r")\s*(day|week|month|year)s?", t)
    if not m:
        return None
    n = m.group(1)
    n = int(n) if n.isdigit() else NUM_WORDS.get(n, 1)
    return {"day": n / 30, "week": n / 4.3, "month": n, "year": n * 12}[m.group(2)]


def format_inr(v: float | None) -> str:
    if v is None:
        return "n/a"
    if v >= 1e7:
        x = v / 1e7
        return f"₹{x:g} crore" if abs(x - round(x, 2)) < 1e-9 else f"₹{x:.2f} crore"
    if v >= 1e5:
        return f"₹{v / 1e5:g} lakh"
    return f"₹{v:,.0f}"


def norm_phone(p: str | None) -> str | None:
    if not p:
        return None
    d = re.sub(r"\D", "", p)
    if len(d) >= 10:
        return d[-10:]
    return d or None
