"""Data-availability preflight: cheap checks first, one small Earth Engine call last."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import ee

from ..change import config as C
from ..change.sentinel import Period, build_period, scene_counts
from ..core.config import get_settings
from ..core.earth_engine import evaluate
from ..core.geometry import validate_polygon
from ..schemas.change import ChangeRequest, Issue, PreflightResponse
from .aoi import ResolvedAOI, resolve_aoi
from .issues import make_issue


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _window_fields(period_a: Period, period_b: Period) -> dict:
    return {
        'period_a_start': period_a.start.isoformat(), 'period_a_end': period_a.end.isoformat(),
        'period_b_start': period_b.start.isoformat(), 'period_b_end': period_b.end.isoformat(),
    }


def _date_issues(req: ChangeRequest, period_b: Period) -> tuple[list[Issue], list[Issue]]:
    settings = get_settings()
    blocking: list[Issue] = []
    warnings: list[Issue] = []
    if req.date_b <= req.date_a:
        blocking.append(make_issue('invalid_dates'))
    if req.date_a < date.fromisoformat(settings.min_date):
        blocking.append(make_issue('date_too_early', min_date=settings.min_date))
    if req.date_b > _today():
        blocking.append(make_issue('future_date'))
    if not blocking:
        if (req.date_b - req.date_a).days <= 2 * C.WINDOW_DAYS:
            warnings.append(make_issue('periods_overlap', days=2 * C.WINDOW_DAYS))
        if period_b.end > _today():
            warnings.append(make_issue('period_incomplete'))
    return blocking, warnings


def _blocked_hectares(req: ChangeRequest, settings) -> float | None:
    """Area of a rejected drawn polygon, so the UI can say how far over the limit it is."""
    if req.geometry is None:
        return None
    return validate_polygon(req.geometry.coordinates, settings.max_polygon_vertices).hectares


def preflight_core(req: ChangeRequest) -> tuple[PreflightResponse, ResolvedAOI | None]:
    """Run every check. The resolved AOI is returned so the analysis does not repeat work."""
    settings = get_settings()
    period_a, period_b = build_period(req.date_a), build_period(req.date_b)
    blocking, warnings = _date_issues(req, period_b)

    if blocking:  # bad dates: skip AOI resolution (no Earth Engine work for a doomed request)
        aoi = None
    else:
        aoi, aoi_blocking, aoi_warnings = resolve_aoi(req, settings)
        blocking += aoi_blocking
        warnings += aoi_warnings

    base = {**_window_fields(period_a, period_b),
            'aoi_kind': aoi.kind if aoi else ('drawn' if req.geometry else 'municipality'),
            'aoi_hectares': aoi.hectares if aoi else _blocked_hectares(req, settings)}

    if blocking or aoi is None:
        return PreflightResponse(status='blocked', valid=False, warnings=warnings,
                                 blocking_errors=blocking, **base), None

    counts = evaluate(scene_counts(aoi.geometry, period_a, period_b),
                      'checking Sentinel-2 availability')
    count_a, count_b = int(counts['period_a']), int(counts['period_b'])
    if count_a < 1:
        blocking.append(make_issue('no_images_period_a'))
    elif count_a < C.FEW_SCENES_THRESHOLD:
        warnings.append(make_issue('few_scenes_a', count=count_a))
    if count_b < 1:
        blocking.append(make_issue('no_images_period_b'))
    elif count_b < C.FEW_SCENES_THRESHOLD:
        warnings.append(make_issue('few_scenes_b', count=count_b))

    response = PreflightResponse(
        status='blocked' if blocking else 'ok', valid=not blocking,
        period_a_count=count_a, period_b_count=count_b,
        warnings=warnings, blocking_errors=blocking, **base)
    return response, (None if blocking else aoi)


def run_preflight(req: ChangeRequest) -> PreflightResponse:
    return preflight_core(req)[0]
