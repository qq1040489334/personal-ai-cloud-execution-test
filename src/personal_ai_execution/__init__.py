"""Canonical Personal AI Execution V2 source package."""

from __future__ import annotations

from .result_normalization import (
    BLOCKED,
    FAIL,
    PASS,
    PENDING,
    TERMINAL_STATUSES,
    event_sync_retry_allowed,
    get_task_result,
    normalize_conclusion,
    normalize_result,
    normalize_self_reported_status,
    workflow_conclusion,
)

__all__ = [
    "BLOCKED",
    "FAIL",
    "PASS",
    "PENDING",
    "TERMINAL_STATUSES",
    "event_sync_retry_allowed",
    "get_task_result",
    "normalize_conclusion",
    "normalize_result",
    "normalize_self_reported_status",
    "workflow_conclusion",
]
