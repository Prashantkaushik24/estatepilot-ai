"""Pydantic models validating structured AI output (provider-agnostic)."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CLASSIFICATIONS = ["property_inquiry", "buying_request", "selling_request", "rental_inquiry",
                   "property_listing_submission", "site_visit_request", "pricing_inquiry", "follow_up",
                   "complaint", "spam", "other"]


class ExtractionModel(BaseModel):
    customer_name: str | None = Field(default=None, max_length=200)
    sender_email: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    intent: str | None = Field(default=None, max_length=300)
    preferred_location: str | None = Field(default=None, max_length=200)
    property_type: Literal["apartment", "villa", "house", "plot", "commercial"] | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=20)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    transaction_type: Literal["buy", "rent", "sell"] | None = None
    timeline: str | None = Field(default=None, max_length=200)
    amenities: list[str] = Field(default_factory=list, max_length=20)
    urgency: Literal["low", "medium", "high"] | None = None
    missing_information: list[str] = Field(default_factory=list)

    @field_validator("property_type", "transaction_type", "urgency", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class AnalysisResult(BaseModel):
    classification: Literal[tuple(CLASSIFICATIONS)]  # type: ignore[valid-type]
    summary: str = Field(max_length=1000)
    priority: Literal["low", "medium", "high"] = "medium"
    extraction: ExtractionModel

    @field_validator("classification", "priority", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.lower().strip() if isinstance(v, str) else v


class DraftResult(BaseModel):
    subject: str = Field(max_length=500)
    body: str = Field(max_length=5000)
