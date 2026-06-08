"""Stage 4 provider — Brevo outreach send.

Two transports:
  • rest  — POST {base}/v3/smtp/email, header `api-key`   (needs an `xkeysib-` API v3 key)
  • smtp  — Brevo SMTP relay via aiosmtplib                 (works with an `xsmtpsib-` SMTP key)

`auto` picks smtp when the key looks like an SMTP key, else rest. Every send
carries a List-Unsubscribe header for CAN-SPAM / GDPR compliance.
"""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import make_msgid
from typing import Optional

import aiosmtplib

from ..config import Settings
from ..errors import AuthError, ConfigError
from ..http import ProviderHTTP
from ..logging import get_logger, redact_email
from ._util import first

log = get_logger("brevo")


class BrevoClient:
    provider = "brevo"

    def __init__(self, http: ProviderHTTP, settings: Settings) -> None:
        self._http = http
        self._s = settings
        self._url = f"{settings.brevo_base_url.rstrip('/')}/v3/smtp/email"
        self.transport = settings.resolved_brevo_transport

    async def send(
        self,
        *,
        to_email: str,
        to_name: str,
        subject: str,
        html: str,
        text: str,
        unsubscribe_url: Optional[str] = None,
    ) -> str:
        # Safety redirect: send everything to one controlled inbox when set.
        if self._s.test_recipient:
            subject = f"[demo → {to_name} <{to_email}>] {subject}"
            to_email = self._s.test_recipient
        if self.transport == "smtp":
            mid = await self._send_smtp(to_email, to_name, subject, html, text, unsubscribe_url)
        else:
            mid = await self._send_rest(to_email, to_name, subject, html, text, unsubscribe_url)
        log.info("Brevo[%s] sent to %s (msg %s)", self.transport, redact_email(to_email), mid)
        return mid

    # ── REST ─────────────────────────────────────────────────────────
    async def _send_rest(self, to_email, to_name, subject, html, text, unsub) -> str:
        headers = {"api-key": self._s.brevo_api_key, "Content-Type": "application/json",
                   "accept": "application/json"}
        body: dict = {
            "sender": {"name": self._s.sender_name, "email": self._s.sender_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
            "tags": ["coldwire-outreach"],
        }
        if self._s.reply_to_email:
            body["replyTo"] = {"email": self._s.reply_to_email}
        if unsub:
            body["headers"] = {
                "List-Unsubscribe": f"<{unsub}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }
        payload = await self._http.request_json(
            self.provider, "POST", self._url, headers=headers, json=body
        )
        return str(first(payload, ("messageId", "message_id", "id"), "")) or "sent"

    # ── SMTP relay ───────────────────────────────────────────────────
    async def _send_smtp(self, to_email, to_name, subject, html, text, unsub) -> str:
        login = self._s.brevo_smtp_login or self._s.sender_email
        if not login:
            raise ConfigError("BREVO_SMTP_LOGIN (Brevo account email) required for smtp transport")

        msg = EmailMessage()
        msg["From"] = f"{self._s.sender_name} <{self._s.sender_email}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg["Subject"] = subject
        msg_id = make_msgid()
        msg["Message-ID"] = msg_id
        if self._s.reply_to_email:
            msg["Reply-To"] = self._s.reply_to_email
        if unsub:
            msg["List-Unsubscribe"] = f"<{unsub}>"
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._s.brevo_smtp_host,
                port=self._s.brevo_smtp_port,
                start_tls=True,
                username=login,
                password=self._s.brevo_api_key,
            )
        except aiosmtplib.SMTPAuthenticationError as exc:
            raise AuthError(f"Brevo SMTP auth failed: {exc}", provider=self.provider) from exc
        return msg_id.strip("<>")
