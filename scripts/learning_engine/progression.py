"""Curriculum-derived progress initialization."""

from __future__ import annotations

import copy

from .constants import EVIDENCE_TYPES, LESSON_STATES, SCHEMA_VERSION
from .evidence import effective_level
from .graph import topological_lessons
from .validation import validate_evidence


class StateTransitionError(ValueError):
    """Raised when progress cannot take the requested deterministic transition."""


def _curriculum_items(curriculum: dict[str, object], name: str) -> list[dict[str, object]]:
    items = curriculum.get(name)
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _accepted_diagnostic_events(
    diagnostic_evidence: list[dict[str, object]] | None,
) -> list[dict[str, object]]:
    return [
        event
        for event in diagnostic_evidence or []
        if isinstance(event, dict)
        and event.get("outcome", "accepted") == "accepted"
        and event.get("type") in EVIDENCE_TYPES
    ]


def _competency_progress(
    competencies: list[dict[str, object]], diagnostic_events: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    progress: dict[str, dict[str, object]] = {}
    for competency in competencies:
        competency_id = competency.get("id")
        if not isinstance(competency_id, str) or not competency_id:
            continue
        required_types = competency.get("required_evidence_types")
        if not isinstance(required_types, list):
            required_types = []
        permitted_types = {item for item in required_types if isinstance(item, str)}
        evidence_event_ids: list[str] = []
        level = 0
        for event in diagnostic_events:
            event_competencies = event.get("competency_ids")
            if (
                not isinstance(event_competencies, list)
                or competency_id not in event_competencies
                or event.get("type") not in permitted_types
            ):
                continue
            level = max(level, effective_level(event))
            event_id = event.get("event_id")
            if isinstance(event_id, str) and event_id:
                evidence_event_ids.append(event_id)
        progress[competency_id] = {"level": level, "evidence_event_ids": evidence_event_ids}
    return progress


def _diagnostic_satisfies_lesson(
    lesson: dict[str, object],
    competencies: dict[str, dict[str, object]],
    diagnostic_events: list[dict[str, object]],
    curriculum_competencies: dict[str, dict[str, object]],
) -> bool:
    required_competencies = lesson.get("required_competencies")
    if not isinstance(required_competencies, list) or not required_competencies:
        return False
    for competency_id in required_competencies:
        if not isinstance(competency_id, str):
            return False
        competency = curriculum_competencies.get(competency_id)
        progress = competencies.get(competency_id)
        if competency is None or progress is None:
            return False
        target_level = competency.get("target_level")
        required_types = competency.get("required_evidence_types")
        if (
            isinstance(target_level, bool)
            or not isinstance(target_level, int)
            or not isinstance(required_types, list)
            or progress["level"] < target_level
        ):
            return False
        for evidence_type in required_types:
            if not isinstance(evidence_type, str):
                return False
            highest_level = max(
                (
                    effective_level(event)
                    for event in diagnostic_events
                    if event.get("type") == evidence_type
                    and isinstance(event.get("competency_ids"), list)
                    and competency_id in event["competency_ids"]
                ),
                default=0,
            )
            if highest_level < target_level:
                return False
    return True


def evaluate_lesson(
    lesson_id: str, curriculum: dict[str, object], evidence: list[dict[str, object]]
) -> dict[str, object]:
    """Evaluate whether one lesson has sufficient independent evidence to pass."""
    lessons = {
        item.get("id"): item
        for item in _curriculum_items(curriculum, "lessons")
        if isinstance(item.get("id"), str)
    }
    competencies = {
        item.get("id"): item
        for item in _curriculum_items(curriculum, "competencies")
        if isinstance(item.get("id"), str)
    }
    lesson = lessons.get(lesson_id)
    required_competency_ids = lesson.get("required_competencies", []) if isinstance(lesson, dict) else []
    if not isinstance(required_competency_ids, list):
        required_competency_ids = []

    superseded_ids: set[str] = set()
    seen_event_ids: set[str] = set()
    for event in evidence:
        if not isinstance(event, dict):
            continue
        superseded_id = event.get("supersedes_event_id")
        if isinstance(superseded_id, str) and superseded_id in seen_event_ids:
            superseded_ids.add(superseded_id)
        event_id = event.get("event_id")
        if isinstance(event_id, str) and event_id:
            seen_event_ids.add(event_id)
    considered_events = [
        event
        for event in evidence
        if isinstance(event, dict)
        and event.get("lesson_id") == lesson_id
        and event.get("event_id") not in superseded_ids
    ]

    competency_levels: dict[str, int] = {}
    missing_evidence: dict[str, list[str]] = {}
    below_target: dict[str, dict[str, int]] = {}
    for competency_id in required_competency_ids:
        if not isinstance(competency_id, str):
            continue
        competency = competencies.get(competency_id)
        if not isinstance(competency, dict):
            continue
        required_types = competency.get("required_evidence_types")
        if not isinstance(required_types, list):
            required_types = []
        evidence_levels: list[int] = []
        missing_types: list[str] = []
        for evidence_type in required_types:
            if not isinstance(evidence_type, str):
                continue
            matched_events = [
                event
                for event in considered_events
                if event.get("type") == evidence_type
                and isinstance(event.get("competency_ids"), list)
                and competency_id in event["competency_ids"]
            ]
            if not matched_events:
                missing_types.append(evidence_type)
                evidence_levels.append(0)
            else:
                evidence_levels.append(max(effective_level(event) for event in matched_events))
        actual_level = min(evidence_levels) if evidence_levels else 0
        competency_levels[competency_id] = actual_level
        if missing_types:
            missing_evidence[competency_id] = missing_types
        target_level = competency.get("target_level")
        if isinstance(target_level, int) and not isinstance(target_level, bool) and actual_level < target_level:
            below_target[competency_id] = {"actual": actual_level, "required": target_level}

    considered_event_ids = [
        event_id
        for event in considered_events
        if isinstance((event_id := event.get("event_id")), str) and event_id
    ]
    return {
        "lesson_id": lesson_id,
        "passed": not missing_evidence and not below_target,
        "competency_levels": competency_levels,
        "missing_evidence": missing_evidence,
        "below_target": below_target,
        "considered_event_ids": considered_event_ids,
    }


def build_initial_progress(
    curriculum: dict[str, object], diagnostic_evidence: list[dict[str, object]] | None = None
) -> dict[str, object]:
    """Create deterministic initial progress from a valid curriculum and diagnostics."""
    lessons = {
        lesson_id: lesson
        for lesson in _curriculum_items(curriculum, "lessons")
        if isinstance((lesson_id := lesson.get("id")), str) and lesson_id
    }
    ordered_lessons = topological_lessons(curriculum)
    diagnostic_events = _accepted_diagnostic_events(diagnostic_evidence)
    competency_items = _curriculum_items(curriculum, "competencies")
    curriculum_competencies = {
        competency_id: competency
        for competency in competency_items
        if isinstance((competency_id := competency.get("id")), str) and competency_id
    }
    competencies = _competency_progress(competency_items, diagnostic_events)

    lesson_states = {
        lesson_id: {"state": "locked", "attempts": 0, "remediation_for": None}
        for lesson_id in ordered_lessons
    }
    for lesson_id in ordered_lessons:
        if _diagnostic_satisfies_lesson(
            lessons[lesson_id], competencies, diagnostic_events, curriculum_competencies
        ):
            lesson_states[lesson_id]["state"] = "passed"

    eligible_lessons = [
        lesson_id
        for lesson_id in ordered_lessons
        if lesson_states[lesson_id]["state"] != "passed"
        and isinstance(lessons[lesson_id].get("prerequisites"), list)
        and all(
            prerequisite in lesson_states and lesson_states[prerequisite]["state"] == "passed"
            for prerequisite in lessons[lesson_id]["prerequisites"]
        )
    ]
    active_lesson_id = eligible_lessons[0] if eligible_lessons else None
    for lesson_id in eligible_lessons:
        lesson_states[lesson_id]["state"] = "active" if lesson_id == active_lesson_id else "available"

    milestones = {
        milestone_id: {"state": "locked"}
        for milestone in _curriculum_items(curriculum, "milestones")
        if isinstance((milestone_id := milestone.get("id")), str) and milestone_id
    }
    for lesson_id, lesson_progress in lesson_states.items():
        if lesson_progress["state"] == "locked":
            continue
        milestone_id = lessons[lesson_id].get("milestone_id")
        if isinstance(milestone_id, str) and milestone_id in milestones:
            milestones[milestone_id]["state"] = "active"

    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "active_lesson_id": active_lesson_id,
        "lessons": lesson_states,
        "competencies": competencies,
        "milestones": milestones,
    }


