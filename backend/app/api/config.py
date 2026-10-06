from __future__ import annotations

from fastapi import APIRouter

from ..change import config as C
from ..core.config import get_settings
from ..core.rate_limit import describe_limits
from ..schemas.config import PublicConfig

router = APIRouter(prefix='/api/v1')


@router.get('/config', response_model=PublicConfig)
def public_config() -> PublicConfig:
    s = get_settings()
    return PublicConfig(
        max_aoi_hectares=s.max_aoi_hectares, warn_aoi_hectares=s.warn_aoi_hectares,
        min_aoi_hectares=s.min_aoi_hectares, max_polygon_vertices=s.max_polygon_vertices,
        window_days=C.WINDOW_DAYS, analysis_scale_m=C.ANALYSIS_SCALE, min_date=s.min_date,
        rate_limits=describe_limits())
