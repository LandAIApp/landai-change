"""AOI-relative percentiles, three-level classification and connected-pixel cleaning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import ee

from . import config as C

Number = Union[float, ee.Number]
BAND = 'ChangeMagnitude'


@dataclass(frozen=True)
class Thresholds:
    """P50 / P90 / P95 of ChangeMagnitude. Floats (evaluated) or ee.Numbers (deferred)."""

    p50: Number
    p90: Number
    p95: Number

    @classmethod
    def from_values(cls, values: dict) -> 'Thresholds':
        """Build from an evaluated percentile dictionary. Raises ValueError when empty."""
        try:
            p50, p90, p95 = (values[f'{BAND}_p{p}'] for p in C.PERCENTILES)
        except KeyError as exc:
            raise ValueError('percentiles missing') from exc
        if p50 is None or p90 is None or p95 is None:
            raise ValueError('no valid pixels')
        return cls(float(p50), float(p90), float(p95))

    @classmethod
    def deferred(cls, dictionary: ee.Dictionary) -> 'Thresholds':
        """Server-side thresholds, used when the whole analysis is kept as one graph."""
        p50, p90, p95 = (ee.Number(dictionary.get(f'{BAND}_p{p}')) for p in C.PERCENTILES)
        return cls(p50, p90, p95)

    def as_floats(self) -> dict[str, float]:
        return {'p50': float(self.p50), 'p90': float(self.p90), 'p95': float(self.p95)}  # type: ignore[arg-type]


def percentile_dictionary(magnitude: ee.Image, aoi: ee.Geometry) -> ee.Dictionary:
    """P50/P90/P95 of ChangeMagnitude over the AOI (20 m, no bestEffort)."""
    return magnitude.reduceRegion(
        reducer=ee.Reducer.percentile(list(C.PERCENTILES)),
        geometry=aoi,
        scale=C.ANALYSIS_SCALE,
        maxPixels=C.MAX_PIXELS,
        tileScale=C.TILE_SCALE,
    )


def classify(magnitude: ee.Image, thresholds: Thresholds, aoi: ee.Geometry) -> ee.Image:
    """1 = < P50 (stable) ; 2 = P50..P90 (moderate) ; 3 = >= P90 (high). Valid data only."""
    return (ee.Image(0)
            .where(magnitude.lt(thresholds.p50), 1)
            .where(magnitude.gte(thresholds.p50).And(magnitude.lt(thresholds.p90)), 2)
            .where(magnitude.gte(thresholds.p90), 3)
            .rename('ChangeClass')
            .updateMask(magnitude.mask())
            .clip(aoi))


def high_change_p95(magnitude: ee.Image, thresholds: Thresholds, aoi: ee.Geometry) -> ee.Image:
    """Binary high-change mask (magnitude >= P95), selfMasked for visualization."""
    return magnitude.gte(thresholds.p95).rename('HighChangeP95').selfMask().clip(aoi)


def clean_high_change(change_class: ee.Image, aoi: ee.Geometry,
                      min_pixels: int = C.MIN_CONNECTED_PIXELS) -> ee.Image:
    """Class-3 pixels kept only when 8-connected patches have >= min_pixels pixels.

    The class-3 mask is selfMasked BEFORE counting (as Wildfire does): the Landsat
    reference counted connections on a 0/1 image and therefore also kept zero-valued
    pixels, which would inflate area statistics.
    """
    high = change_class.eq(3).selfMask()
    connected = high.connectedPixelCount(C.CONNECTED_MAX_SIZE, True)
    return high.updateMask(connected.gte(min_pixels)).rename('HighChangeClean').clip(aoi)
