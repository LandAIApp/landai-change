from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DepartmentsResponse(BaseModel):
    departments: list[str]


class MunicipalitiesResponse(BaseModel):
    department: str
    municipalities: list[str]


class MunicipalityInfoResponse(BaseModel):
    department: str
    municipality: str
    aoi_hectares: float
    max_aoi_hectares: float
    within_limit: bool
    boundary: dict[str, Any]
    bounds: list[list[float]]
