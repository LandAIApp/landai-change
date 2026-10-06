"""One structured JSON line per analysis (Cloud Logging parses stdout JSON).

Never log credentials, headers, IP addresses or drawn coordinates.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger('landai.analysis')

LOG_FIELDS = (
    'aoi_kind', 'department', 'municipality', 'aoi_hectares', 'date_a', 'date_b',
    'period_a_count', 'period_b_count', 'p50', 'p90', 'p95',
    'high_change_ha', 'clean_high_change_ha', 'duration_seconds', 'success', 'error_code',
)


def configure_logging(level: str = 'INFO') -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format='%(message)s')


def log_analysis(**fields) -> dict:
    record = {'event': 'analysis', **{k: fields.get(k) for k in LOG_FIELDS}}
    logger.info(json.dumps(record, default=str))
    return record
