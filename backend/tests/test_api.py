from fastapi.testclient import TestClient

from app.main import app
from app.schemas.change import PreflightResponse
from conftest import BIG, SQUARE

client = TestClient(app)
BODY = {'geometry': {'type': 'Polygon', 'coordinates': [SQUARE]},
        'date_a': '2023-01-15', 'date_b': '2024-01-15'}


def test_health_does_not_need_earth_engine():
    r = client.get('/health')
    assert r.status_code == 200 and r.json()['status'] == 'ok'


def test_public_config_exposes_limits():
    data = client.get('/api/v1/config').json()
    assert data['max_aoi_hectares'] == 100_000 and data['beta'] is True
    assert {'count': 5, 'per': 'hour'} in data['rate_limits']
    assert {'count': 20, 'per': 'day'} in data['rate_limits']


def test_invalid_body_returns_structured_422():
    r = client.post('/api/v1/change/preflight', json={'date_a': '2023-01-15', 'date_b': '2024-01-15'})
    assert r.status_code == 422 and r.json()['code'] == 'invalid_request'


def test_preflight_blocks_oversized_polygon_before_earth_engine():
    body = {**BODY, 'geometry': {'type': 'Polygon', 'coordinates': [BIG]}}
    r = client.post('/api/v1/change/preflight', json=body)
    data = r.json()
    assert r.status_code == 200 and data['status'] == 'blocked'
    assert data['blocking_errors'][0]['code'] == 'aoi_too_large'
    assert data['aoi_hectares'] > 100_000


def test_preflight_blocks_bad_dates():
    body = {**BODY, 'date_a': '2024-01-15', 'date_b': '2023-01-15'}
    codes = [e['code'] for e in client.post('/api/v1/change/preflight', json=body).json()['blocking_errors']]
    assert 'invalid_dates' in codes


def test_analyze_rate_limit_returns_structured_429(monkeypatch):
    monkeypatch.setenv('RATE_LIMIT_ANALYZE', '2/hour')
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.api.change as change_api
    from app.core.errors import ServerBusyError
    calls = []

    def fake(payload):
        calls.append(1)
        raise ServerBusyError('busy')

    monkeypatch.setattr(change_api, 'run_analysis', fake)
    codes = []
    for _ in range(3):
        r = client.post('/api/v1/change/analyze', json=BODY)
        codes.append(r.status_code)
    assert codes == [503, 503, 429]
    body = r.json()
    assert body['code'] == 'rate_limit_exceeded'
    assert 'Retry-After' in r.headers
    assert len(calls) == 2
    # preflight is NOT limited
    assert client.post('/api/v1/change/preflight', json={**BODY, 'geometry': {'type': 'Polygon', 'coordinates': [BIG]}}).status_code == 200
