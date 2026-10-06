from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .api import administrative, change, config, health
from .core.config import get_settings
from .core.errors import ChangeError, RateLimitError
from .core.logging import configure_logging
from .core.rate_limit import limiter, retry_after_seconds

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title='Land AI Change Intelligence', version='1.0.0',
              description='Sentinel-2 change detection (public beta, free resources).')
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type'], expose_headers=['Retry-After'])


@app.exception_handler(ChangeError)
async def change_error_handler(_: Request, exc: ChangeError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry = retry_after_seconds(request)
    error = RateLimitError('Free-beta usage limit reached. Please try again later.',
                           details={'retry_after_seconds': retry, 'limit': str(exc.detail)})
    headers = {'Retry-After': str(retry)} if retry else None
    return JSONResponse(status_code=429, content=error.to_dict(), headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{'loc': list(e.get('loc', [])), 'msg': e.get('msg', '')} for e in exc.errors()]
    return JSONResponse(status_code=422, content={
        'status': 'error', 'code': 'invalid_request', 'message': 'Invalid request.', 'details': errors})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger('landai').error('unhandled %s', type(exc).__name__)
    return JSONResponse(status_code=500, content={
        'status': 'error', 'code': 'internal_error', 'message': 'Unexpected server error.',
        'details': None})


app.include_router(health.router)
app.include_router(config.router)
app.include_router(administrative.router)
app.include_router(change.router)
