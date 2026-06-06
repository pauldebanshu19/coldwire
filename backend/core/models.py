"""Typed models passed between pipeline stages (Pydantic v2).

Every stage's output is the next stage's input — these are the contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_domain(value: str) -> str:
    """Strip scheme/path/www, lowercase. `https://www.Acme.com/x` -> `acme.com`."""
    v = (value or "").strip().lower()
    for prefix in ("https://", "http://"):
        if v.startswith(prefix):
            v = v[len(prefix):]
    v = v.split("/")[0].split("?")[0]
    if v.startswith("www."):
        v = v[4:]
    return v.strip().strip(".")


# ── Stage 1: companies ────────────────────────────────────────────────
class Company(BaseModel):
    domain: str
    name: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @field_validator("domain")
    @classmethod
    def _norm(cls, v: str) -> str:
        d = normalize_domain(v)
        if not d or "." not in d:
            raise ValueError(f"invalid domain: {v!r}")
        return d


# ── Stage 3: email ────────────────────────────────────────────────────
class EmailStatus(str, Enum):
    VERIFIED = "VERIFIED"
    RISKY = "RISKY"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"
    NOT_FOUND = "NOT_FOUND"


class Email(BaseModel):
    address: str
    status: EmailStatus = EmailStatus.UNKNOWN
    verification_method: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def deliverable(self) -> bool:
        return self.status in (EmailStatus.VERIFIED, EmailStatus.UNKNOWN) and "@" in self.address


# ── Stage 2: contacts ─────────────────────────────────────────────────
class Contact(BaseModel):
    company_domain: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[Email] = None
    # email hint sometimes returned already by the prospecting provider
    email_hint: Optional[str] = Field(default=None, repr=False)
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) if parts else (self.linkedin_url or "Unknown contact")

    @property
    def greeting_name(self) -> str:
        return self.first_name or (self.full_name.split()[0] if self.full_name else "there")

    @property
    def dedup_key(self) -> str:
        """Identity for de-duplication: prefer linkedin, fall back to name@domain."""
        if self.linkedin_url:
            return f"li::{self.linkedin_url.strip().lower().rstrip('/')}"
        return f"nm::{(self.display_name or '').lower()}@{self.company_domain}"

    @property
    def is_deliverable(self) -> bool:
        return self.email is not None and self.email.deliverable


# ── Stage 4: send result ──────────────────────────────────────────────
class SendStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SendResult(BaseModel):
    contact_name: str
    email: Optional[str] = None
    status: SendStatus
    message_id: Optional[str] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


# ── Approval gate payload ─────────────────────────────────────────────
class Review(BaseModel):
    seed_domain: str
    companies: int
    contacts: int
    deliverable: int
    skipped: int
    sample_to: Optional[str] = None
    sample_subject: Optional[str] = None
    sample_body: Optional[str] = None
    sendable: list[Contact] = Field(default_factory=list, repr=False)


# ── Final pipeline result ─────────────────────────────────────────────
class PipelineResult(BaseModel):
    seed_domain: str
    status: str
    companies: list[Company] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    results: list[SendResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    @property
    def stats(self) -> dict[str, int]:
        return {
            "companies": len(self.companies),
            "contacts": len(self.contacts),
            "deliverable": sum(1 for c in self.contacts if c.is_deliverable),
            "sent": sum(1 for r in self.results if r.status == SendStatus.SENT),
            "failed": sum(1 for r in self.results if r.status == SendStatus.FAILED),
            "skipped": sum(1 for r in self.results if r.status == SendStatus.SKIPPED),
        }
