"""Structured application errors returned as JSON by the API."""
from __future__ import annotations

from typing import Any


class ChangeError(Exception):
    status_code = 400
    code = 'change_error'

    def __init__(self, message: str, *, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {'status': 'error', 'code': self.code, 'message': self.message,
                'details': self.details}


class InvalidRequestError(ChangeError):
    status_code, code = 422, 'invalid_request'


class DepartmentNotFoundError(ChangeError):
    status_code, code = 404, 'department_not_found'


class MunicipalityNotFoundError(ChangeError):
    status_code, code = 404, 'municipality_not_found'


class PreflightFailedError(ChangeError):
    status_code, code = 422, 'preflight_failed'


class NoValidPixelsError(ChangeError):
    status_code, code = 422, 'no_valid_pixels'


class ServerBusyError(ChangeError):
    status_code, code = 503, 'server_busy'


class RateLimitError(ChangeError):
    status_code, code = 429, 'rate_limit_exceeded'


class EarthEngineAuthError(ChangeError):
    status_code, code = 503, 'earth_engine_not_available'


class EarthEngineServiceError(ChangeError):
    status_code, code = 502, 'earth_engine_error'


class EarthEngineTimeoutError(ChangeError):
    status_code, code = 504, 'earth_engine_timeout'


class EarthEngineLimitError(ChangeError):
    status_code, code = 422, 'earth_engine_computation_limit'


class EarthEngineQuotaError(ChangeError):
    status_code, code = 429, 'earth_engine_quota'


class TileGenerationError(ChangeError):
    status_code, code = 502, 'tile_generation_failed'
