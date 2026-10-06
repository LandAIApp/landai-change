"""Concurrency gate: at most N heavy analyses at a time (free-tier protection)."""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings
from .errors import ServerBusyError

_lock = threading.Lock()
_semaphore: threading.BoundedSemaphore | None = None


def _get() -> threading.BoundedSemaphore:
    global _semaphore
    with _lock:
        if _semaphore is None:
            _semaphore = threading.BoundedSemaphore(max(1, get_settings().max_concurrent_analyses))
        return _semaphore


def reset_gate() -> None:
    """Tests only."""
    global _semaphore
    with _lock:
        _semaphore = None


@contextmanager
def analysis_slot() -> Iterator[None]:
    semaphore = _get()
    if not semaphore.acquire(blocking=False):
        raise ServerBusyError('Another analysis is running. Please retry in a minute.')
    try:
        yield
    finally:
        semaphore.release()
