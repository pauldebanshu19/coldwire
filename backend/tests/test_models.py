import pytest

from core.models import Company, Contact, Email, EmailStatus, normalize_domain


@pytest.mark.parametrize("raw,expected", [
    ("https://www.Acme.com/team?x=1", "acme.com"),
    ("HTTP://Foo.IO", "foo.io"),
    ("  bar.com.  ", "bar.com"),
    ("www.baz.co.uk", "baz.co.uk"),
])
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


def test_company_rejects_bad_domain():
    with pytest.raises(ValueError):
        Company(domain="not-a-domain")


def test_contact_dedup_key_prefers_linkedin():
    a = Contact(company_domain="x.com", full_name="A B",
                linkedin_url="https://linkedin.com/in/ab/")
    b = Contact(company_domain="x.com", full_name="A B",
                linkedin_url="https://LinkedIn.com/in/ab")
    assert a.dedup_key == b.dedup_key  # trailing slash + case normalized


def test_email_deliverable_rules():
    assert Email(address="a@b.com", status=EmailStatus.VERIFIED).deliverable
    assert not Email(address="a@b.com", status=EmailStatus.INVALID).deliverable
    assert not Email(address="bogus", status=EmailStatus.VERIFIED).deliverable
