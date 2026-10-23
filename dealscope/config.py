"""Environment-driven configuration (spec §6.3). No setting here is a secret."""

import os
from dataclasses import dataclass, field
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
    geocoder: str = "census"
    connect_timeout_s: float = 3.0
    read_timeout_s: float = 8.0
    request_budget_s: float = 15.0
    rate_limit: str = "20/minute"
    log_level: str = "INFO"
    max_body_bytes: int = 8 * 1024
    # Host secret. Never log or print it (repr=False keeps it out of tracebacks and logs).
    rentcast_api_key: str = field(default="", repr=False)

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
            geocoder=os.environ.get("GEOCODER", "census").strip().lower(),
            connect_timeout_s=_float("UPSTREAM_CONNECT_TIMEOUT_S", 3.0),
            read_timeout_s=_float("UPSTREAM_READ_TIMEOUT_S", 8.0),
            rate_limit=os.environ.get("RATE_LIMIT", "20/minute"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            rentcast_api_key=os.environ.get("RENTCAST_API_KEY", "").strip(),
        )
