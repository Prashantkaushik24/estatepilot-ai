from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORM, UTCDT

LEAD_STATUSES = ["New", "Contacted", "Qualified", "Viewing Scheduled", "Negotiation", "Won", "Lost"]
Status = Literal["New", "Contacted", "Qualified", "Viewing Scheduled", "Negotiation", "Won", "Lost"]
LPriority = Literal["low", "medium", "high", "hot"]
Source = Literal["email", "manual", "web", "referral", "gmail", "demo"]
PType = Literal["apartment", "villa", "house", "plot", "commercial"]
Txn = Literal["buy", "rent", "sell"]


class UserOut(ORM):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    is_active: bool


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "manager", "agent", "analyst"]


class UserPatch(BaseModel):
    role: Literal["admin", "manager", "agent", "analyst"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=200)


class ScoreReason(BaseModel):
    factor: str
    points: int
    detail: str


class LeadOut(ORM):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    status: str
    priority: str
    score: int
    score_reasons: list[ScoreReason] = []
    source: str
    preferred_location: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    timeline: str | None = None
    amenities: list[str] = []
    intent: str | None = None
    transaction_type: str | None = None
    assigned_agent_id: str | None = None
    assigned_agent_name: str | None = None
    tags: list[str] = []
    notes: str | None = None
    next_follow_up_at: UTCDT | None = None
    is_archived: bool
    is_demo: bool
    created_at: UTCDT
    updated_at: UTCDT


class LeadIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    status: Status = "New"
    priority: LPriority | None = None
    source: Source = "manual"
    preferred_location: str | None = None
    property_type: PType | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    timeline: str | None = None
    amenities: list[str] = []
    intent: str | None = None
    transaction_type: Txn | None = None
    assigned_agent_id: str | None = None
    tags: list[str] = []
    notes: str | None = None
    next_follow_up_at: UTCDT | None = None


class LeadPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    status: Status | None = None
    priority: LPriority | None = None
    source: Source | None = None
    preferred_location: str | None = None
    property_type: PType | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    timeline: str | None = None
    amenities: list[str] | None = None
    intent: str | None = None
    transaction_type: Txn | None = None
    assigned_agent_id: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    next_follow_up_at: UTCDT | None = None


class ActivityOut(BaseModel):
    id: str
    type: str
    message: str
    created_at: UTCDT
    actor: str | None = None


class PropertyOut(ORM):
    id: str
    title: str
    property_type: str
    listing_type: str
    price: float
    location: str
    city: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqft: float | None = None
    units_available: int
    amenities: list[str] = []
    status: str
    description: str | None = None
    url: str | None = None
    agent_id: str | None = None
    is_demo: bool
    created_at: UTCDT
    updated_at: UTCDT


class PropertyIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    property_type: PType = "apartment"
    listing_type: Literal["sale", "rent"] = "sale"
    price: float = Field(ge=0)
    location: str = Field(min_length=1, max_length=300)
    city: str | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: int | None = Field(default=None, ge=0, le=50)
    area_sqft: float | None = Field(default=None, ge=0)
    units_available: int = Field(default=1, ge=0)
    amenities: list[str] = []
    status: Literal["available", "reserved", "sold", "rented"] = "available"
    description: str | None = None
    url: str | None = None
    agent_id: str | None = None


class PropertyPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    property_type: PType | None = None
    listing_type: Literal["sale", "rent"] | None = None
    price: float | None = Field(default=None, ge=0)
    location: str | None = None
    city: str | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: int | None = Field(default=None, ge=0, le=50)
    area_sqft: float | None = Field(default=None, ge=0)
    units_available: int | None = Field(default=None, ge=0)
    amenities: list[str] | None = None
    status: Literal["available", "reserved", "sold", "rented"] | None = None
    description: str | None = None
    url: str | None = None
    agent_id: str | None = None


class Criterion(BaseModel):
    name: str
    matched: bool
    points: int
    max_points: int
    detail: str


class MatchOut(ORM):
    id: str | None = None
    lead_id: str | None = None
    property: PropertyOut
    score: int
    criteria: list[Criterion]
    explanation: str


