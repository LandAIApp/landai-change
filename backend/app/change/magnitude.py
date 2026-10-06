"""Change Vector Analysis: spectral magnitude and spectral angle."""
from __future__ import annotations

import math

import ee

from . import config as C


def vector_norm(image: ee.Image) -> ee.Image:
    """Euclidean norm across the bands of a multiband image."""
    return image.pow(2).reduce(ee.Reducer.sum()).sqrt()


def spectral_difference(composite_a: ee.Image, composite_b: ee.Image) -> ee.Image:
    """difference = Composite B - Composite A over the six change bands."""
    bands = list(C.BAND_NAMES)
    return composite_b.select(bands).subtract(composite_a.select(bands))


def change_magnitude(composite_a: ee.Image, composite_b: ee.Image, aoi: ee.Geometry) -> ee.Image:
    """sqrt(sum(diff^2)) / sqrt(number of bands), as in the Landsat reference."""
    difference = spectral_difference(composite_a, composite_b)
    return (vector_norm(difference).divide(math.sqrt(len(C.BAND_NAMES)))
            .rename('ChangeMagnitude').clip(aoi))


def spectral_angle(composite_a: ee.Image, composite_b: ee.Image, aoi: ee.Geometry) -> ee.Image:
    """acos(clamp(dot(A,B) / (|A| |B|), -1, 1)), radians, with an epsilon-protected denominator."""
    bands = list(C.BAND_NAMES)
    a, b = composite_a.select(bands), composite_b.select(bands)
    dot = a.multiply(b).reduce(ee.Reducer.sum())
    denominator = vector_norm(a).multiply(vector_norm(b)).max(C.EPSILON)
    return dot.divide(denominator).clamp(-1, 1).acos().rename('SpectralAngle').clip(aoi)
