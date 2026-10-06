import pytest

from app.change import config as C
from app.change.areas import add_percentages
from app.change.classification import Thresholds
from app.change.sentinel import build_period
from app.core import gate
from app.core.errors import ServerBusyError
from app.core.logging import LOG_FIELDS, log_analysis
from datetime import date


def test_constants_follow_the_spec():
    assert C.CLEAR_THRESHOLD == 0.55 and C.EXCLUDED_SCL_CLASSES == (1, 3, 7, 8, 9, 10, 11)
    assert C.S2_BANDS == ('B2', 'B3', 'B4', 'B8A', 'B11', 'B12') and C.WINDOW_DAYS == 30
    assert C.ANALYSIS_SCALE == 20 and C.PERCENTILES == (50, 90, 95) and C.MIN_CONNECTED_PIXELS == 7
    assert len(C.PRODUCT_BANDS) == 9


def test_period_is_inclusive_30_days():
    p = build_period(date(2024, 3, 1))
    assert (p.start, p.end) == (date(2024, 1, 31), date(2024, 3, 31))


def test_thresholds_from_values_and_empty():
    t = Thresholds.from_values({'ChangeMagnitude_p50': .01, 'ChangeMagnitude_p90': .03, 'ChangeMagnitude_p95': .05})
    assert t.as_floats() == {'p50': .01, 'p90': .03, 'p95': .05}
    with pytest.raises(ValueError):
        Thresholds.from_values({'ChangeMagnitude_p50': None, 'ChangeMagnitude_p90': None, 'ChangeMagnitude_p95': None})
    with pytest.raises(ValueError):
        Thresholds.from_values({})


def test_area_percentages():
    out = add_percentages({'stable_ha': 50, 'moderate_change_ha': 40, 'high_change_ha': 10,
                           'p95_change_ha': 5, 'clean_high_change_ha': 4, 'total_aoi_ha': 100})
    assert out['valid_data_pct'] == 100 and out['high_change_pct'] == 10 and out['clean_high_change_pct'] == 4
    assert add_percentages({})['total_aoi_ha'] == 0


def test_gate_rejects_second_concurrent_analysis():
    with gate.analysis_slot():
        with pytest.raises(ServerBusyError):
            with gate.analysis_slot():
                pass
    with gate.analysis_slot():
        pass


def test_log_has_no_sensitive_fields():
    rec = log_analysis(aoi_kind='drawn', geometry=[[1, 2]], ip='1.2.3.4', authorization='x', success=True)
    assert set(rec) == {'event', *LOG_FIELDS}
