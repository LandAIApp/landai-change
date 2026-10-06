"""Service-level tests with Earth Engine fully mocked (no network, no credentials)."""
from types import SimpleNamespace

import pytest

import app.services.analysis as analysis
import app.services.preflight as preflight_mod
from app.core.errors import EarthEngineServiceError, NoValidPixelsError, PreflightFailedError
from app.schemas.change import ChangeRequest, PreflightResponse
from app.services import administrative
from conftest import SQUARE

MUNI = ChangeRequest(department='Tolima', municipality='San Luis', date_a='2023-02-15', date_b='2025-02-15')
DRAWN = ChangeRequest(geometry={'type': 'Polygon', 'coordinates': [SQUARE]},
                      date_a='2023-02-15', date_b='2025-02-15')


def fake_aoi(hectares=28000.0):
    return SimpleNamespace(kind='municipality', label='San Luis, Tolima', geometry=object(),
                           hectares=hectares, boundary={'type': 'Feature', 'properties': {}, 'geometry': {}},
                           bounds=[[3, -75], [4, -74]], department='Tolima', municipality='San Luis')


@pytest.fixture
def ee_mock(monkeypatch):
    """Mock every Earth Engine touchpoint of preflight + analysis."""
    state = {'counts': {'period_a': 6, 'period_b': 9}, 'municipality_matches': True}
    import app.services.aoi as aoi_mod
    monkeypatch.setattr(aoi_mod.administrative, 'municipality_info',
                        lambda d, m: ({'matches': 1, 'hectares': 28000.0,
                                       'boundary': {'type': 'Feature', 'properties': {}, 'geometry': {}},
                                       'bounds': [[3, -75], [4, -74]]} if state['municipality_matches']
                                      else {'matches': 0}))
    monkeypatch.setattr(aoi_mod.administrative, 'select_municipality',
                        lambda d, m: SimpleNamespace(geometry=lambda: object()))
    monkeypatch.setattr(preflight_mod, 'scene_counts', lambda *a, **k: 'counts')
    monkeypatch.setattr(preflight_mod, 'evaluate', lambda obj, what='': dict(state['counts']))
    return state


def test_valid_preflight(ee_mock):
    r = preflight_mod.run_preflight(MUNI)
    assert r.status == 'ok' and r.valid and (r.period_a_count, r.period_b_count) == (6, 9)
    assert r.aoi_kind == 'municipality' and r.aoi_hectares == 28000.0
    assert (r.period_a_start, r.period_a_end) == ('2023-01-16', '2023-03-17')


def test_invalid_municipality(ee_mock):
    ee_mock['municipality_matches'] = False
    r = preflight_mod.run_preflight(MUNI)
    assert r.status == 'blocked' and r.blocking_errors[0].code == 'municipality_not_found'


@pytest.mark.parametrize('which,code', [('period_a', 'no_images_period_a'), ('period_b', 'no_images_period_b')])
def test_no_imagery_blocks(ee_mock, which, code):
    ee_mock['counts'][which] = 0
    r = preflight_mod.run_preflight(MUNI)
    assert not r.valid and code in [e.code for e in r.blocking_errors]


def test_few_scenes_is_only_a_warning(ee_mock):
    ee_mock['counts']['period_a'] = 2
    r = preflight_mod.run_preflight(MUNI)
    assert r.valid and r.warnings[0].code == 'few_scenes_a'


def test_municipality_over_limit_blocked(ee_mock, monkeypatch):
    import app.services.aoi as aoi_mod
    monkeypatch.setattr(aoi_mod.administrative, 'municipality_info',
                        lambda d, m: {'matches': 1, 'hectares': 250000.0, 'boundary': {}, 'bounds': []})
    r = preflight_mod.run_preflight(MUNI)
    assert not r.valid and r.blocking_errors[0].code == 'aoi_too_large'


