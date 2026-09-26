"""Canonical Personal AI Execution V2 source package."""

from __future__ import annotations

from . import event_sync
from .event_sync import (
    GOLDEN_TASK_ID,
    PENDING_REVIEW,
    REVIEWED_STATE,
    EventSyncRegistry,
    default_registry,
    get_review_events,
    get_sync_events,
    list_pending_results,
    mark_reviewed,
    reset_default_registry,
    submit_task,
    sync_terminal_result,
)
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
    "GOLDEN_TASK_ID",
    "PASS",
    "PENDING",
    "PENDING_REVIEW",
    "REVIEWED_STATE",
    "TERMINAL_STATUSES",
    "EventSyncRegistry",
    "default_registry",
    "event_sync",
    "event_sync_retry_allowed",
    "get_review_events",
    "get_sync_events",
    "get_task_result",
    "list_pending_results",
    "mark_reviewed",
    "normalize_conclusion",
    "normalize_result",
    "normalize_self_reported_status",
    "reset_default_registry",
    "submit_task",
    "sync_terminal_result",
    "workflow_conclusion",
]
