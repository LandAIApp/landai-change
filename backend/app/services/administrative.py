"""Departments / municipalities from the municipal FeatureCollection (shared with Wildfire)."""
from __future__ import annotations

from functools import lru_cache

import ee

from ..core.config import get_settings
from ..core.earth_engine import ensure_initialized, evaluate
from ..core.errors import DepartmentNotFoundError

DEPARTMENT_FIELD = 'ADM1_ES'
MUNICIPALITY_FIELD = 'ADM2_ES'
MUNICIPALITY_CODE_FIELD = 'ADM2_PCODE'  # declared by the asset; unused by the method


def municipalities_collection() -> ee.FeatureCollection:
    ensure_initialized()
    return ee.FeatureCollection(get_settings().municipalities_asset)


@lru_cache(maxsize=1)
def _departments() -> tuple[str, ...]:
    values = evaluate(
        municipalities_collection().aggregate_array(DEPARTMENT_FIELD).distinct().sort(),
        'loading departments')
    return tuple(values or ())


@lru_cache(maxsize=128)
def _municipalities(department: str) -> tuple[str, ...]:
    values = evaluate(
        municipalities_collection().filter(ee.Filter.eq(DEPARTMENT_FIELD, department))
        .aggregate_array(MUNICIPALITY_FIELD).distinct().sort(),
        'loading municipalities')
    return tuple(values or ())


def clear_cache() -> None:
    _departments.cache_clear()
    _municipalities.cache_clear()
    municipality_info.cache_clear()


def list_departments() -> list[str]:
    return list(_departments())


def list_municipalities(department: str) -> list[str]:
    values = _municipalities(department)
    if not values:
        raise DepartmentNotFoundError(f"Department '{department}' was not found.")
    return list(values)


def select_municipality(department: str, municipality: str) -> ee.FeatureCollection:
    """Department AND municipality name; all matches are merged (same as Wildfire)."""
    return (municipalities_collection()
            .filter(ee.Filter.eq(DEPARTMENT_FIELD, department))
            .filter(ee.Filter.eq(MUNICIPALITY_FIELD, municipality)))


def _walk(coords, acc):
    if coords and isinstance(coords[0], (int, float)):
        acc.append(coords)
    else:
        for c in coords or []:
            _walk(c, acc)


def geometry_bounds(geometry: dict) -> list[list[float]]:
    """[[south, west], [north, east]] from a GeoJSON geometry (Leaflet order)."""
    pts: list = []
    if geometry.get('type') == 'GeometryCollection':
        for g in geometry.get('geometries', []):
            _walk(g.get('coordinates'), pts)
    else:
        _walk(geometry.get('coordinates'), pts)
    if not pts:
        return [[-4.3, -79.0], [13.5, -66.8]]  # Colombia fallback
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


@lru_cache(maxsize=256)
def municipality_info(department: str, municipality: str) -> dict:
    """Area and simplified boundary of a municipality (cached: the asset is static).

    Two tiny evaluations the first time, none afterwards; the boundary is for DISPLAY only
    (the analysis uses the full-resolution geometry).
    """
    collection = select_municipality(department, municipality)
    matches = int(evaluate(collection.size(), 'resolving the municipality') or 0)
    if matches == 0:
        return {'matches': 0}
    geometry = collection.geometry()
    info = evaluate(ee.Dictionary({
        'area_ha': geometry.area(100).divide(10000),
        'boundary': geometry.simplify(100),
    }), 'measuring the municipality')
    boundary_geometry = info['boundary']
    return {
        'matches': matches,
        'hectares': float(info['area_ha']),
        'boundary': {'type': 'Feature', 'properties': {}, 'geometry': boundary_geometry},
        'bounds': geometry_bounds(boundary_geometry),
    }
