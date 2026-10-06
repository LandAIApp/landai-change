"""Resolve the requested area (municipality or drawn polygon) and apply the free-tier limits."""
from __future__ import annotations

from dataclasses import dataclass

import ee

from ..core.config import Settings
from ..core.earth_engine import ensure_initialized
from ..core.geometry import ring_bounds, validate_polygon
from ..schemas.change import ChangeRequest, Issue
from . import administrative
from .issues import make_issue


@dataclass
class ResolvedAOI:
    kind: str                       # 'municipality' | 'drawn'
    label: str
    geometry: ee.Geometry
    hectares: float
    boundary: dict                  # GeoJSON Feature (display)
    bounds: list[list[float]]
    department: str | None = None
    municipality: str | None = None


def limit_issues(hectares: float, kind: str, settings: Settings) -> tuple[list[Issue], list[Issue]]:
    """(blocking, warnings) for the area limits of the public beta."""
    blocking: list[Issue] = []
    warnings: list[Issue] = []
    if hectares > settings.max_aoi_hectares:
        blocking.append(make_issue('aoi_too_large', hectares=hectares, max=settings.max_aoi_hectares))
    elif hectares > settings.warn_aoi_hectares:
        warnings.append(make_issue('aoi_large', hectares=hectares, warn=settings.warn_aoi_hectares))
    if kind == 'drawn' and hectares < settings.min_aoi_hectares:
        blocking.append(make_issue('aoi_too_small', hectares=hectares, min=settings.min_aoi_hectares))
    return blocking, warnings


def resolve_aoi(req: ChangeRequest, settings: Settings) -> tuple[ResolvedAOI | None, list[Issue], list[Issue]]:
    """Return (aoi, blocking, warnings). `aoi` is None when it cannot be used."""
    if req.geometry is not None:
        return _resolve_drawn(req, settings)
    return _resolve_municipality(req, settings)


def _resolve_drawn(req: ChangeRequest, settings: Settings):
    check = validate_polygon(req.geometry.coordinates, settings.max_polygon_vertices)  # type: ignore[union-attr]
    if check.ring is None:
        return None, [make_issue(code, **params) for code, params in check.issues], []
    hectares = float(check.hectares or 0)
    blocking, warnings = limit_issues(hectares, 'drawn', settings)
    if blocking:  # rejected locally: no Earth Engine object is even built
        return None, blocking, warnings
    # Planar edges (what the user sees on the map), not geodesics.
    ensure_initialized()
    geometry = ee.Geometry.Polygon([check.ring], None, False)
    aoi = ResolvedAOI(
        kind='drawn', label='drawn', geometry=geometry, hectares=hectares,
        boundary={'type': 'Feature', 'properties': {},
                  'geometry': {'type': 'Polygon', 'coordinates': [check.ring]}},
        bounds=ring_bounds(check.ring))
    return aoi, blocking, warnings


def _resolve_municipality(req: ChangeRequest, settings: Settings):
    department, municipality = req.department or '', req.municipality or ''
    info = administrative.municipality_info(department, municipality)
    if not info.get('matches'):
        return None, [make_issue('municipality_not_found', department=department,
                                 municipality=municipality)], []
    hectares = float(info['hectares'])
    blocking, warnings = limit_issues(hectares, 'municipality', settings)
    aoi = ResolvedAOI(
        kind='municipality', label=f'{municipality}, {department}',
        geometry=administrative.select_municipality(department, municipality).geometry(),
        hectares=hectares, boundary=info['boundary'], bounds=info['bounds'],
        department=department, municipality=municipality)
    return (None if blocking else aoi), blocking, warnings
