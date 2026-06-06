import httpx
import pytest

from core.cache import NullCache
from core.config import Settings
from core.http import ProviderHTTP
from core.models import Contact, Email, EmailStatus, Review
from core.pipeline import run_pipeline
from core.ratelimit import RateLimiterRegistry
from core.stages.prospect import find_contacts
from core.stages.send import sendable_contacts


def mock_settings(**kw) -> Settings:
    base = dict(mock=True, max_companies=4, max_contacts_per_company=2,
                send_concurrency=2, resolve_concurrency=4)
    base.update(kw)
    return Settings(**base)


async def test_end_to_end_mock_sends_when_approved():
    result = await run_pipeline(mock_settings(), "acme.com", approve=lambda r: True)
    assert result.status == "COMPLETED"
    assert result.stats["companies"] > 0
    assert result.stats["sent"] > 0
    # nobody mailed twice
    sent_emails = [r.email for r in result.results if r.status.value == "SENT"]
    assert len(sent_emails) == len(set(sent_emails))


async def test_gate_blocks_send_when_cancelled():
    result = await run_pipeline(mock_settings(), "acme.com", approve=lambda r: False)
    assert result.status == "CANCELLED"
    assert result.stats["sent"] == 0


async def test_no_approver_defaults_to_no_send():
    result = await run_pipeline(mock_settings(), "acme.com")
    assert result.status == "CANCELLED"
    assert result.stats["sent"] == 0


async def test_review_has_sample():
    seen: dict[str, Review] = {}

    def approve(r: Review) -> bool:
        seen["r"] = r
        return False

    await run_pipeline(mock_settings(), "acme.com", approve=approve)
    r = seen["r"]
    assert r.deliverable >= 0
    if r.deliverable:
        assert r.sample_subject and "@" in (r.sample_to or "")


def test_sendable_dedups_and_skips_undeliverable():
    contacts = [
        Contact(company_domain="x.com", full_name="A",
                email=Email(address="dup@x.com", status=EmailStatus.VERIFIED)),
        Contact(company_domain="x.com", full_name="B",
                email=Email(address="DUP@x.com", status=EmailStatus.VERIFIED)),  # same addr
        Contact(company_domain="x.com", full_name="C",
                email=Email(address="bad@x.com", status=EmailStatus.INVALID)),   # undeliverable
        Contact(company_domain="x.com", full_name="D"),                           # no email
    ]
    out = sendable_contacts(contacts)
    assert [c.full_name for c in out] == ["A"]


class _FlakyProspeo:
    """One company errors, one returns contacts — run must survive."""
    async def find_contacts(self, domain):
        if domain == "boom.com":
            from core.errors import RetryableError
            raise RetryableError("boom", provider="prospeo")
        return [Contact(company_domain=domain, full_name="OK Person",
                        linkedin_url=f"https://linkedin.com/in/{domain}")]


async def test_prospect_survives_partial_failure():
    from core.models import Company
    companies = [Company(domain="boom.com"), Company(domain="good.com")]
    contacts = await find_contacts(_FlakyProspeo(), companies, concurrency=2)
    assert [c.company_domain for c in contacts] == ["good.com"]
