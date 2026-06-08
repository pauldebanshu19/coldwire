"""Request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobIn(BaseModel):
    seed_domain: str = Field(min_length=3, max_length=255)
    reply_to: Optional[EmailStr] = None   # where replies go; From stays the verified sender


class ApproveIn(BaseModel):
    # set at the approval gate; From email stays the verified Brevo sender.
    sender_name: Optional[str] = Field(default=None, max_length=120)
    reply_to: Optional[EmailStr] = None
    send_to: Optional[EmailStr] = None   # deliver every email to this inbox instead of the prospects

    @field_validator("sender_name")
    @classmethod
    def _no_header_injection(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if any(ch in v for ch in ("\r", "\n", "\x00")):
            raise ValueError("sender_name must not contain control characters")
        return v.strip() or None


class JobOut(BaseModel):
    id: str
    seed_domain: str
    status: str
    stats: dict
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ContactOut(BaseModel):
    name: str
    title: Optional[str] = None
    company_domain: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    deliverable: bool = False


class ReviewOut(BaseModel):
    job_id: str
    status: str
    companies: int
    contacts: int
    deliverable: int
    skipped: int
    template_subject: Optional[str] = None
    sample_to: Optional[str] = None
    sample_subject: Optional[str] = None
    sample_body: Optional[str] = None


class ResultRow(BaseModel):
    contact: str
    email: Optional[str] = None
    status: str
    message_id: Optional[str] = None
    error: Optional[str] = None


class ResultsOut(BaseModel):
    job_id: str
    status: str
    stats: dict
    results: list[ResultRow]
