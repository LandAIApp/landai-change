"""Earth Engine initialization and the single server->client evaluation helper.

Credentials, in order of preference:
  1. Cloud Run / GCE service identity (Application Default Credentials) - production.
  2. Credentials saved by `earthengine authenticate` (~/.config/earthengine) - local.
  3. Optional service-account JSON via EE_PRIVATE_KEY_PATH - never required, never committed.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import ee

from .config import BACKEND_DIR, REPO_ROOT, get_settings
from .errors import (
    ChangeError, EarthEngineAuthError, EarthEngineLimitError, EarthEngineQuotaError,
    EarthEngineServiceError, EarthEngineTimeoutError,
)

_lock = threading.Lock()
_state: dict[str, Any] = {'initialized': False, 'error': None}


def _resolve_key_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    for base in (Path.cwd(), BACKEND_DIR, REPO_ROOT):
        candidate = base / path
        if candidate.exists():
            return candidate
    return path


def ensure_initialized() -> None:
    """Initialize Earth Engine once per process."""
    if _state['initialized']:
        return
    with _lock:
        if _state['initialized']:
            return
        settings = get_settings()
        try:
            if not settings.ee_project:
                raise ValueError('EE_PROJECT is empty')
            if settings.ee_private_key_path:
                key_path = _resolve_key_path(settings.ee_private_key_path)
                if not key_path.exists():
                    raise FileNotFoundError('EE_PRIVATE_KEY_PATH does not point to a file')
                key_data = json.loads(key_path.read_text(encoding='utf-8'))
                email = settings.ee_service_account or key_data.get('client_email', '')
                credentials = ee.ServiceAccountCredentials(email, str(key_path))
                ee.Initialize(credentials, project=settings.ee_project)
            else:
                ee.Initialize(project=settings.ee_project)
        except Exception as exc:  # noqa: BLE001 - any init failure is an availability problem
            _state['error'] = f'{type(exc).__name__}: {exc}'[:500]
            raise EarthEngineAuthError(
                'Earth Engine could not be initialized. Check EE_PROJECT and the credentials '
                '(Cloud Run service identity, or `earthengine authenticate` locally).',
                details=_state['error']) from exc
        _state['initialized'] = True
        _state['error'] = None


def status() -> dict[str, Any]:
    return {'initialized': _state['initialized'], 'last_error': _state['error']}


def map_ee_error(exc: Exception, what: str) -> ChangeError:
    text = str(exc)
    low = text.lower()
    short = text[:400]
    if 'timed out' in low or 'deadline' in low:
        return EarthEngineTimeoutError(
            f'Earth Engine timed out while {what}. Try a smaller area.', details=short)
    if any(k in low for k in ('memory limit', 'too many concurrent', 'too large', 'too many pixels')):
        return EarthEngineLimitError(
            f'Earth Engine computation limit reached while {what}. Try a smaller area.',
            details=short)
    if 'quota' in low or 'too many requests' in low or 'rate limit' in low:
        return EarthEngineQuotaError(
            f'Earth Engine quota exceeded while {what}. Wait a moment and retry.', details=short)
    if 'permission' in low or 'not found' in low or 'does not exist' in low:
        return EarthEngineServiceError(
            f'Earth Engine could not access a required dataset or asset while {what}. '
            'Make sure the municipal asset is shared with the runtime identity.', details=short)
    return EarthEngineServiceError(f'Earth Engine error while {what}.', details=short)


def evaluate(obj: Any, what: str = 'evaluating a request') -> Any:
    """Evaluate a SMALL server-side object at the API boundary (getInfo)."""
    ensure_initialized()
    try:
        return obj.getInfo()
    except ChangeError:
        raise
    except ee.EEException as exc:
        raise map_ee_error(exc, what) from exc
    except Exception as exc:  # noqa: BLE001 - network/transport failures
        raise EarthEngineServiceError(
            f'Unexpected error while {what}.',
            details=f'{type(exc).__name__}: {str(exc)[:300]}') from exc