def test_earth_engine_error_propagates_as_structured_error(ee_mock, monkeypatch):
    def boom(obj, what=''):
        raise EarthEngineServiceError('Earth Engine error while checking.')
    monkeypatch.setattr(preflight_mod, 'evaluate', boom)
    with pytest.raises(EarthEngineServiceError):
        preflight_mod.run_preflight(MUNI)


# ---------------------------------------------------------------- analysis

AREAS = {'stable_ha': 14000, 'moderate_change_ha': 11200, 'high_change_ha': 2800,
         'p95_change_ha': 1400, 'clean_high_change_ha': 2500, 'total_aoi_ha': 28000}
PCT = {'ChangeMagnitude_p50': .01, 'ChangeMagnitude_p90': .03, 'ChangeMagnitude_p95': .05}


@pytest.fixture
def analysis_mock(monkeypatch):
    state = {'pct': PCT, 'areas': AREAS}
    ok = PreflightResponse(status='ok', valid=True, period_a_count=6, period_b_count=9,
                           aoi_kind='municipality', aoi_hectares=28000.0, warnings=[], blocking_errors=[])
    state['preflight'] = (ok, fake_aoi())
    monkeypatch.setattr(analysis, 'preflight_core', lambda req: state['preflight'])
    monkeypatch.setattr(analysis, 'build_inputs', lambda *a, **k: 'inputs')
    monkeypatch.setattr(analysis, 'threshold_request', lambda *a, **k: 'pct-request')
    monkeypatch.setattr(analysis, 'build_outputs',
                        lambda *a, **k: SimpleNamespace(change_class=1, high_p95=2, high_clean=3))
    monkeypatch.setattr(analysis, 'area_dictionary', lambda *a, **k: 'area-request')
    monkeypatch.setattr(analysis, 'build_layers', lambda i, o: ([], []))

    def fake_eval(obj, what=''):
        return state['pct'] if obj == 'pct-request' else state['areas']
    monkeypatch.setattr(analysis, 'evaluate', fake_eval)
    return state


def test_successful_statistics(analysis_mock):
    res = analysis.run_analysis(MUNI)
    s = res.area_statistics
    assert (s.high_change_ha, s.clean_high_change_ha, s.total_aoi_ha) == (2800, 2500, 28000)
    assert s.high_change_pct == 10 and s.valid_data_pct == 100
    assert (res.percentiles.p50, res.percentiles.p95) == (.01, .05)
    assert res.image_counts == {'period_a': 6, 'period_b': 9}
    assert res.metadata.resolution_m == 20 and res.metadata.window_days == 30
    assert res.date_windows.period_a.start == '2023-01-16'
    assert res.warnings == []


def test_low_coverage_and_no_clean_patch_warn(analysis_mock):
    analysis_mock['areas'] = {**AREAS, 'stable_ha': 7000, 'moderate_change_ha': 5000, 'high_change_ha': 1000,
                              'clean_high_change_ha': 0}
    codes = [w.code for w in analysis.run_analysis(MUNI).warnings]
    assert codes == ['low_coverage', 'no_clean_high_change']


def test_no_valid_pixels(analysis_mock):
    analysis_mock['pct'] = {k: None for k in PCT}
    with pytest.raises(NoValidPixelsError):
        analysis.run_analysis(MUNI)


def test_blocked_preflight_raises(analysis_mock):
    blocked = PreflightResponse(status='blocked', valid=False, blocking_errors=[
        {'code': 'aoi_too_large', 'message': 'x', 'params': {}}])
    analysis_mock['preflight'] = (blocked, None)
    with pytest.raises(PreflightFailedError) as info:
        analysis.run_analysis(DRAWN)
    assert info.value.details[0]['code'] == 'aoi_too_large'


def test_analysis_log_has_no_coordinates_or_credentials(analysis_mock, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger='landai.analysis'):
        analysis.run_analysis(DRAWN)
    text = ' '.join(r.getMessage() for r in caplog.records)
    assert '"success": true' in text and '-75.0' not in text and 'geometry' not in text
