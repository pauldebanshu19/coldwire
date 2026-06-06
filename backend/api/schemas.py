"""Request/response models for the API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobIn(BaseModel):
    seed_domain: str = Field(min_length=3, max_length=255)


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
