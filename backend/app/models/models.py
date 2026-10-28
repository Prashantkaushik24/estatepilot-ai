"""ORM models. UUID string PKs, org-scoped, UTC timestamps."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, returns tz-aware UTC (SQLite drops tzinfo)."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


def _id():
    return mapped_column(String(36), primary_key=True, default=uid)


def _org():
    return mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, onupdate=now, nullable=False)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    id: Mapped[str] = _id()
    name: Mapped[str] = mapped_column(String(200), unique=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    default_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(20), nullable=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="agent")
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EmailAccount(Base, TimestampMixin):
    __tablename__ = "email_accounts"
    __table_args__ = (UniqueConstraint("organization_id", "provider", "account_email"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    provider: Mapped[str] = mapped_column(String(20), default="gmail")
    account_email: Mapped[str] = mapped_column(String(320))
    access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class EmailThread(Base, TimestampMixin):
    __tablename__ = "email_threads"
    __table_args__ = (UniqueConstraint("organization_id", "external_id"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_org_status", "organization_id", "status"),
                      Index("ix_leads_org_email", "organization_id", "email"),
                      Index("ix_leads_org_phone", "organization_id", "phone"))
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="New")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    score: Mapped[int] = mapped_column(Integer, default=0)
    score_reasons: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    preferred_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    intent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    assigned_agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id], lazy="joined")

    @property
    def assigned_agent_name(self):
        return self.assigned_agent.full_name if self.assigned_agent else None


class Property(Base, TimestampMixin):
    __tablename__ = "properties"
    __table_args__ = (Index("ix_properties_org_status", "organization_id", "status"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    title: Mapped[str] = mapped_column(String(300))
    property_type: Mapped[str] = mapped_column(String(30), default="apartment")
    listing_type: Mapped[str] = mapped_column(String(10), default="sale")
    price: Mapped[float] = mapped_column(Float, default=0)
    location: Mapped[str] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sqft: Mapped[float | None] = mapped_column(Float, nullable=True)
    units_available: Mapped[int] = mapped_column(Integer, default=1)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="available")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class PropertyMatch(Base, TimestampMixin):
    __tablename__ = "property_matches"
    __table_args__ = (UniqueConstraint("lead_id", "property_id"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    lead_id: Mapped[str] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[str] = mapped_column(String(36), ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    criteria: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    property = relationship("Property", lazy="joined")


class Email(Base, TimestampMixin):
    __tablename__ = "emails"
    __table_args__ = (UniqueConstraint("organization_id", "content_hash", name="uq_email_org_hash"),
                      UniqueConstraint("organization_id", "external_id", name="uq_email_org_extid"),
                      Index("ix_emails_org_status", "organization_id", "processing_status"))
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    thread_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("email_threads.id", ondelete="SET NULL"), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    sender_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sender_email: Mapped[str] = mapped_column(String(320))
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    source: Mapped[str] = mapped_column(String(20), default="paste")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    classification: Mapped[str | None] = mapped_column(String(40), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(20), default="pending")
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    lead = relationship("Lead", lazy="joined")
    drafts = relationship("EmailDraft", order_by="EmailDraft.created_at.desc()", lazy="selectin")

    @property
    def lead_name(self):
        return self.lead.full_name if self.lead else None

    @property
    def draft(self):
        return self.drafts[0] if self.drafts else None


class EmailDraft(Base, TimestampMixin):
    __tablename__ = "email_drafts"
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    email_id: Mapped[str] = mapped_column(String(36), ForeignKey("emails.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|approved|sending|sent|failed|discarded
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_demo_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_org_status_due", "organization_id", "status", "due_at"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    due_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now)
    reminder_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="manual")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    lead = relationship("Lead", lazy="joined")
    owner = relationship("User", lazy="joined")

    @property
    def lead_name(self):
        return self.lead.full_name if self.lead else None

    @property
    def owner_name(self):
        return self.owner.full_name if self.owner else None

    @property
    def is_overdue(self):
        return self.status == "pending" and self.due_at is not None and self.due_at < now()


class AutomationRule(Base, TimestampMixin):
    __tablename__ = "automation_rules"
    __table_args__ = (UniqueConstraint("organization_id", "key"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    key: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_result: Mapped[str | None] = mapped_column(String(300), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)


class AIProcessingRun(Base):
    __tablename__ = "ai_processing_runs"
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    email_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("emails.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="success")
    provider: Mapped[str] = mapped_column(String(20), default="demo")
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_entity", "organization_id", "entity_type", "entity_id"),)
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    message: Mapped[str] = mapped_column(String(1000))
    level: Mapped[str] = mapped_column(String(10), default="info")
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, index=True)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = _id()
    organization_id: Mapped[str] = _org()
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(String(1000), default="")
    type: Mapped[str] = mapped_column(String(30), default="info")
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now, index=True)
