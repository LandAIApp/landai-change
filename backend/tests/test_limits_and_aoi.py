from app.core.config import Settings
from app.schemas.change import ChangeRequest
from app.services.aoi import limit_issues, resolve_aoi
from conftest import BIG, SQUARE


def req(ring):
    return ChangeRequest(geometry={'type': 'Polygon', 'coordinates': [ring]},
                         date_a='2023-01-15', date_b='2024-01-15')


def test_limit_issues_levels():
    s = Settings(max_aoi_hectares=100, warn_aoi_hectares=50, min_aoi_hectares=10)
    assert limit_issues(120, 'municipality', s)[0][0].code == 'aoi_too_large'
    assert limit_issues(60, 'municipality', s)[1][0].code == 'aoi_large'
    assert limit_issues(5, 'drawn', s)[0][0].code == 'aoi_too_small'
    assert limit_issues(5, 'municipality', s) == ([], [])   # minimum applies to drawn only
    assert limit_issues(20, 'drawn', s) == ([], [])


def test_drawn_inside_limit_resolves(monkeypatch):
    import ee
    import app.services.aoi as aoi_mod
    monkeypatch.setattr(aoi_mod, 'ensure_initialized', lambda: None)
    monkeypatch.setattr(ee.Geometry, 'Polygon', staticmethod(lambda *a, **k: object()))
    aoi, blocking, _ = resolve_aoi(req(SQUARE), Settings())
    assert aoi is not None and not blocking and aoi.kind == 'drawn'


def test_drawn_over_limit_blocked_without_ee():
    aoi, blocking, _ = resolve_aoi(req(BIG), Settings())
    assert aoi is None and blocking[0].code == 'aoi_too_large'
    assert blocking[0].params['max'] == 100_000


def test_request_needs_exactly_one_area_source():
    import pytest
    with pytest.raises(ValueError):
        ChangeRequest(date_a='2023-01-15', date_b='2024-01-15')
    with pytest.raises(ValueError):
        ChangeRequest(department='Tolima', date_a='2023-01-15', date_b='2024-01-15')
    with pytest.raises(ValueError):
        ChangeRequest(department='Tolima', municipality='Ibagué',
                      geometry={'type': 'Polygon', 'coordinates': [SQUARE]},
                      date_a='2023-01-15', date_b='2024-01-15')
