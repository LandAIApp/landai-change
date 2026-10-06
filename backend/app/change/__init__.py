"""Sentinel-2 adaptation of the Landsat multitemporal change-detection method.

Every function here only BUILDS a deferred Earth Engine graph. Nothing is evaluated
(no getInfo) inside this package: evaluation happens at the API boundary
(app/services).
"""
