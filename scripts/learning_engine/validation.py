"""Deterministic schema checks for the course state files."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .constants import AUTHORS, EVIDENCE_TYPES, EVENT_OUTCOMES, EVENT_TYPES, SCHEMA_VERSION
from .evidence import EVIDENCE_FIELDS
from .graph import validate_prerequisite_graph


FRESHNESS_VALUES = {"verified", "stale", "unverified"}


def _require_string(value: object, field: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")
        return None
    return value


def _require_list(value: object, field: str, errors: list[str]) -> list[object] | None:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return None
    return value


def _require_object(value: object, field: str, errors: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return None
    return value


def _require_integer_in_range(
    value: object, field: str, minimum: int, maximum: int, errors: list[str]
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        errors.append(f"{field} must be an integer from {minimum} through {maximum}")
        return None
    return value


def _require_enum(value: object, field: str, allowed: set[str], errors: list[str]) -> str | None:
    if not isinstance(value, str) or value not in allowed:
        errors.append(f"{field} must be one of: {', '.join(sorted(allowed))}")
        return None
    return value


def _require_timestamp(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO 8601 timestamp with a timezone")
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None:
        errors.append(f"{field} must be an ISO 8601 timestamp with a timezone")


def _validate_identified_items(
    items: list[object] | None, field: str, required: tuple[str, ...], errors: list[str]
) -> tuple[list[dict[str, object]], set[str]]:
    valid_items: list[dict[str, object]] = []
    identifiers: set[str] = set()
    for index, item in enumerate(items or []):
        item_field = f"{field}[{index}]"
        item_object = _require_object(item, item_field, errors)
        if item_object is None:
            continue
        identifier = _require_string(item_object.get("id"), f"{item_field}.id", errors)
        label = identifier if identifier is not None else str(index)
        for name in required:
            if name != "id":
                _require_string(item_object.get(name), f"{field}[{label}].{name}", errors)
        if identifier is not None:
            if identifier in identifiers:
                errors.append(f"{field} contains duplicate id {identifier}")
            else:
                identifiers.add(identifier)
        valid_items.append(item_object)
    return valid_items, identifiers


def _validate_competencies(
    items: list[object] | None, errors: list[str]
) -> tuple[list[dict[str, object]], set[str]]:
    competencies, identifiers = _validate_identified_items(items, "curriculum.competencies", ("id", "title"), errors)
    for index, competency in enumerate(competencies):
        identifier = competency.get("id")
        label = identifier if isinstance(identifier, str) and identifier else str(index)
        _require_integer_in_range(
            competency.get("target_level"),
            f"curriculum.competencies[{label}].target_level",
            0,
            3,
            errors,
        )
        evidence_types = _require_list(
            competency.get("required_evidence_types"),
            f"curriculum.competencies[{label}].required_evidence_types",
            errors,
        )
        for evidence_index, evidence_type in enumerate(evidence_types or []):
            _require_enum(
                evidence_type,
                f"curriculum.competencies[{label}].required_evidence_types[{evidence_index}]",
                EVIDENCE_TYPES,
                errors,
            )
    return competencies, identifiers


def _validate_milestones(items: list[object] | None, errors: list[str]) -> tuple[list[dict[str, object]], set[str]]:
    return _validate_identified_items(items, "curriculum.milestones", ("id", "title"), errors)


def _validate_lessons(
    items: list[object] | None,
    competency_ids: set[str],
    milestone_ids: set[str],
    errors: list[str],
) -> None:
    lessons, _ = _validate_identified_items(items, "curriculum.lessons", ("id", "title", "milestone_id"), errors)
    for index, lesson in enumerate(lessons):
        identifier = lesson.get("id")
        label = identifier if isinstance(identifier, str) and identifier else str(index)
        milestone_id = lesson.get("milestone_id")
        if isinstance(milestone_id, str) and milestone_id and milestone_id not in milestone_ids:
            errors.append(f"curriculum.lessons[{label}] references unknown milestone {milestone_id}")
        prerequisites = _require_list(lesson.get("prerequisites"), f"curriculum.lessons[{label}].prerequisites", errors)
        for prerequisite in prerequisites or []:
            if not isinstance(prerequisite, str) or not prerequisite:
                errors.append(f"curriculum.lessons[{label}].prerequisites entries must be non-empty strings")
        required_competencies = _require_list(
            lesson.get("required_competencies"),
            f"curriculum.lessons[{label}].required_competencies",
            errors,
        )
        for competency_id in required_competencies or []:
            if not isinstance(competency_id, str) or not competency_id:
                errors.append(f"curriculum.lessons[{label}].required_competencies entries must be non-empty strings")
            elif competency_id not in competency_ids:
                errors.append(f"curriculum.lessons[{label}] references unknown competency {competency_id}")


def _validate_sources(value: object, errors: list[str]) -> None:
    sources_object = _require_object(value, "sources", errors)
    if sources_object is None:
        return
    sources = _require_list(sources_object.get("sources"), "sources.sources", errors)
    source_ids: set[str] = set()
    for index, source in enumerate(sources or []):
        source_object = _require_object(source, f"sources.sources[{index}]", errors)
        if source_object is None:
            continue
        identifier = _require_string(source_object.get("id"), f"sources.sources[{index}].id", errors)
        label = identifier if identifier is not None else str(index)
        if identifier is not None:
            if identifier in source_ids:
                errors.append(f"sources.sources contains duplicate id {identifier}")
            source_ids.add(identifier)
        for field in ("publisher", "version", "verified_at"):
            _require_string(source_object.get(field), f"sources.sources[{label}].{field}", errors)
        _require_enum(source_object.get("freshness"), f"sources.sources[{label}].freshness", FRESHNESS_VALUES, errors)


def validate_sources(payload: dict[str, object]) -> list[str]:
    """Return source-record schema errors without requiring a course initialization."""
    errors: list[str] = []
    _validate_sources(payload, errors)
    return errors


def validate_initialization(payload: dict[str, object]) -> list[str]:
    """Return every initialization error in a stable, human-readable order."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["initialization payload must be an object"]

    course = _require_object(payload.get("course"), "course", errors)
    if course is not None:
        schema_version = course.get("schema_version")
        if schema_version != SCHEMA_VERSION or isinstance(schema_version, bool):
            errors.append(f"course.schema_version must equal {SCHEMA_VERSION}")
        for field in ("id", "subject", "goal", "language", "status"):
            _require_string(course.get(field), f"course.{field}", errors)

    curriculum = _require_object(payload.get("curriculum"), "curriculum", errors)
    if curriculum is not None:
        competencies, competency_ids = _validate_competencies(curriculum.get("competencies"), errors)
        _, milestone_ids = _validate_milestones(curriculum.get("milestones"), errors)
        _validate_lessons(curriculum.get("lessons"), competency_ids, milestone_ids, errors)
        errors.extend(validate_prerequisite_graph(curriculum))

    _validate_sources(payload.get("sources"), errors)
    return errors


