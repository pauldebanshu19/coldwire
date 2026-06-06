"""Outreach email copy + rendering.

Personalized per contact (name, role, company). Plain-text + HTML parts, plus a
compliant unsubscribe link. The copy is intentionally short and specific — a
mail you'd actually open beats a generic blast (the brief's bonus criterion).
"""

from __future__ import annotations

from urllib.parse import quote
from typing import Optional

from .config import Settings
from .models import Contact


def company_label(contact: Contact) -> str:
    """Human-ish company name from domain: `acme-logistics.com` -> `Acme Logistics`."""
    root = contact.company_domain.split(".")[0]
    return " ".join(w.capitalize() for w in root.replace("_", "-").split("-"))


def role_hook(contact: Contact) -> str:
    title = (contact.title or "").lower()
    if any(k in title for k in ("sales", "revenue", "growth", "gtm")):
        return "your team is probably spending hours each week sourcing accounts and chasing contact data"
    if any(k in title for k in ("ceo", "founder", "owner", "president")):
        return "pipeline that isn't built by hand is the difference between hitting plan and missing it"
    if any(k in title for k in ("market",)):
        return "getting clean, targeted account lists to sales is still mostly manual"
    return "the sourcing-to-outreach handoff is still mostly copy-paste for most teams"


def unsubscribe_url(settings: Settings, email: str) -> str:
    return f"{settings.unsubscribe_base_url}?e={quote(email)}"


def render(contact: Contact, settings: Settings) -> tuple[str, str, str]:
    """Return (subject, html, text) for one contact."""
    name = contact.greeting_name
    company = company_label(contact)
    hook = role_hook(contact)
    sender = settings.sender_name
    to_addr = contact.email.address if contact.email else ""
    unsub = unsubscribe_url(settings, to_addr) if to_addr else settings.unsubscribe_base_url

    subject = f"{company} — cut sourcing-to-outreach to one step?"

    text = f"""Hi {name},

I'll keep this short — {hook}.

I built an outreach engine that takes a single seed account and, with no
manual steps, finds lookalike companies, surfaces the decision-makers,
verifies their work emails, and queues personalized outreach. One input in,
a vetted contact list out.

Worth a 15-minute look to see if it fits how {company} runs outbound?

— {sender}

—
You received this because we think it's relevant to your role.
Unsubscribe: {unsub}
"""

    html = f"""\
<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:15px;line-height:1.55;color:#1a1a1a;max-width:560px">
<p>Hi {name},</p>
<p>I'll keep this short — {hook}.</p>
<p>I built an outreach engine that takes a single seed account and, with no
manual steps, finds lookalike companies, surfaces the decision-makers,
verifies their work emails, and queues personalized outreach.
<strong>One input in, a vetted contact list out.</strong></p>
<p>Worth a 15-minute look to see if it fits how {company} runs outbound?</p>
<p>— {sender}</p>
<hr style="border:none;border-top:1px solid #e5e5e5;margin:20px 0">
<p style="font-size:12px;color:#888">You received this because we think it's relevant to your role.
<br><a href="{unsub}" style="color:#888">Unsubscribe</a></p>
</body></html>"""

    return subject, html, text