class MatchSearchIn(BaseModel):
    location: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    bedrooms: int | None = None
    property_type: PType | None = None
    amenities: list[str] = []
    transaction_type: Txn | None = None


class TaskOut(ORM):
    id: str
    title: str
    description: str | None = None
    lead_id: str | None = None
    lead_name: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    priority: str
    status: str
    due_at: UTCDT
    reminder_at: UTCDT | None = None
    completed_at: UTCDT | None = None
    is_overdue: bool
    source: str
    created_at: UTCDT


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    lead_id: str | None = None
    owner_id: str | None = None
    priority: Literal["low", "medium", "high", "hot"] = "medium"
    due_at: UTCDT
    reminder_at: UTCDT | None = None


class TaskPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    lead_id: str | None = None
    owner_id: str | None = None
    priority: Literal["low", "medium", "high", "hot"] | None = None
    status: Literal["pending", "completed", "cancelled"] | None = None
    due_at: UTCDT | None = None
    reminder_at: UTCDT | None = None


class ExtractionOut(BaseModel):
    customer_name: str | None = None
    sender_email: str | None = None
    phone: str | None = None
    intent: str | None = None
    preferred_location: str | None = None
    property_type: str | None = None
    bedrooms: int | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    transaction_type: str | None = None
    timeline: str | None = None
    amenities: list[str] = []
    urgency: str | None = None
    missing_information: list[str] = []


class DraftOut(ORM):
    id: str
    email_id: str
    lead_id: str | None = None
    subject: str
    body: str
    status: str
    approved_by: str | None = None
    approved_at: UTCDT | None = None
    sent_at: UTCDT | None = None
    provider_message_id: str | None = None
    is_demo_ai: bool
    created_at: UTCDT
    updated_at: UTCDT


class DraftIn(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=5000)


class SendIn(BaseModel):
    confirm: bool
    confirm_recipient: str


class EmailOut(ORM):
    id: str
    thread_id: str | None = None
    external_id: str | None = None
    sender_name: str | None = None
    sender_email: str
    recipient_email: str | None = None
    subject: str
    body: str
    received_at: UTCDT
    source: str
    is_read: bool
    classification: str | None = None
    processing_status: str
    priority: str | None = None
    lead_id: str | None = None
    lead_name: str | None = None
    summary: str | None = None
    extraction: ExtractionOut | None = None
    draft: DraftOut | None = None
    is_demo_ai: bool
    error: str | None = None
    created_at: UTCDT


class EmailImport(BaseModel):
    sender_email: EmailStr
    sender_name: str | None = Field(default=None, max_length=200)
    subject: str = Field(max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    received_at: UTCDT | None = None
    process: bool = True
    source: Literal["paste", "demo"] = "paste"


class EmailPatch(BaseModel):
    is_read: bool | None = None


class AIRunOut(ORM):
    id: str
    email_id: str | None = None
    status: str
    provider: str
    model: str | None = None
    is_demo: bool
    attempts: int
    error: str | None = None
    duration_ms: int
    steps: list[Any] = []
    created_at: UTCDT


class ProcessResult(BaseModel):
    email: EmailOut
    lead: LeadOut | None = None
    lead_created: bool = False
    matches: list[MatchOut] = []
    draft: DraftOut | None = None
    task: TaskOut | None = None
    run: AIRunOut | None = None
    steps: list[dict]


class RuleOut(ORM):
    id: str
    key: str
    name: str
    description: str
    enabled: bool
    last_run_at: UTCDT | None = None
    last_result: str | None = None
    run_count: int


class RulePatch(BaseModel):
    enabled: bool


class KillIn(BaseModel):
    enabled: bool


class AuditOut(BaseModel):
    id: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    message: str
    level: str
    actor_id: str | None = None
    metadata: dict = {}
    created_at: UTCDT


class NotificationOut(ORM):
    id: str
    title: str
    message: str
    type: str
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool
    created_at: UTCDT


class SettingsPatch(BaseModel):
    demo_mode: bool | None = None