def _curriculum_lessons(curriculum: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        lesson_id: lesson
        for lesson in _curriculum_items(curriculum, "lessons")
        if isinstance((lesson_id := lesson.get("id")), str) and lesson_id
    }


def _curriculum_competencies(curriculum: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        competency_id: competency
        for competency in _curriculum_items(curriculum, "competencies")
        if isinstance((competency_id := competency.get("id")), str) and competency_id
    }


def _curriculum_milestones(curriculum: dict[str, object]) -> set[str]:
    return {
        milestone_id
        for milestone in _curriculum_items(curriculum, "milestones")
        if isinstance((milestone_id := milestone.get("id")), str) and milestone_id
    }


def _is_nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _terminal(state: object) -> bool:
    return state in {"passed", "skipped", "waived"}


def validate_progress(progress: dict[str, object], curriculum: dict[str, object]) -> list[str]:
    """Return deterministic state-shape and curriculum-reference errors."""
    errors: list[str] = []
    if not isinstance(progress, dict):
        return ["progress must be an object"]
    if progress.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"progress.schema_version must equal {SCHEMA_VERSION}")
    if not _is_nonnegative_int(progress.get("revision")):
        errors.append("progress.revision must be a non-negative integer")

    lessons = _curriculum_lessons(curriculum)
    lesson_progress = progress.get("lessons")
    if not isinstance(lesson_progress, dict):
        errors.append("progress.lessons must be an object")
        lesson_progress = {}
    for lesson_id in sorted(lessons):
        entry = lesson_progress.get(lesson_id)
        if not isinstance(entry, dict):
            errors.append(f"progress.lessons[{lesson_id}] must be an object")
            continue
        if entry.get("state") not in LESSON_STATES:
            errors.append(f"progress.lessons[{lesson_id}].state is invalid")
        if not _is_nonnegative_int(entry.get("attempts")):
            errors.append(f"progress.lessons[{lesson_id}].attempts must be a non-negative integer")
    for lesson_id in sorted(set(lesson_progress) - set(lessons)):
        errors.append(f"progress references unknown lesson {lesson_id}")
    for lesson_id in topological_lessons(curriculum):
        entry = lesson_progress.get(lesson_id)
        if not isinstance(entry, dict) or entry.get("state") not in {"available", "active", "remediation", "passed"}:
            continue
        prerequisites = lessons[lesson_id].get("prerequisites")
        if not isinstance(prerequisites, list):
            continue
        if any(
            not isinstance(prerequisite, str)
            or not isinstance(lesson_progress.get(prerequisite), dict)
            or not _terminal(lesson_progress[prerequisite].get("state"))
            for prerequisite in prerequisites
        ):
            errors.append(f"progress.lessons[{lesson_id}] prerequisites are not terminal")

    active_lesson_id = progress.get("active_lesson_id")
    if active_lesson_id is not None:
        if not isinstance(active_lesson_id, str) or active_lesson_id not in lessons:
            errors.append(f"progress references unknown active lesson {active_lesson_id}")
        elif isinstance(lesson_progress.get(active_lesson_id), dict):
            active_state = lesson_progress[active_lesson_id].get("state")
            if active_state not in {"active", "remediation", "passed", "skipped", "waived"}:
                errors.append("progress.active_lesson_id must reference an active or terminal lesson")

    competencies = _curriculum_competencies(curriculum)
    competency_progress = progress.get("competencies")
    if not isinstance(competency_progress, dict):
        errors.append("progress.competencies must be an object")
        competency_progress = {}
    for competency_id in sorted(competencies):
        entry = competency_progress.get(competency_id)
        if not isinstance(entry, dict):
            errors.append(f"progress.competencies[{competency_id}] must be an object")
            continue
        level = entry.get("level")
        if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 3:
            errors.append(f"progress.competencies[{competency_id}].level must be an integer from 0 through 3")
        event_ids = entry.get("evidence_event_ids")
        if not isinstance(event_ids, list) or any(not isinstance(item, str) or not item for item in event_ids):
            errors.append(f"progress.competencies[{competency_id}].evidence_event_ids must be a list of non-empty strings")
    for competency_id in sorted(set(competency_progress) - set(competencies)):
        errors.append(f"progress references unknown competency {competency_id}")
    for lesson_id, lesson in lessons.items():
        lesson_entry = lesson_progress.get(lesson_id)
        if not isinstance(lesson_entry, dict) or lesson_entry.get("state") != "passed":
            continue
        required_competencies = lesson.get("required_competencies")
        if not isinstance(required_competencies, list):
            continue
        for competency_id in required_competencies:
            competency = competencies.get(competency_id) if isinstance(competency_id, str) else None
            competency_entry = competency_progress.get(competency_id) if isinstance(competency_id, str) else None
            target_level = competency.get("target_level") if isinstance(competency, dict) else None
            actual_level = competency_entry.get("level") if isinstance(competency_entry, dict) else None
            if (
                isinstance(target_level, bool)
                or not isinstance(target_level, int)
                or isinstance(actual_level, bool)
                or not isinstance(actual_level, int)
                or actual_level < target_level
            ):
                errors.append(
                    f"progress.lessons[{lesson_id}] does not meet target for competency {competency_id}"
                )

    milestones = _curriculum_milestones(curriculum)
    milestone_progress = progress.get("milestones")
    if not isinstance(milestone_progress, dict):
        errors.append("progress.milestones must be an object")
        milestone_progress = {}
    for milestone_id in sorted(milestones):
        entry = milestone_progress.get(milestone_id)
        if not isinstance(entry, dict) or not isinstance(entry.get("state"), str):
            errors.append(f"progress.milestones[{milestone_id}] must contain a state")
    for milestone_id in sorted(set(milestone_progress) - milestones):
        errors.append(f"progress references unknown milestone {milestone_id}")
    return errors


