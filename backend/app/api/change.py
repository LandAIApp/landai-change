from fastapi import APIRouter, Request

from ..core.rate_limit import analyze_limit, limiter
from ..schemas.change import AnalyzeResponse, ChangeRequest, PreflightResponse
from ..services.analysis import run_analysis
from ..services.preflight import run_preflight

router = APIRouter(prefix='/api/v1/change')


@router.post('/preflight', response_model=PreflightResponse)
def preflight(payload: ChangeRequest) -> PreflightResponse:
    return run_preflight(payload)


@router.post('/analyze', response_model=AnalyzeResponse)
@limiter.limit(analyze_limit)
def analyze(request: Request, payload: ChangeRequest) -> AnalyzeResponse:
    return run_analysis(payload)
