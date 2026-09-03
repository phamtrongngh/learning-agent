"""Evidence normalization and attribution-aware mastery calculations."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid


EVIDENCE_FIELDS = frozenset({
    "event_id",
    "attempt_id",
    "timestamp",
    "lesson_id",
    "context",
    "competency_ids",
    "type",
    "outcome",
    "author",
    "hint_level",
    "rubric_level",
    "rationale",
    "supersedes_event_id",
    "artifact_reference",
    "artifact_ref",
    "command_summary",
})


def normalize_evidence(event: dict[str, object]) -> dict[str, object]:
    """Return a canonical evidence event without overwriting supplied provenance."""
    if not isinstance(event, dict):
        raise ValueError("evidence event must be an object")
    unknown_fields = sorted(set(event) - EVIDENCE_FIELDS)
    if unknown_fields:
        raise ValueError(f"unknown evidence field {unknown_fields[0]}")

    normalized = dict(event)
    normalized.setdefault("event_id", str(uuid.uuid4()))
    normalized.setdefault("attempt_id", str(uuid.uuid4()))
    normalized.setdefault(
        "timestamp", datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    normalized.setdefault("outcome", "accepted")
    normalized.setdefault("context", "diagnostic" if normalized.get("lesson_id") is None else "lesson")

    competency_ids = normalized.get("competency_ids")
    if isinstance(competency_ids, list):
        normalized["competency_ids"] = sorted(competency_ids)
    return normalized


def effective_level(event: dict[str, object]) -> int:
    """Calculate mastery attributable to the learner from one evidence event."""
    if event.get("outcome", "accepted") != "accepted":
        return 0
    if event.get("type") in {"environment", "disposition"}:
        return 0

    rubric_level = event.get("rubric_level")
    if isinstance(rubric_level, bool) or not isinstance(rubric_level, int):
        return 0

    attribution_cap = 3
    if event.get("author") in {"agent", "collaborative"}:
        attribution_cap = 1
    hint_level = event.get("hint_level")
    if isinstance(hint_level, int) and not isinstance(hint_level, bool) and hint_level in {4, 5}:
        attribution_cap = min(attribution_cap, 1)
    return max(0, min(rubric_level, attribution_cap))