def _validated_copy(progress: dict[str, object], curriculum: dict[str, object]) -> dict[str, object]:
    errors = validate_progress(progress, curriculum)
    if errors:
        raise StateTransitionError("; ".join(errors))
    updated = copy.deepcopy(progress)
    revision = updated["revision"]
    assert isinstance(revision, int)
    updated["revision"] = revision + 1
    return updated


def _validate_transition_result(progress: dict[str, object], curriculum: dict[str, object]) -> dict[str, object]:
    errors = validate_progress(progress, curriculum)
    if errors:
        raise StateTransitionError("; ".join(errors))
    return progress


def _set_next_available(progress: dict[str, object], curriculum: dict[str, object]) -> None:
    lessons = _curriculum_lessons(curriculum)
    lesson_progress = progress["lessons"]
    assert isinstance(lesson_progress, dict)
    eligible: list[str] = []
    for lesson_id in topological_lessons(curriculum):
        entry = lesson_progress[lesson_id]
        assert isinstance(entry, dict)
        if _terminal(entry.get("state")) or entry.get("state") == "remediation":
            continue
        prerequisites = lessons[lesson_id].get("prerequisites")
        if isinstance(prerequisites, list) and all(
            isinstance(prerequisite, str)
            and isinstance(lesson_progress.get(prerequisite), dict)
            and _terminal(lesson_progress[prerequisite].get("state"))
            for prerequisite in prerequisites
        ):
            eligible.append(lesson_id)
    for lesson_id in eligible:
        entry = lesson_progress[lesson_id]
        assert isinstance(entry, dict)
        entry["state"] = "available"
    if eligible:
        selected = eligible[0]
        selected_entry = lesson_progress[selected]
        assert isinstance(selected_entry, dict)
        selected_entry["state"] = "active"
        progress["active_lesson_id"] = selected
    else:
        progress["active_lesson_id"] = None


