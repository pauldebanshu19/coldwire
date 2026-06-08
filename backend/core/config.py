"""Settings loaded from environment / .env (Pydantic Settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # ── Provider credentials ──
    ocean_api_key: str = ""
    prospeo_api_key: str = ""
    brevo_api_key: str = ""

    # ── Provider base URLs (overridable for the mock stub server) ──
    ocean_base_url: str = "https://api.ocean.io"
    prospeo_base_url: str = "https://api.prospeo.io"
    brevo_base_url: str = "https://api.brevo.com"

    # ── Brevo transport ──
    brevo_transport: Literal["auto", "rest", "smtp"] = "auto"
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_login: str = ""

    # ── Sender identity (configure via env — must be a verified sender) ──
    sender_email: str = ""
    sender_name: str = "Coldwire"
    reply_to_email: str = ""

    # Safety: when set, ALL outreach is redirected to this single address
    # instead of the real prospects (safe demos / testing). Empty = real send.
    test_recipient: str = ""

    # ── Pipeline tuning ──
    mock: bool = False
    max_companies: int = 15
    max_contacts_per_company: int = 5
    prospect_concurrency: int = 3
    resolve_concurrency: int = 3
    send_concurrency: int = 3

    # ── Rate limits (req/sec, enforced by a shared token bucket) ──
    # Prospeo's limit is strict — keep these conservative; 429s are retried.
    ocean_rps: float = 2
    prospeo_rps: float = 1
    brevo_rps: float = 5

    # ── HTTP retry ──
    http_timeout: float = 30.0
    max_retries: int = 4

    # ── Cache / Redis ──
    # When redis_url is set, the result cache and the rate-limit token buckets
    # become Redis-backed and GLOBAL across all worker processes.
    redis_url: str = ""
    cache_enabled: bool = True
    cache_dir: str = ".cache"
    cache_ttl_seconds: int = 86_400

    # ── Compliance ──
    unsubscribe_base_url: str = ""

    log_level: str = "INFO"

    # ── Derived ──
    @property
    def resolved_brevo_transport(self) -> Literal["rest", "smtp"]:
        if self.brevo_transport != "auto":
            return self.brevo_transport  # type: ignore[return-value]
        # SMTP keys look like `xsmtpsib-...`; REST API keys like `xkeysib-...`.
        if self.brevo_api_key.startswith("xsmtpsib"):
            return "smtp"
        return "rest"

    def provider_rps(self, provider: str) -> float:
        return float(getattr(self, f"{provider}_rps", 2))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def fresh_settings(**overrides) -> Settings:
    """Build settings ignoring the cache (used by the CLI for flag overrides)."""
    base = Settings().model_dump()
    base.update({k: v for k, v in overrides.items() if v is not None})
    return Settings(**base)