def validate_evidence(event: dict[str, object], curriculum: dict[str, object]) -> list[str]:
    """Return every evidence-event schema and reference error deterministically."""
    errors: list[str] = []
    if not isinstance(event, dict):
        return ["evidence event must be an object"]
    if not isinstance(curriculum, dict):
        return ["curriculum must be an object"]

    for field in sorted(set(event) - EVIDENCE_FIELDS):
        errors.append(f"evidence contains unknown field {field}")

    for field in ("event_id", "attempt_id"):
        _require_string(event.get(field), f"evidence.{field}", errors)
    if "timestamp" in event:
        _require_timestamp(event["timestamp"], "evidence.timestamp", errors)
    lesson_id = event.get("lesson_id")
    if lesson_id is not None:
        _require_string(lesson_id, "evidence.lesson_id", errors)
    context = event.get("context")
    if context is not None and context not in {"diagnostic", "lesson"}:
        errors.append("evidence.context must be diagnostic or lesson")
    if lesson_id is None and context == "lesson":
        errors.append("evidence.context must be diagnostic when lesson_id is null")
    if lesson_id is not None and context == "diagnostic":
        errors.append("evidence.context must be lesson when lesson_id is set")

    lesson_ids = {
        item.get("id")
        for item in curriculum.get("lessons", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if isinstance(lesson_id, str) and lesson_id and lesson_id not in lesson_ids:
        errors.append(f"evidence references unknown lesson {lesson_id}")

    competency_ids = {
        item.get("id")
        for item in curriculum.get("competencies", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    event_competencies = _require_list(event.get("competency_ids"), "evidence.competency_ids", errors)
    for competency_id in event_competencies or []:
        if not isinstance(competency_id, str) or not competency_id:
            errors.append("evidence.competency_ids entries must be non-empty strings")
        elif competency_id not in competency_ids:
            errors.append(f"evidence references unknown competency {competency_id}")

    _require_enum(event.get("type"), "evidence.type", EVENT_TYPES, errors)
    _require_enum(event.get("outcome", "accepted"), "evidence.outcome", EVENT_OUTCOMES, errors)
    _require_enum(event.get("author"), "evidence.author", AUTHORS, errors)
    _require_integer_in_range(event.get("hint_level"), "evidence.hint_level", 0, 5, errors)
    _require_integer_in_range(event.get("rubric_level"), "evidence.rubric_level", 0, 3, errors)
    _require_string(event.get("rationale"), "evidence.rationale", errors)
    for field in ("artifact_reference", "artifact_ref", "command_summary", "supersedes_event_id"):
        if field in event:
            _require_string(event[field], f"evidence.{field}", errors)
    return errors
