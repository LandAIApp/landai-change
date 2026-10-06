"""Visualization parameters for every map layer (centralized, per the brief)."""
from __future__ import annotations

RGB = {'bands': ['Red', 'Green', 'Blue'], 'min': 0.02, 'max': 0.30, 'gamma': 1.2}

# Palettes follow the Landsat reference script; ranges for the new index layers are
# symmetric around zero like the reference dNDVI / dNBR.
CHANGE_MAGNITUDE = {'min': 0, 'max': 0.09, 'palette': ['ffffff', 'cac859', 'f10808']}
SPECTRAL_ANGLE = {'min': 0, 'max': 1, 'palette': ['ffffff', '00ffff', '0000ff', '800080']}
D_NDVI = {'min': -0.5, 'max': 0.5, 'palette': ['ff0000', 'ffffff', '008000']}
D_NBR = {'min': -0.5, 'max': 0.5, 'palette': ['ff0000', 'ffffff', '0000ff']}
D_NDWI = {'min': -0.5, 'max': 0.5, 'palette': ['8c510a', 'f5f5f5', '01665e']}
D_NDBI = {'min': -0.5, 'max': 0.5, 'palette': ['5e3c99', 'f7f7f7', 'e66101']}
CHANGE_CLASS = {'min': 1, 'max': 3, 'palette': ['2ca25f', 'fee08b', 'd73027']}  # stable / moderate / high
HIGH_CHANGE = {'min': 0, 'max': 1, 'palette': ['ff0000']}
