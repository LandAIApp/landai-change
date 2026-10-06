from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

Position = Annotated[list[float], Field(min_length=2, max_length=3)]
Ring = Annotated[list[Position], Field(max_length=2000)]


class PolygonGeometry(BaseModel):
    """GeoJSON Polygon drawn by the user ([lon, lat] positions, outer ring only)."""

    type: Literal['Polygon']
    coordinates: Annotated[list[Ring], Field(min_length=1, max_length=5)]


class ChangeRequest(BaseModel):
    """Select the area EITHER by municipality OR by a drawn polygon."""

    department: str | None = Field(None, min_length=1, max_length=120)
    municipality: str | None = Field(None, min_length=1, max_length=120)
    geometry: PolygonGeometry | None = None
    date_a: date
    date_b: date

    @model_validator(mode='after')
    def _one_area_source(self) -> 'ChangeRequest':
        by_municipality = bool(self.department) and bool(self.municipality)
        partial = bool(self.department) != bool(self.municipality)
        by_geometry = self.geometry is not None
        if partial:
            raise ValueError('department and municipality must be provided together')
        if by_municipality == by_geometry:
            raise ValueError('provide either department + municipality or a drawn geometry')
        return self


class Issue(BaseModel):
    code: str
    message: str
    params: dict[str, Any] = Field(default_factory=dict)


class PreflightResponse(BaseModel):
    status: Literal['ok', 'blocked']
    valid: bool
    period_a_count: int | None = None
    period_b_count: int | None = None
    period_a_start: str | None = None
    period_a_end: str | None = None
    period_b_start: str | None = None
    period_b_end: str | None = None
    aoi_kind: Literal['municipality', 'drawn'] | None = None
    aoi_hectares: float | None = None
    warnings: list[Issue] = Field(default_factory=list)
    blocking_errors: list[Issue] = Field(default_factory=list)


class DateRange(BaseModel):
    start: str
    end: str


class DateWindows(BaseModel):
    period_a: DateRange
    period_b: DateRange


class Percentiles(BaseModel):
    p50: float
    p90: float
    p95: float


class AreaStatistics(BaseModel):
    stable_ha: float
    moderate_change_ha: float
    high_change_ha: float
    p95_change_ha: float
    clean_high_change_ha: float
    total_aoi_ha: float
    valid_data_ha: float
    stable_pct: float
    moderate_change_pct: float
    high_change_pct: float
    p95_change_pct: float
    clean_high_change_pct: float
    valid_data_pct: float


class LegendInfo(BaseModel):
    type: Literal['gradient', 'solid', 'rgb', 'classes']
    min: float | None = None
    max: float | None = None
    colors: list[str] = Field(default_factory=list)


class LayerInfo(BaseModel):
    id: str
    group: Literal['main', 'advanced']
    tile_url: str
    visible_by_default: bool
    legend: LegendInfo | None = None


class AoiInfo(BaseModel):
    kind: Literal['municipality', 'drawn']
    label: str
    hectares: float
    department: str | None = None
    municipality: str | None = None


class Metadata(BaseModel):
    method: str
    data: str
    resolution_m: int
    window_days: int
    min_connected_pixels: int
    thresholds: str
    date_a: str
    date_b: str
    aoi: AoiInfo


class AnalyzeResponse(BaseModel):
    status: Literal['ok']
    metadata: Metadata
    image_counts: dict[str, int]
    date_windows: DateWindows
    percentiles: Percentiles
    area_statistics: AreaStatistics
    layers: list[LayerInfo]
    boundary: dict[str, Any]
    bounds: list[list[float]]
    warnings: list[Issue] = Field(default_factory=list)
    generated_at: str
