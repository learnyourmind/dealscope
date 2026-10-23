"""Environment-driven configuration (spec §6.3). No setting here is a secret."""

import os
from dataclasses import dataclass
from typing import Tuple


def _float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Config:
    app_env: str = "development"
    app_version: str = "dev"
    cors_origins: Tuple[str, ...] = ()
    property_provider: str = "disabled"
    connect_timeout_s: float = 3.0
    read_timeout_s: float = 8.0
    request_budget_s: float = 15.0
    rate_limit: str = "20/minute"
    log_level: str = "INFO"
    max_body_bytes: int = 8 * 1024

    @classmethod
    def from_env(cls) -> "Config":
        origins = tuple(
            o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
        )
        return cls(
            app_env=os.environ.get("APP_ENV", "development"),
            app_version=os.environ.get("APP_VERSION")
            or os.environ.get("VERCEL_GIT_COMMIT_SHA", "dev")[:7],
            cors_origins=origins,
            # Off by default: the unofficial Redfin endpoint needs terms review (spec §7, D-01).
            property_provider=os.environ.get("PROPERTY_PROVIDER", "disabled").strip().lower(),
            connect_timeout_s=_float("UPSTREAM_CONNECT_TIMEOUT_S", 3.0),
            read_timeout_s=_float("UPSTREAM_READ_TIMEOUT_S", 8.0),
            rate_limit=os.environ.get("RATE_LIMIT", "20/minute"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
