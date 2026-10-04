"""Reference implementation for PERSONAL_AI_REALITY_DAILY_WECHAT_SNAPSHOT_V0.1.

Cloud-side L2 adapter boundary for the approved Reality daily WeChat snapshot
pipeline. It maps a *reader-shaped* item produced by the local
``wechat-reader-v1`` capability into the existing REALITY capture envelope
(``PERSONAL_AI_REALITY_CAPTURE_NORMALIZATION_V0.1``) and assembles a per-day,
per-chat bundle of those envelopes.

The adapter is pure and dry-run only:

* it never reads a WeChat store, database, file or network endpoint and never
  contacts a device -- the reader is a local runtime provider;
* it performs no production write, no Canonical write and creates no second
  state store (it reuses the existing capture normalizer and promotion planner);
* real acquisition, relay deployment and Canonical promotion remain behind the
  approved Human Gate boundaries.

It reuses :mod:`personal_ai_execution.reality_capture`
(``build_capture_envelope`` / ``normalize_reality_capture``) and
:mod:`personal_ai_execution.reality_canonical_writer` (``prepare_promotion``)
directly; it introduces no alternate schema and no second Reality store.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from personal_ai_execution.reality_capture import (
    EPISTEMIC_INFERRED,
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_UNKNOWN,
    REALITY_CONTRACT_VERSION,
    STATUS_HASH_MISMATCH,
    STATUS_INCOMPLETE,
    STATUS_VERIFIED,
    build_capture_envelope,
    normalize_reality_capture,
)
from personal_ai_execution.reality_canonical_writer import (
    HUMAN_GATE,
    prepare_promotion,
)

BUNDLE_CONTRACT = "PERSONAL_AI_REALITY_DAILY_WECHAT_SNAPSHOT_V0.1"
READER_CAPABILITY = "wechat-reader-v1"

BUNDLE_ID_NAMESPACE = "wechat-daily"
PRODUCER_RUNTIME = "windows_local"

READER_OUTPUT_FIELDS = (
    "chat_id",
    "message_id",
    "sender_id",
    "create_time_iso",
    "content_available",
    "source_db",
)

BUNDLE_REQUIRED_FIELDS = (
    "bundle_contract",
    "bundle_id",
    "producer",
    "window",
    "watermark",
    "snapshots",
)

EPISTEMIC_STATUSES = (
    EPISTEMIC_OBSERVED,
    EPISTEMIC_STATED,
    EPISTEMIC_INFERRED,
    EPISTEMIC_UNKNOWN,
)

MODE_DRY_RUN = "DRY_RUN"


def _meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _pick(record: Mapping[str, Any], *keys: str) -> Any:
    if not isinstance(record, Mapping):
        return None
    for key in keys:
        value = record.get(key)
        if _meaningful(value):
            return value
    return None


def _compact(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if _meaningful(value)}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def bundle_id_for(chat_id: Any, window_start: Any, window_end: Any) -> str:
    """Derive the deterministic daily bundle id.

    ``bundle_id = "wechat-daily:" + chat_id + ":" + window_start + ":" + window_end``
    """
    return (
        BUNDLE_ID_NAMESPACE
        + ":"
        + _text(chat_id)
        + ":"
        + _text(window_start)
        + ":"
        + _text(window_end)
    )


def _source_identity(chat_id: Any) -> str | None:
    text = _text(chat_id)
    if not text:
        return None
    return "wechat:conversation:" + text


def _redact_source_db(source_db: Any) -> str:
    """Reduce a possibly path-shaped ``source_db`` to its basename.

    Local paths are redacted on read: only the opaque leaf name is retained in
    the ``source_location`` URI so no local filesystem path is carried into the
    capture envelope.
    """
    text = _text(source_db).replace("\\", "/")
    return text.rstrip("/").split("/")[-1] if text else ""


def _source_location(source_db: Any, chat_id: Any) -> str | None:
    chat = _text(chat_id)
    if not chat:
        return None
    db = _redact_source_db(source_db)
    if db:
        return "wechat://local-snapshot/" + db + "/" + chat
    return "wechat://local-snapshot/" + chat


def _build_reader_evidence(
    record: Mapping[str, Any],
    *,
    window: Mapping[str, Any] | None,
    reader_version: Any,
    observed_at: Any,
) -> dict[str, Any]:
    evidence = {
        "method": READER_CAPABILITY,
        "capability": READER_CAPABILITY,
        "reader_version": reader_version,
        "chat_id": _pick(record, "chat_id"),
        "message_id": _pick(record, "message_id"),
        "sender_id": _pick(record, "sender_id"),
        "source_db": _redact_source_db(record.get("source_db"))
        if isinstance(record, Mapping)
        else None,
        "content_available": record.get("content_available")
        if isinstance(record, Mapping)
        else None,
        "window": dict(window) if isinstance(window, Mapping) else None,
        "observed_at": observed_at,
    }
    return _compact(evidence)


def reader_item_to_envelope(
    item: Mapping[str, Any] | None,
    *,
    window: Mapping[str, Any] | None = None,
    reader_version: Any = None,
    observed_at: Any = None,
) -> dict[str, Any]:
    """Map one ``wechat-reader-v1`` output item to the existing L2 envelope.

    The mapping is fail-closed and never fabricates a value:

    * a missing ``chat_id`` leaves ``source_identity`` unset (``UNKNOWN``), so the
      normalizer reports ``INCOMPLETE`` -- never silently verified;
    * ``content_available=false`` drops any content, so the capture is
      ``INCOMPLETE`` rather than inventing a payload;
    * values the adapter *derives* (``source_identity`` / ``source_location`` and
      the ``content_version`` fallback) default to ``INFERRED`` unless the local
      producer explicitly attests a status, so an inferred field can never become
      ``VERIFIED`` promotion-eligible by accident.
    """
    record = item if isinstance(item, Mapping) else {}

    epistemic: dict[str, str] = {}
    declared = record.get("epistemic")
    if isinstance(declared, Mapping):
        epistemic.update({str(key): value for key, value in declared.items()})

    chat_id = _pick(record, "chat_id")
    source_db = _pick(record, "source_db")
    message_id = _pick(record, "message_id")

    source_identity = _pick(record, "source_identity", "wechat_source")
    if not _meaningful(source_identity):
        source_identity = _source_identity(chat_id)
        if _meaningful(source_identity):
            epistemic.setdefault("source_identity", EPISTEMIC_INFERRED)

    source_location = _pick(record, "source_location", "source_uri", "source_url")
    if not _meaningful(source_location):
        source_location = _source_location(source_db, chat_id)
        if _meaningful(source_location):
            epistemic.setdefault("source_location", EPISTEMIC_INFERRED)

    source_version = _pick(record, "source_version", "source_revision")

    content_version = _pick(record, "content_version", "content_revision")
    if not _meaningful(content_version) and _meaningful(message_id):
        content_version = message_id
        epistemic.setdefault("content_version", EPISTEMIC_INFERRED)

    captured_at = _pick(record, "create_time_iso", "captured_at", "source_timestamp")

    content_available = record.get("content_available")
    if content_available is False:
        content = None
    else:
        content = _pick(record, "content", "snapshot.content", "payload", "body")

    evidence = record.get("verification_evidence")
    if not _meaningful(evidence):
        nested = record.get("verification")
        if isinstance(nested, Mapping):
            evidence = nested.get("evidence")
    if not _meaningful(evidence):
        evidence = _build_reader_evidence(
            record,
            window=window,
            reader_version=reader_version,
            observed_at=observed_at,
        )
        if _meaningful(evidence):
            epistemic.setdefault("verification_evidence", EPISTEMIC_INFERRED)
        else:
            evidence = None

    content_hash = _pick(record, "content_hash", "snapshot_hash")
    source_content_hash = _pick(record, "source_content_hash", "source_hash")
    capture_id = _pick(record, "capture_id", "snapshot_id")
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        provenance = record.get("asset_provenance")
    if not isinstance(provenance, Mapping):
        provenance = None

    envelope = build_capture_envelope(
        source_identity=source_identity,
        source_location=source_location,
        source_version=source_version,
        content_version=content_version,
        captured_at=captured_at,
        content=content,
        verification_evidence=evidence,
        capture_id=capture_id,
        message_id=message_id,
        content_hash=content_hash,
        epistemic=epistemic or None,
        provenance=provenance,
    )
    if _meaningful(source_content_hash):
        envelope["source_content_hash"] = source_content_hash
    return envelope


def assemble_daily_bundle(
    *,
    chat_id: Any,
    reader_items: Any,
    window_start: Any,
    window_end: Any,
    timezone: str = "UTC",
    executor: str = "hermes",
    reader_version: Any = None,
    previous_source_version: Any = None,
    this_source_version: Any = None,
    observed_at: Any = None,
) -> dict[str, Any]:
    """Assemble one daily, per-chat bundle of existing L2 capture envelopes."""
    items = list(reader_items) if isinstance(reader_items, (list, tuple)) else []
    window = {
        "start": window_start,
        "end": window_end,
        "timezone": timezone,
    }
    snapshots = [
        reader_item_to_envelope(
            item,
            window=window,
            reader_version=reader_version,
            observed_at=observed_at,
        )
        for item in items
    ]
    return {
        "bundle_contract": BUNDLE_CONTRACT,
        "bundle_id": bundle_id_for(chat_id, window_start, window_end),
        "producer": {
            "runtime": PRODUCER_RUNTIME,
            "executor": executor,
            "reader_capability": READER_CAPABILITY,
            "reader_version": reader_version,
        },
        "window": window,
        "watermark": {
            "previous_source_version": previous_source_version,
            "this_source_version": this_source_version,
        },
        "snapshots": snapshots,
    }


def bundle_fingerprint(bundle: Mapping[str, Any] | None) -> str:
    """Deterministic SHA-256 fingerprint over the bundle's snapshot envelopes."""
    snapshots = bundle.get("snapshots") if isinstance(bundle, Mapping) else None
    payload = snapshots if isinstance(snapshots, list) else []
    return "sha256:" + _sha256(payload)


