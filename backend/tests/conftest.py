import pytest

from app.core import gate, rate_limit
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _reset():
    get_settings.cache_clear()
    gate.reset_gate()
    rate_limit.limiter.reset()
    yield
    get_settings.cache_clear()
    gate.reset_gate()


SQUARE = [[-75.0, 4.0], [-74.9, 4.0], [-74.9, 4.1], [-75.0, 4.1], [-75.0, 4.0]]  # ~12,000 ha
BIG = [[-75.0, 4.0], [-73.0, 4.0], [-73.0, 6.0], [-75.0, 6.0], [-75.0, 4.0]]