def _evaluation_error(evaluation: dict[str, object], curriculum: dict[str, object]) -> str | None:
    lesson_id = evaluation.get("lesson_id")
    if not isinstance(lesson_id, str) or lesson_id not in _curriculum_lessons(curriculum):
        return f"evaluation references unknown lesson {lesson_id}"
    if not isinstance(evaluation.get("passed"), bool):
        return "evaluation.passed must be a boolean"
    for key in ("competency_levels", "missing_evidence", "below_target"):
        if not isinstance(evaluation.get(key), dict):
            return f"evaluation.{key} must be an object"
    considered_event_ids = evaluation.get("considered_event_ids")
    if not isinstance(considered_event_ids, list) or any(
        not isinstance(event_id, str) or not event_id for event_id in considered_event_ids
    ):
        return "evaluation.considered_event_ids must be a list of non-empty strings"
    return None


def apply_evaluation(
    progress: dict[str, object], evaluation: dict[str, object], curriculum: dict[str, object]
) -> dict[str, object]:
    """Apply one Task 4 evaluation without mutating the prior progress snapshot."""
    error = _evaluation_error(evaluation, curriculum)
    if error:
        raise StateTransitionError(error)
    updated = _validated_copy(progress, curriculum)
    lesson_id = evaluation["lesson_id"]
    assert isinstance(lesson_id, str)
    if updated.get("active_lesson_id") != lesson_id:
        raise StateTransitionError(f"lesson {lesson_id} is not active")
    lesson_progress = updated["lessons"]
    assert isinstance(lesson_progress, dict)
    entry = lesson_progress[lesson_id]
    assert isinstance(entry, dict)
    if entry.get("state") not in {"active", "remediation"}:
        raise StateTransitionError(f"lesson {lesson_id} cannot be evaluated from state {entry.get('state')}")

    competency_levels = evaluation["competency_levels"]
    considered_event_ids = evaluation["considered_event_ids"]
    assert isinstance(competency_levels, dict)
    assert isinstance(considered_event_ids, list)
    competencies = updated["competencies"]
    assert isinstance(competencies, dict)
    for competency_id, level in competency_levels.items():
        if competency_id not in competencies:
            raise StateTransitionError(f"evaluation references unknown competency {competency_id}")
        if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 3:
            raise StateTransitionError(f"evaluation.competency_levels[{competency_id}] must be an integer from 0 through 3")
        competency_entry = competencies[competency_id]
        assert isinstance(competency_entry, dict)
        prior_level = competency_entry.get("level")
        assert isinstance(prior_level, int)
        competency_entry["level"] = max(prior_level, level)
        evidence_event_ids = competency_entry.get("evidence_event_ids")
        assert isinstance(evidence_event_ids, list)
        for event_id in considered_event_ids:
            assert isinstance(event_id, str)
            if event_id not in evidence_event_ids:
                evidence_event_ids.append(event_id)

    attempts = entry.get("attempts")
    assert isinstance(attempts, int)
    entry["attempts"] = attempts + 1
    if evaluation["passed"]:
        entry["state"] = "passed"
        entry["remediation_for"] = None
    else:
        entry["state"] = "remediation"
        entry["remediation_for"] = {
            "missing_evidence": copy.deepcopy(evaluation["missing_evidence"]),
            "below_target": copy.deepcopy(evaluation["below_target"]),
        }
    return _validate_transition_result(updated, curriculum)


