"""Full change analysis: preflight -> thresholds -> classes/areas -> map tiles."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ..change import config as C
from ..change.areas import add_percentages, area_dictionary
from ..change.classification import Thresholds
from ..change.sentinel import build_period
from ..change.pipeline import build_inputs, build_outputs, threshold_request
from ..core.earth_engine import evaluate
from ..core.errors import NoValidPixelsError, PreflightFailedError
from ..core.gate import analysis_slot
from ..core.logging import log_analysis
from ..schemas.change import (
    AnalyzeResponse, AoiInfo, AreaStatistics, ChangeRequest, DateRange, DateWindows, Metadata,
    Percentiles,
)
from .issues import make_issue
from .preflight import preflight_core
from .tiles import build_layers


def run_analysis(req: ChangeRequest) -> AnalyzeResponse:
    started = time.monotonic()
    log: dict = {'date_a': req.date_a.isoformat(), 'date_b': req.date_b.isoformat(),
                 'aoi_kind': 'drawn' if req.geometry else 'municipality',
                 'department': req.department, 'municipality': req.municipality,
                 'success': False}
    try:
        with analysis_slot():
            response = _analyze(req, log)
        log.update(success=True)
        return response
    except Exception as exc:  # noqa: BLE001 - logged, then re-raised unchanged
        log['error_code'] = getattr(exc, 'code', type(exc).__name__)
        raise
    finally:
        log['duration_seconds'] = round(time.monotonic() - started, 2)
        log_analysis(**log)


def _analyze(req: ChangeRequest, log: dict) -> AnalyzeResponse:
    preflight, aoi = preflight_core(req)
    log.update(aoi_hectares=preflight.aoi_hectares, period_a_count=preflight.period_a_count,
               period_b_count=preflight.period_b_count)
    if not preflight.valid or aoi is None:
        raise PreflightFailedError('The request did not pass the preflight checks.',
                                   details=[e.model_dump() for e in preflight.blocking_errors])
    warnings = list(preflight.warnings)

    period_a, period_b = build_period(req.date_a), build_period(req.date_b)

    inputs = build_inputs(aoi.geometry, period_a, period_b)
    # Stage 1 -> API boundary: percentiles are the only value evaluated before the tiles.
    raw = evaluate(threshold_request(inputs, aoi.geometry), 'computing change percentiles')
    try:
        thresholds = Thresholds.from_values(raw or {})
    except ValueError as exc:
        raise NoValidPixelsError(
            'No valid (cloud-free) pixels in both periods for this area. '
            'Try other dates or a different area.') from exc
    log.update(thresholds.as_floats())

    outputs = build_outputs(inputs, aoi.geometry, thresholds)
    areas = add_percentages(evaluate(
        area_dictionary(outputs.change_class, outputs.high_p95, outputs.high_clean, aoi.geometry),
        'computing area statistics'))
    log.update(high_change_ha=areas['high_change_ha'],
               clean_high_change_ha=areas['clean_high_change_ha'])

    if areas['total_aoi_ha'] <= 0 or areas['valid_data_ha'] <= 0:
        raise NoValidPixelsError('No valid pixels remained after cloud masking.')
    if areas['valid_data_pct'] < C.LOW_COVERAGE_PCT:
        warnings.append(make_issue('low_coverage', pct=areas['valid_data_pct']))
    if areas['clean_high_change_ha'] <= 0:
        warnings.append(make_issue('no_clean_high_change'))

    layers, layer_warnings = build_layers(inputs, outputs)
    warnings += layer_warnings

    th = thresholds.as_floats()
    return AnalyzeResponse(
        status='ok',
        metadata=Metadata(
            method='Change Vector Analysis (CVA) + spectral angle, AOI-relative percentiles',
            data='Sentinel-2 SR Harmonized + Cloud Score+',
            resolution_m=C.ANALYSIS_SCALE, window_days=C.WINDOW_DAYS,
            min_connected_pixels=C.MIN_CONNECTED_PIXELS,
            thresholds='P50 / P90 / P95 of ChangeMagnitude within the AOI',
            date_a=req.date_a.isoformat(), date_b=req.date_b.isoformat(),
            aoi=AoiInfo(kind=aoi.kind, label=aoi.label, hectares=aoi.hectares,
                        department=aoi.department, municipality=aoi.municipality)),
        image_counts={'period_a': int(preflight.period_a_count or 0),
                      'period_b': int(preflight.period_b_count or 0)},
        date_windows=DateWindows(
            period_a=DateRange(start=period_a.start.isoformat(), end=period_a.end.isoformat()),
            period_b=DateRange(start=period_b.start.isoformat(), end=period_b.end.isoformat())),
        percentiles=Percentiles(**th),
        area_statistics=AreaStatistics(**areas),
        layers=layers, boundary=aoi.boundary, bounds=aoi.bounds, warnings=warnings,
        generated_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
