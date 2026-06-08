"""ORM models — mirrors PRD §4. Durable state for jobs and every entity
discovered. JSONB on Postgres, JSON elsewhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


# Job status values (see PRD §5)
JOB_STATUSES = (
    "QUEUED", "SOURCING", "PROSPECTING", "RESOLVING",
    "AWAITING_APPROVAL", "SENDING", "COMPLETED", "FAILED", "CANCELLED",
)


class User(Base):
    __tablename__ = "users"
    # id mirrors the Supabase user id (sub). Auth lives in Supabase; this row
    # exists only so jobs stay relationally scoped to a user.
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True, default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")  # unused (Supabase)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship(back_populates="user")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    seed_domain: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stats: Mapped[dict] = mapped_column(JSONType, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_job_user_idem"),
    )

    user: Mapped["User"] = relationship(back_populates="jobs")
    companies: Mapped[list["Company"]] = relationship(
        back_populates="job", cascade="all, delete-orphan")
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="job", cascade="all, delete-orphan")


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    domain: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONType, default=dict)

    __table_args__ = (UniqueConstraint("job_id", "domain", name="uq_company_job_domain"),)

    job: Mapped["Job"] = relationship(back_populates="companies")
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONType, default=dict)

    __table_args__ = (
        UniqueConstraint("company_id", "linkedin_url", name="uq_contact_company_li"),
    )

    company: Mapped["Company"] = relationship(back_populates="contacts")
    job: Mapped["Job"] = relationship()
    email: Mapped["Email | None"] = relationship(
        back_populates="contact", uselist=False, cascade="all, delete-orphan")
    outreach: Mapped["Outreach | None"] = relationship(
        back_populates="contact", uselist=False, cascade="all, delete-orphan")


class Email(Base):
    __tablename__ = "emails"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), unique=True, index=True)
    address: Mapped[str] = mapped_column(String(320))
    verification_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    deliverable: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contact: Mapped["Contact"] = relationship(back_populates="email")


class Outreach(Base):
    __tablename__ = "outreach"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contact_id: Mapped[str] = mapped_column(ForeignKey("contacts.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    brevo_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    contact: Mapped["Contact"] = relationship(back_populates="outreach")
