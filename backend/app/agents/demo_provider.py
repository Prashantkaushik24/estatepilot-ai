"""Deterministic regex/keyword analysis. Output is clearly marked demo AI by callers (is_demo_ai=true)."""
import re

from app.agents.nlp import NUM_WORDS, extract_amenities, format_inr, timeline_months
from app.agents.schemas import AnalysisResult, DraftResult, ExtractionModel

CITIES = ["jaipur", "delhi", "new delhi", "mumbai", "bangalore", "bengaluru", "pune", "hyderabad", "chennai",
          "kolkata", "gurgaon", "gurugram", "noida", "ahmedabad", "udaipur", "jodhpur", "lucknow", "chandigarh",
          "goa", "indore", "kota", "ajmer", "bikaner", "surat", "nagpur"]
LOCALITIES = ["vaishali nagar", "malviya nagar", "c-scheme", "c scheme", "mansarovar", "jagatpura", "tonk road",
              "sodala", "bani park", "ajmer road", "raja park", "civil lines", "sector 62", "whitefield", "bandra"]
_STOP = {"I", "The", "My", "We", "It", "A", "An", "Hello", "Hi", "Dear", "Please", "Thanks", "Regards", "Also"}

PTYPES = [("villa", r"\bvillas?\b"), ("plot", r"\bplots?\b|\bland\b"), ("commercial", r"\boffice\b|\bshop\b|\bcommercial\b|\bshowroom\b"),
          ("house", r"\bhouse\b|\bbungalow\b|\bindependent\b|\bkothi\b"), ("apartment", r"\bapartments?\b|\bflats?\b|\bbhk\b|\bcondo\b")]
UNIT = {"crore": 1e7, "crores": 1e7, "cr": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5, "k": 1e3}
_NUM = r"(\d+(?:[.,]\d+)?)"
_UNITS = r"(crores?|cr|lakhs?|lacs?|l|k)\b"


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_budget(t: str) -> tuple[float | None, float | None]:
    t = t.lower()
    m = re.search(_NUM + r"\s*(?:-|to)\s*(?:₹|rs\.?\s*|inr\s*)?" + _NUM + r"\s*" + _UNITS, t)
    if m:
        u = UNIT[m.group(3)]
        return _num(m.group(1)) * u, _num(m.group(2)) * u
    m = re.search(r"(?:(under|below|upto|up to|within|max(?:imum)?|less than|not more than|above|over|at least|minimum|more than|around|about|approx(?:imately)?)\s*)?(?:₹|rs\.?|inr)?\s*"
                  + _NUM + r"\s*" + _UNITS, t)
    amount = None
    mod = None
    if m and (m.group(0).find("₹") >= 0 or re.search(r"rs|inr|budget|under|below|upto|up to|within|max|around|about|above|over|less|more|least|minimum|approx", m.group(0)) or True):
        # guard: unit "l"/"k" with no currency/budget cue is too ambiguous
        if m.group(3) in ("l", "k") and not (m.group(1) or re.search(r"₹|rs|inr|budget", t)):
            m = None
    if m:
        amount = _num(m.group(2)) * UNIT[m.group(3)]
        mod = m.group(1)
    else:
        m2 = re.search(r"(under|below|upto|up to|budget(?: of| is)?|within)?\s*(?:₹|rs\.?|inr)\s*([\d,]{6,})", t)
        if m2:
            amount, mod = float(m2.group(2).replace(",", "")), m2.group(1)
    if amount is None:
        return None, None
    if mod and re.match(r"above|over|at least|minimum|more than", mod):
        return amount, None
    return None, amount


def parse_phone(t: str) -> str | None:
    m = re.search(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)", t)
    if m:
        return re.sub(r"\D", "", m.group(1))
    return None


