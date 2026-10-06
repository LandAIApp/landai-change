"""Spectral indices (NDVI, NBR, NDWI, NDBI) and their temporal differences."""
from __future__ import annotations

import ee

# index -> (positive band, negative band) in the harmonized band names
INDEX_BANDS = {
    'NDVI': ('NIR', 'Red'),
    'NBR': ('NIR', 'SWIR2'),
    'NDWI': ('Green', 'NIR'),
    'NDBI': ('SWIR1', 'NIR'),
}
DELTA_BANDS = tuple(f'd{name}' for name in INDEX_BANDS)


def compute_indices(composite: ee.Image) -> ee.Image:
    """Return a 4-band image: NDVI, NBR, NDWI, NDBI (same mapping for both periods)."""
    return ee.Image.cat(*[
        composite.normalizedDifference(list(bands)).rename(name)
        for name, bands in INDEX_BANDS.items()
    ])


def index_differences(indices_a: ee.Image, indices_b: ee.Image) -> ee.Image:
    """dIndex = Index_B - Index_A, for all four indices."""
    return ee.Image.cat(*[
        indices_b.select(name).subtract(indices_a.select(name)).rename(f'd{name}')
        for name in INDEX_BANDS
    ])
