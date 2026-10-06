from __future__ import annotations

from pydantic import BaseModel


class RateLimitItem(BaseModel):
    count: int
    per: str


class PublicConfig(BaseModel):
    """Limits shown to the user. The UI never hard-codes them."""

    max_aoi_hectares: float
    warn_aoi_hectares: float
    min_aoi_hectares: float
    max_polygon_vertices: int
    window_days: int
    analysis_scale_m: int
    min_date: str
    rate_limits: list[RateLimitItem]
    beta: bool = True