def parse_timeline(t: str) -> str | None:
    tl = t.lower()
    m = re.search(r"\b(?:within|in|by|over)\s+(?:the\s+)?(?:next\s+)?((?:\d+|" + "|".join(NUM_WORDS) + r")(?:\s*-\s*\d+)?\s*(?:days?|weeks?|months?|years?))", tl)
    if m:
        return ("within " if re.match(r"(within|in)", m.group(0)) and m.group(0).startswith("within") else "in ") + m.group(1)
    for k in ("asap", "immediately", "urgent", "next month", "this month", "this week", "right away"):
        if k in tl:
            return k
    m = re.search(r"\bmove\b[^.]*?\b(?:in|within)\s+(?:the\s+)?(?:next\s+)?([\w ]{3,25}?(?:months?|weeks?))", tl)
    return m.group(1) if m else None


def parse_location(text: str) -> str | None:
    tl = text.lower()
    for loc in LOCALITIES:
        if loc in tl:
            base = loc.title()
            city = next((c for c in CITIES if c in tl), None)
            return f"{base}, {city.title()}" if city else base
    for c in CITIES:
        if re.search(r"\b" + re.escape(c) + r"\b", tl):
            return c.title()
    m = re.search(r"\b(?:in|at|around|near)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", text)
    if m and m.group(1).split()[0] not in _STOP:
        return m.group(1)
    return None


def parse_bedrooms(t: str) -> int | None:
    tl = t.lower()
    m = re.search(r"(\d+|" + "|".join(k for k in NUM_WORDS if k not in ("a", "an")) + r")\s*[- ]?\s*(?:bhk|bed(?:room)?s?|br)\b", tl)
    if not m:
        return None
    v = m.group(1)
    return int(v) if v.isdigit() else NUM_WORDS[v]


def parse_ptype(t: str) -> str | None:
    tl = t.lower()
    for name, pat in PTYPES:
        if re.search(pat, tl):
            return name
    return None


def parse_txn(t: str) -> str | None:
    tl = t.lower()
    if re.search(r"\b(sell|selling|list my|want to list|for sale by)\b|\bmy (?:flat|house|apartment|villa|property|plot)\b.*\bsale\b", tl):
        return "sell"
    if re.search(r"\brent(?:al|ing)?\b|\blease\b|\bmonthly\b", tl):
        return "rent"
    if re.search(r"\bbuy|purchase|looking for|interested in|invest|looking to\b|under|budget", tl):
        return "buy"
    return None


def classify(subject: str, body: str, ex: ExtractionModel) -> str:
    t = f"{subject}\n{body}".lower()
    if re.search(r"lottery|you have won|winner|click here to claim|crypto|viagra|wire transfer|bitcoin|unsubscribe now", t):
        return "spam"
    if re.search(r"complain|disappointed|unacceptable|very poor|refund|terrible service|not happy", t):
        return "complaint"
    if re.search(r"site visit|schedule a visit|book a visit|visit the (?:property|site|flat)|see the (?:property|flat)|arrange a viewing|viewing", t):
        return "site_visit_request"
    if ex.transaction_type == "sell":
        return "property_listing_submission" if re.search(r"list my|submit|listing|list it", t) else "selling_request"
    if re.search(r"following up|follow up|any update|as discussed|reminder", t):
        return "follow_up"
    if re.search(r"\bprice of\b|how much|what(?:'s| is) the (?:price|cost)|pricing|\bcost\b|price list", t) and not ex.budget_max:
        return "pricing_inquiry"
    if ex.transaction_type == "rent":
        return "rental_inquiry"
    if re.search(r"looking (?:for|to buy)|want to buy|buy|purchase|budget|under", t) and (ex.property_type or ex.bedrooms or ex.budget_max):
        return "buying_request"
    if re.search(r"interested|available|property|flat|apartment|villa|plot|bhk", t):
        return "property_inquiry"
    return "other"