def bundle_idempotency_key(bundle: Mapping[str, Any] | None) -> str | None:
    """Daily idempotency key: ``bundle_id`` plus the deterministic fingerprint."""
    if not isinstance(bundle, Mapping):
        return None
    bundle_id = _text(bundle.get("bundle_id"))
    if not bundle_id:
        return None
    return bundle_id + ":" + bundle_fingerprint(bundle)


def snapshot_idempotency_key(
    normalized: Mapping[str, Any] | None,
    *,
    target: Any = None,
) -> str | None:
    """Message idempotency key: ``candidate_id`` plus the recomputed content hash.

    When a canonical ``target`` is supplied the existing L3 form
    ``target:candidate_id:content_hash`` is produced; the L2 adapter itself never
    resolves or writes a target.
    """
    candidate = normalized.get("candidate") if isinstance(normalized, Mapping) else None
    if not isinstance(candidate, Mapping):
        return None
    candidate_id = candidate.get("candidate_id")
    content_hash = candidate.get("content_hash")
    if not _meaningful(candidate_id) or not _meaningful(content_hash):
        return None
    base = str(candidate_id) + ":" + str(content_hash)
    if _meaningful(target):
        return str(target).strip().lower() + ":" + base
    return base


def validate_bundle(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    """Structurally validate a daily bundle (no normalization, no write)."""
    reasons: list[str] = []
    if not isinstance(bundle, Mapping):
        return {
            "ok": False,
            "reasons": ["bundle is not a mapping"],
            "bundle_id": None,
            "snapshot_count": 0,
        }

    if bundle.get("bundle_contract") != BUNDLE_CONTRACT:
        reasons.append("bundle_contract is not " + BUNDLE_CONTRACT)

    bundle_id = _text(bundle.get("bundle_id"))
    if not bundle_id:
        reasons.append("bundle_id is missing")
    elif not bundle_id.startswith(BUNDLE_ID_NAMESPACE + ":"):
        reasons.append("bundle_id does not use the " + BUNDLE_ID_NAMESPACE + ": namespace")

    producer = bundle.get("producer")
    if not isinstance(producer, Mapping):
        reasons.append("producer is not a mapping")
    else:
        if producer.get("reader_capability") != READER_CAPABILITY:
            reasons.append("producer.reader_capability is not " + READER_CAPABILITY)
        if not _meaningful(producer.get("executor")):
            reasons.append("producer.executor is missing")

    window = bundle.get("window")
    if not isinstance(window, Mapping):
        reasons.append("window is not a mapping")
    else:
        for key in ("start", "end"):
            if not _meaningful(window.get(key)):
                reasons.append("window." + key + " is missing")

    if not isinstance(bundle.get("watermark"), Mapping):
        reasons.append("watermark is not a mapping")

    snapshots = bundle.get("snapshots")
    if not isinstance(snapshots, list):
        reasons.append("snapshots is not a list")
        snapshots = []
    else:
        for index, snapshot in enumerate(snapshots):
            if not isinstance(snapshot, Mapping):
                reasons.append("snapshot[" + str(index) + "] is not a mapping")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "bundle_id": bundle_id or None,
        "snapshot_count": len(snapshots),
    }


