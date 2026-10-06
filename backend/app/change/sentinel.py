"""Sentinel-2 selection, cloud masking and median composites for the two periods."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import ee

from . import config as C


@dataclass(frozen=True)
class Period:
    """Temporal window around a reference date: [center - N days, center + N days]."""

    center: date
    start: date  # inclusive
    end: date    # inclusive

    @property
    def ee_start(self) -> ee.Date:
        return ee.Date(self.start.isoformat())

    @property
    def ee_end_exclusive(self) -> ee.Date:
        """filterDate() excludes its end, so the last day is included by adding one day."""
        return ee.Date((self.end + timedelta(days=1)).isoformat())


def build_period(center: date, window_days: int = C.WINDOW_DAYS) -> Period:
    delta = timedelta(days=window_days)
    return Period(center=center, start=center - delta, end=center + delta)


def linked_collection() -> ee.ImageCollection:
    """S2 SR Harmonized linked with Cloud Score+ (adds the cs_cdf band)."""
    return ee.ImageCollection(C.S2_COLLECTION).linkCollection(
        ee.ImageCollection(C.CLOUD_SCORE_COLLECTION), [C.CLOUD_SCORE_BAND])


def scenes(aoi: ee.Geometry, period: Period) -> ee.ImageCollection:
    """Scenes intersecting the AOI inside the period (scene-level cloud filter only)."""
    return (linked_collection()
            .filterBounds(aoi)
            .filterDate(period.ee_start, period.ee_end_exclusive)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', C.SCENE_CLOUD_MAX)))


def mask_and_scale(image: ee.Image) -> ee.Image:
    """Cloud Score+ (cs_cdf >= .55) + SCL mask, six analysis bands, reflectance / 10000."""
    clear = image.select(C.CLOUD_SCORE_BAND).gte(C.CLEAR_THRESHOLD)
    scl = image.select('SCL')
    valid = scl.neq(C.EXCLUDED_SCL_CLASSES[0])
    for excluded in C.EXCLUDED_SCL_CLASSES[1:]:
        valid = valid.And(scl.neq(excluded))
    return (image.select(list(C.S2_BANDS), list(C.BAND_NAMES))
            .updateMask(clear).updateMask(valid)
            .divide(C.REFLECTANCE_SCALE)
            .copyProperties(image, ['system:time_start']))


def composite(aoi: ee.Geometry, period: Period) -> ee.Image:
    """Median composite of the masked scenes of one period, clipped to the AOI."""
    return scenes(aoi, period).map(mask_and_scale).median().clip(aoi)


def scene_counts(aoi: ee.Geometry, period_a: Period, period_b: Period) -> ee.Dictionary:
    """Number of scenes per period (single deferred dictionary, evaluated once)."""
    return ee.Dictionary({
        'period_a': scenes(aoi, period_a).size(),
        'period_b': scenes(aoi, period_b).size(),
    })
