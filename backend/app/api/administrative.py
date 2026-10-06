from __future__ import annotations

from fastapi import APIRouter, Query

from ..core.config import get_settings
from ..core.errors import MunicipalityNotFoundError
from ..schemas.administrative import (
    DepartmentsResponse, MunicipalitiesResponse, MunicipalityInfoResponse,
)
from ..services import administrative

router = APIRouter(prefix='/api/v1/administrative')


@router.get('/departments', response_model=DepartmentsResponse)
def departments() -> DepartmentsResponse:
    return DepartmentsResponse(departments=administrative.list_departments())


@router.get('/municipalities', response_model=MunicipalitiesResponse)
def municipalities(department: str = Query(..., min_length=1, max_length=120)) -> MunicipalitiesResponse:
    return MunicipalitiesResponse(
        department=department, municipalities=administrative.list_municipalities(department))


@router.get('/municipality', response_model=MunicipalityInfoResponse)
def municipality(department: str = Query(..., min_length=1, max_length=120),
                 municipality: str = Query(..., min_length=1, max_length=120)) -> MunicipalityInfoResponse:
    """Area + simplified boundary so the map can preview the selection and show the limit."""
    info = administrative.municipality_info(department, municipality)
    if not info.get('matches'):
        raise MunicipalityNotFoundError(
            f"Municipality '{municipality}' was not found in department '{department}'.")
    limit = get_settings().max_aoi_hectares
    return MunicipalityInfoResponse(
        department=department, municipality=municipality, aoi_hectares=info['hectares'],
        max_aoi_hectares=limit, within_limit=info['hectares'] <= limit,
        boundary=info['boundary'], bounds=info['bounds'])
