"""Area statistics (hectares) computed server-side with a single reduceRegion."""
from __future__ import annotations

import ee

from . import config as C

AREA_KEYS = (
    'stable_ha', 'moderate_change_ha', 'high_change_ha',
    'p95_change_ha', 'clean_high_change_ha', 'total_aoi_ha',
)


def area_dictionary(change_class: ee.Image, high_p95: ee.Image, high_clean: ee.Image,
                    aoi: ee.Geometry) -> ee.Dictionary:
    """Sum of pixelArea()/10000 per class, at 20 m. Missing pixels count as 0 ha."""
    hectares = ee.Image.pixelArea().divide(10000)
    stack = ee.Image.cat([
        hectares.updateMask(change_class.eq(1)).rename('stable_ha'),
        hectares.updateMask(change_class.eq(2)).rename('moderate_change_ha'),
        hectares.updateMask(change_class.eq(3)).rename('high_change_ha'),
        hectares.updateMask(high_p95).rename('p95_change_ha'),
        hectares.updateMask(high_clean).rename('clean_high_change_ha'),
        hectares.rename('total_aoi_ha'),
    ]).unmask(0)
    return stack.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=C.ANALYSIS_SCALE,
        maxPixels=C.MAX_PIXELS,
        tileScale=C.TILE_SCALE,
    )


def _pct(part: float, total: float) -> float:
    return round(100.0 * part / total, 4) if total > 0 else 0.0


def add_percentages(raw: dict) -> dict:
    """Normalize the evaluated areas and derive percentages of the AOI.

    Pure arithmetic on server-computed hectares (nothing is measured client-side).
    """
    areas = {key: float(raw.get(key) or 0.0) for key in AREA_KEYS}
    total = areas['total_aoi_ha']
    valid = areas['stable_ha'] + areas['moderate_change_ha'] + areas['high_change_ha']
    return {
        **areas,
        'valid_data_ha': valid,
        'stable_pct': _pct(areas['stable_ha'], total),
        'moderate_change_pct': _pct(areas['moderate_change_ha'], total),
        'high_change_pct': _pct(areas['high_change_ha'], total),
        'p95_change_pct': _pct(areas['p95_change_ha'], total),
        'clean_high_change_pct': _pct(areas['clean_high_change_ha'], total),
        'valid_data_pct': _pct(valid, total),
    }