def dry_run_bundle(
    bundle: Mapping[str, Any] | None,
    *,
    target_asset_type: Any = None,
) -> dict[str, Any]:
    """Dry-run a daily bundle through the existing L2 boundary with no write.

    Each snapshot is normalized by ``normalize_reality_capture``. When a
    ``target_asset_type`` is supplied, each result is additionally passed through
    ``prepare_promotion`` so the promotion plan (and its Human Gate) can be
    previewed. Nothing is persisted: every report states
    ``write_performed=false`` / ``production_write_performed=false`` and
    ``second_state_store_created=false``.
    """
    validation = validate_bundle(bundle)
    snapshots = (
        bundle.get("snapshots")
        if isinstance(bundle, Mapping) and isinstance(bundle.get("snapshots"), list)
        else []
    )

    results: list[dict[str, Any]] = []
    promotions: list[dict[str, Any]] = []
    counts = {
        STATUS_VERIFIED: 0,
        STATUS_INCOMPLETE: 0,
        STATUS_HASH_MISMATCH: 0,
    }
    epistemic_totals = {status: 0 for status in EPISTEMIC_STATUSES}
    aggregated_missing: list[str] = []

    for index, snapshot in enumerate(snapshots):
        normalized = normalize_reality_capture(snapshot)
        status = normalized["status"]
        if status in counts:
            counts[status] += 1

        for field in normalized["missing"]:
            if field not in aggregated_missing:
                aggregated_missing.append(field)
        for tag in normalized["epistemic"].values():
            if tag in epistemic_totals:
                epistemic_totals[tag] += 1

        candidate = normalized["candidate"]
        results.append(
            {
                "index": index,
                "status": status,
                "verified": normalized["verified"],
                "promotion_eligible": normalized["promotion_eligible"],
                "missing": list(normalized["missing"]),
                "invalid": list(normalized["invalid"]),
                "hash_match": normalized["hash_match"],
                "candidate_id": candidate["candidate_id"],
                "content_hash": candidate["content_hash"],
                "idempotency_key": snapshot_idempotency_key(normalized),
                "epistemic": dict(normalized["epistemic"]),
                "write_performed": normalized["write_performed"],
            }
        )

        if target_asset_type is not None:
            plan = prepare_promotion(
                normalized, target_asset_type=target_asset_type
            )
            promotions.append(
                {
                    "index": index,
                    "phase": plan["phase"],
                    "status": plan["status"],
                    "eligible": plan["eligible"],
                    "target_asset_type": plan["target_asset_type"],
                    "requires_human_gate": plan["requires_human_gate"],
                    "human_gate": plan["human_gate"],
                    "production_write_performed": plan["production_write_performed"],
                    "second_state_store_created": plan["second_state_store_created"],
                    "idempotency_key": plan["idempotency_key"],
                }
            )

    total = len(results)
    report: dict[str, Any] = {
        "contract": BUNDLE_CONTRACT,
        "capture_contract": REALITY_CONTRACT_VERSION,
        "mode": MODE_DRY_RUN,
        "bundle_id": validation["bundle_id"],
        "bundle_fingerprint": bundle_fingerprint(bundle),
        "bundle_idempotency_key": bundle_idempotency_key(bundle),
        "validation": validation,
        "snapshot_results": results,
        "promotion_previews": promotions,
        "status_counts": counts,
        "aggregated_missing": aggregated_missing,
        "epistemic_totals": epistemic_totals,
        "snapshot_count": total,
        "all_verified": bool(total) and counts[STATUS_VERIFIED] == total,
        "any_incomplete": counts[STATUS_INCOMPLETE] > 0,
        "any_hash_mismatch": counts[STATUS_HASH_MISMATCH] > 0,
        "ok": validation["ok"],
        "read_only": True,
        "write_performed": False,
        "production_write_performed": False,
        "canonical_write_performed": False,
        "second_state_store_created": False,
        "requires_human_gate": True,
        "human_gate": HUMAN_GATE,
        "reasons": list(validation["reasons"]),
    }
    return report
