from __future__ import annotations

from fastapi import APIRouter

from ..core import earth_engine

router = APIRouter()


@router.get('/health')
def health() -> dict:
    """Liveness only: never calls Earth Engine."""
    return {'status': 'ok', 'service': 'landai-change', 'earth_engine': earth_engine.status()}
