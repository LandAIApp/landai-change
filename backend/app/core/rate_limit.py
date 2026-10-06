"""SlowAPI limiter, kept in its own module to avoid circular imports.

Only POST /api/v1/change/analyze is decorated with it. The limit string comes from the
RATE_LIMIT_ANALYZE setting (default "5/hour;20/day"). The counters live in memory: with
Cloud Run max-instances=1 they are exact while the instance is alive and reset when it
scales to zero (see docs/deployment.md).
"""
from __future__ import annotations

import time

from limits import parse_many
from slowapi import Limiter
from starlette.requests import Request

from .config import get_settings


def client_key(request: Request) -> str:
    """Client identifier used for the counters (never logged)."""
    settings = get_settings()
    if settings.trust_forwarded_for:
        parts = [p.strip() for p in request.headers.get('x-forwarded-for', '').split(',') if p.strip()]
        if parts:
            # Cloud Run appends the real client IP; entries to its left are client-supplied.
            hops = max(1, settings.trusted_proxy_hops)
            return parts[-hops] if len(parts) >= hops else parts[0]
    return request.client.host if request.client else 'unknown'


limiter = Limiter(key_func=client_key, enabled=get_settings().rate_limit_enabled)


def analyze_limit() -> str:
    """Evaluated on every request, so tests and ops can change it via settings."""
    return get_settings().rate_limit_analyze


def describe_limits(spec: str | None = None) -> list[dict]:
    """[{'count': 5, 'per': 'hour'}, {'count': 20, 'per': 'day'}] for the public config."""
    items = parse_many(spec or get_settings().rate_limit_analyze)
    return [{'count': item.amount, 'per': item.GRANULARITY.name} for item in items]


def retry_after_seconds(request: Request) -> int | None:
    """Seconds until the exceeded window resets (None when unknown)."""
    view = getattr(request.state, 'view_rate_limit', None)
    if not view:
        return None
    try:
        reset_at, _remaining = limiter.limiter.get_window_stats(*view)
        return max(1, int(reset_at - time.time()) + 1)
    except Exception:  # noqa: BLE001 - best effort only
        return None