def customer_name(sender_name, sender_email, body) -> str | None:
    if sender_name and sender_name.strip():
        return sender_name.strip()
    m = re.search(r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", body)
    if m and m.group(1) not in _STOP and not re.match(r"(Looking|Interested)", m.group(1)):
        return m.group(1)
    m = re.search(r"(?:regards|thanks|thank you|sincerely|best),?\s*\n\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*$", body.strip())
    if m:
        return m.group(1)
    if sender_email:
        return re.sub(r"[._\-\d]+", " ", sender_email.split("@")[0]).strip().title() or None
    return None


def demo_analyze(sender_name, sender_email, subject, body) -> AnalysisResult:
    text = f"{subject}\n{body}"
    bmin, bmax = parse_budget(text)
    bhk = parse_bedrooms(text)
    ptype = parse_ptype(text)
    ex = ExtractionModel(
        customer_name=customer_name(sender_name, sender_email, body), sender_email=sender_email,
        phone=parse_phone(text), preferred_location=parse_location(text), property_type=ptype, bedrooms=bhk,
        budget_min=bmin, budget_max=bmax, transaction_type=parse_txn(text), timeline=parse_timeline(text),
        amenities=extract_amenities(text))
    cls = classify(subject, body, ex)
    if ex.transaction_type is None and cls in ("property_inquiry", "buying_request", "pricing_inquiry", "site_visit_request"):
        ex.transaction_type = "buy"
    months = timeline_months(ex.timeline)
    if months is not None and months <= 1:
        ex.urgency = "high"
    elif months is not None and months <= 3:
        ex.urgency = "medium"
    elif cls in ("site_visit_request", "complaint"):
        ex.urgency = "high" if cls == "complaint" else "medium"
    else:
        ex.urgency = "low"
    parts = []
    if ex.bedrooms:
        parts.append(f"{ex.bedrooms} BHK")
    parts.append(ex.property_type or "property")
    verb = {"buy": "buy", "rent": "rent", "sell": "sell"}.get(ex.transaction_type or "", "enquire about")
    intent = f"{verb.capitalize()} {' '.join(parts)}" + (f" in {ex.preferred_location}" if ex.preferred_location else "")
    ex.intent = intent if cls not in ("spam", "other", "complaint") else None
    miss = []
    for label, val in [("phone number", ex.phone), ("budget", ex.budget_max or ex.budget_min), ("preferred location", ex.preferred_location),
                       ("bedrooms", ex.bedrooms), ("property type", ex.property_type), ("timeline", ex.timeline)]:
        if not val:
            miss.append(label)
    ex.missing_information = miss if cls not in ("spam", "other") else []
    summ = f"{ex.customer_name or 'Sender'}: {ex.intent or cls.replace('_', ' ')}"
    if ex.budget_max:
        summ += f", budget up to {format_inr(ex.budget_max)}"
    if ex.timeline:
        summ += f", timeline {ex.timeline}"
    prio = "high" if ex.urgency == "high" else ("medium" if ex.urgency == "medium" else "low")
    if cls == "spam":
        prio = "low"
    return AnalysisResult(classification=cls, summary=summ[:900], priority=prio, extraction=ex)


def demo_draft(ctx: dict) -> DraftResult:
    name = (ctx.get("name") or "there").split()[0]
    lines = [f"Dear {name},", "", "Thank you for reaching out to us. " + (f"We understand you are looking for: {ctx['intent']}." if ctx.get("intent") else "We have received your enquiry.")]
    ms = ctx.get("matches") or []
    if ms:
        lines += ["", "Based on your requirements, these currently available options may suit you:"]
        for m in ms[:3]:
            lines.append(f"- {m['title']} ({m['location']}) - {m['price_display']}")
        lines += ["", "We would be happy to arrange a site visit at a time that suits you."]
    else:
        lines += ["", "We do not have an exact match in our current available listings, but we will keep your requirements on file and notify you as soon as suitable options become available."]
    miss = ctx.get("missing") or []
    if miss:
        lines += ["", "To help us shortlist better, could you please share: " + ", ".join(miss) + "?"]
    lines += ["", "Please let us know a convenient time for a short call.", "", "Warm regards,", "EstatePilot Realty Team"]
    subj = ctx.get("subject") or "your enquiry"
    return DraftResult(subject=subj if subj.lower().startswith("re:") else f"Re: {subj}", body="\n".join(lines))