def advance(progress: dict[str, object], curriculum: dict[str, object]) -> dict[str, object]:
    """Activate the first topological lesson whose terminal prerequisites permit it."""
    updated = _validated_copy(progress, curriculum)
    active_lesson_id = updated.get("active_lesson_id")
    if not isinstance(active_lesson_id, str):
        raise StateTransitionError("cannot advance without an active terminal lesson")
    lessons = updated["lessons"]
    assert isinstance(lessons, dict)
    active_entry = lessons[active_lesson_id]
    assert isinstance(active_entry, dict)
    if not _terminal(active_entry.get("state")):
        raise StateTransitionError(f"active lesson {active_lesson_id} is not terminal")
    _set_next_available(updated, curriculum)
    return _validate_transition_result(updated, curriculum)


def skip_lesson(progress: dict[str, object], lesson_id: str, disposition: str) -> dict[str, object]:
    """Record a skipped or waived lesson without granting competency mastery."""
    if disposition not in {"skipped", "waived"}:
        raise StateTransitionError("disposition must be skipped or waived")
    if not isinstance(lesson_id, str) or not lesson_id:
        raise StateTransitionError("lesson_id must be a non-empty string")
    curriculum_proxy = {
        "lessons": [
            {"id": identifier, "prerequisites": []}
            for identifier in (progress.get("lessons", {}) if isinstance(progress, dict) else {})
            if isinstance(identifier, str)
        ],
        "competencies": [
            {"id": identifier}
            for identifier in (progress.get("competencies", {}) if isinstance(progress, dict) else {})
            if isinstance(identifier, str)
        ],
        "milestones": [
            {"id": identifier}
            for identifier in (progress.get("milestones", {}) if isinstance(progress, dict) else {})
            if isinstance(identifier, str)
        ],
    }
    # The public signature intentionally has no curriculum.  The state carries every
    # identifier needed to validate this local disposition transition.
    updated = _validated_copy(progress, curriculum_proxy)
    lessons = updated["lessons"]
    assert isinstance(lessons, dict)
    entry = lessons.get(lesson_id)
    if not isinstance(entry, dict):
        raise StateTransitionError(f"unknown lesson {lesson_id}")
    if _terminal(entry.get("state")):
        raise StateTransitionError(f"lesson {lesson_id} is already terminal")
    entry["state"] = disposition
    entry["remediation_for"] = None
    return _validate_transition_result(updated, curriculum_proxy)


