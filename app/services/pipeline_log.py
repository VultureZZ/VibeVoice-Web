"""
Structured JSON logs for production pipeline stages (timings + context).
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

_logger = logging.getLogger("pipeline.structured")


def log_pipeline_event(
    stage: str,
    *,
    task_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit one JSON line for operators / log aggregation."""
    rec: Dict[str, Any] = {"stage": stage, "event": "pipeline"}
    if task_id is not None:
        rec["task_id"] = task_id
    if duration_ms is not None:
        rec["duration_ms"] = round(float(duration_ms), 2)
    if extra:
        for k, v in extra.items():
            if k not in rec:
                rec[k] = v
    _logger.info(json.dumps(rec, default=str))


@contextmanager
def pipeline_stage(
    stage: str,
    *,
    task_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        log_pipeline_event(stage, task_id=task_id, duration_ms=dt_ms, extra=extra)
