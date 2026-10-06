"""Centralized scientific constants of the Sentinel-2 change-detection method.

Everything that may need tuning later lives here; no other module hard-codes these
values. See docs/adaptation.md for the Landsat -> Sentinel-2 decisions.
"""
from __future__ import annotations

# --- Data ---------------------------------------------------------------------
S2_COLLECTION = 'COPERNICUS/S2_SR_HARMONIZED'
CLOUD_SCORE_COLLECTION = 'GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'
CLOUD_SCORE_BAND = 'cs_cdf'
CLEAR_THRESHOLD = 0.55                       # keep pixels with cs_cdf >= 0.55
EXCLUDED_SCL_CLASSES = (1, 3, 7, 8, 9, 10, 11)
SCENE_CLOUD_MAX = 85                         # CLOUDY_PIXEL_PERCENTAGE < 85 (same as Wildfire)
REFLECTANCE_SCALE = 10000                    # surface reflectance = DN / 10000

# Landsat 8 (Blue, Green, Red, NIR, SWIR1, SWIR2) -> Sentinel-2 equivalents
S2_BANDS = ('B2', 'B3', 'B4', 'B8A', 'B11', 'B12')
BAND_NAMES = ('Blue', 'Green', 'Red', 'NIR', 'SWIR1', 'SWIR2')

# --- Temporal design ------------------------------------------------------------
WINDOW_DAYS = 30                             # period = date -30 d ... date +30 d (inclusive)

# --- Analysis ---------------------------------------------------------------------
ANALYSIS_SCALE = 20                          # metres (NIR/SWIR native resolution)
PERCENTILES = (50, 90, 95)
MIN_CONNECTED_PIXELS = 7                     # ~2700 m2 at 20 m (Landsat: 3 px x 900 m2)
CONNECTED_MAX_SIZE = 100                     # connectedPixelCount(maxSize, eightConnected)
MAX_PIXELS = 1e9
TILE_SCALE = 4
EPSILON = 1e-6                               # protects zero denominators (spectral angle)

# --- User-facing quality heuristics (NOT part of the method) --------------------------
FEW_SCENES_THRESHOLD = 3                     # warn when a period has fewer scenes
LOW_COVERAGE_PCT = 70.0                      # warn when valid data covers less of the AOI

# --- Output band names -----------------------------------------------------------------
PRODUCT_BANDS = (
    'ChangeMagnitude', 'SpectralAngle', 'dNDVI', 'dNBR', 'dNDWI', 'dNDBI',
    'ChangeClass', 'HighChangeP95', 'HighChangeClean',
)