def _validate_recovery_evidence(
    curriculum: dict[str, object], evidence: list[dict[str, object]]
) -> None:
    event_ids: set[str] = set()
    for index, event in enumerate(evidence):
        if not isinstance(event, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        errors = validate_evidence(event, curriculum)
        if errors:
            raise ValueError("; ".join(errors))
        event_id = event.get("event_id")
        assert isinstance(event_id, str)
        superseded_event_id = event.get("supersedes_event_id")
        if superseded_event_id is not None:
            if not isinstance(superseded_event_id, str) or not superseded_event_id:
                raise ValueError("evidence.supersedes_event_id must be a non-empty string")
            if superseded_event_id not in event_ids:
                raise ValueError(f"unknown superseded evidence event {superseded_event_id}")
        if event_id in event_ids:
            raise ValueError(f"duplicate evidence event_id {event_id}")
        event_ids.add(event_id)


def _superseded_event_ids(evidence: list[dict[str, object]]) -> set[str]:
    """Return every earlier journal event replaced by a later correction."""
    return {
        superseded_event_id
        for event in evidence
        if isinstance((superseded_event_id := event.get("supersedes_event_id")), str)
    }


def _ordered_recovery_attempts(
    evidence: list[dict[str, object]], superseded_event_ids: set[str]
) -> list[tuple[str, str, list[dict[str, object]]]]:
    """Keep recoverable lesson attempts contiguous and in journal order."""
    grouped_attempts: list[tuple[str, str, list[dict[str, object]]]] = []
    completed_attempts: set[tuple[str, str]] = set()
    attempt_lessons: dict[str, str] = {}
    active_key: tuple[str, str] | None = None

    for event in evidence:
        event_id = event.get("event_id")
        if event_id in superseded_event_ids:
            continue
        lesson_id = event.get("lesson_id")
        if lesson_id is None:
            continue
        assert isinstance(lesson_id, str)
        attempt_id = event.get("attempt_id")
        assert isinstance(attempt_id, str)
        key = (attempt_id, lesson_id)
        prior_lesson = attempt_lessons.setdefault(attempt_id, lesson_id)
        if prior_lesson != lesson_id:
            raise ValueError(f"attempt {attempt_id} spans multiple lessons")
        if key != active_key:
            if active_key is not None:
                completed_attempts.add(active_key)
            if key in completed_attempts:
                raise ValueError(f"attempt {attempt_id} for lesson {lesson_id} is non-contiguous")
            grouped_attempts.append((attempt_id, lesson_id, []))
            active_key = key
        grouped_attempts[-1][2].append(event)
    return grouped_attempts


def reconstruct_progress(
    curriculum: dict[str, object], evidence: list[dict[str, object]]
) -> dict[str, object]:
    """Derive a progress candidate from a valid, ordered evidence journal."""
    if not isinstance(curriculum, dict):
        raise ValueError("curriculum must be an object")
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")
    _validate_recovery_evidence(curriculum, evidence)
    superseded_event_ids = _superseded_event_ids(evidence)

    diagnostic_evidence = [
        event
        for event in evidence
        if event.get("event_id") not in superseded_event_ids
        and event.get("lesson_id") is None
        and event.get("context") == "diagnostic"
        and event.get("outcome") == "accepted"
        and event.get("type") in EVIDENCE_TYPES
    ]
    progress = build_initial_progress(curriculum, diagnostic_evidence)
    grouped_attempts = _ordered_recovery_attempts(evidence, superseded_event_ids)
    for attempt_id, lesson_id, events in grouped_attempts:
        disposition_events = [event for event in events if event.get("type") == "disposition"]
        if disposition_events:
            if len(events) != 1 or len(disposition_events) != 1:
                raise ValueError(f"attempt {attempt_id} ambiguously mixes a disposition with evidence")
            disposition_event = disposition_events[0]
            if disposition_event.get("outcome") != "accepted":
                raise ValueError(f"disposition event for lesson {lesson_id} must be accepted")
            disposition = disposition_event.get("rationale")
            if disposition not in {"skipped", "waived"}:
                raise ValueError(f"disposition event for lesson {lesson_id} must use rationale skipped or waived")
            if progress.get("active_lesson_id") != lesson_id:
                raise ValueError(f"cannot reconstruct lesson {lesson_id} before its prerequisites permit it")
            progress = skip_lesson(progress, lesson_id, disposition)
            progress = advance(progress, curriculum)
            continue
        evaluable_events = [event for event in events if event.get("type") in EVIDENCE_TYPES]
        if not evaluable_events:
            continue
        if progress.get("active_lesson_id") != lesson_id:
            raise ValueError(f"cannot reconstruct lesson {lesson_id} before its prerequisites permit it")
        evaluation = evaluate_lesson(lesson_id, curriculum, evaluable_events)
        progress = apply_evaluation(progress, evaluation, curriculum)
        if evaluation["passed"]:
            progress = advance(progress, curriculum)
    errors = validate_progress(progress, curriculum)
    if errors:
        raise ValueError("; ".join(errors))
    return progress
