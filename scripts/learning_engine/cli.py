"""JSON-only command dispatch for the learning-state engine."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Sequence

from .evidence import normalize_evidence
from .progression import (
    StateTransitionError,
    advance,
    apply_evaluation,
    evaluate_lesson,
    reconstruct_progress,
    skip_lesson,
    validate_progress,
)
from .rendering import render_readme, render_roadmap
from .store import CourseStore, StateValidationError, StateWriteError
from .validation import validate_evidence, validate_initialization


class UserInputError(ValueError):
    """An invalid command argument, payload, or authoritative state."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UserInputError(message)


def _parser() -> JsonArgumentParser:
    parser = JsonArgumentParser(add_help=False, prog="learning_state.py")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--help", action="store_true")
    commands = parser.add_subparsers(dest="command")
    for name in ("init", "record", "sources"):
        command = commands.add_parser(name, add_help=False)
        command.add_argument("--input", required=True, type=Path)
    commands.add_parser("status", add_help=False)
    evaluate = commands.add_parser("evaluate", add_help=False)
    evaluate.add_argument("--lesson", required=True)
    commands.add_parser("advance", add_help=False)
    skip = commands.add_parser("skip", add_help=False)
    skip.add_argument("--lesson", required=True)
    skip.add_argument("--disposition", required=True, choices=("skipped", "waived"))
    commands.add_parser("render", add_help=False)
    commands.add_parser("validate", add_help=False)
    recover = commands.add_parser("recover", add_help=False)
    recover.add_argument("--apply", action="store_true")
    return parser


def _read_json(path: Path) -> dict[str, object]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise UserInputError(f"cannot read JSON input {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise UserInputError(f"JSON input {path} must contain an object")
    return payload


def _load_state(store: CourseStore) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    try:
        return store.load_course(), store.load_curriculum(), store.load_progress(), store.load_sources()
    except (OSError, json.JSONDecodeError) as exc:
        raise UserInputError(f"cannot load authoritative course state: {exc}") from exc


def _lesson_map(curriculum: dict[str, object]) -> dict[str, dict[str, object]]:
    lessons = curriculum.get("lessons")
    return {
        lesson_id: lesson
        for lesson in lessons if isinstance(lessons, list) and isinstance(lesson, dict)
        and isinstance((lesson_id := lesson.get("id")), str)
    }


def _summary(event: dict[str, object]) -> dict[str, object]:
    return {
        key: event[key]
        for key in ("event_id", "attempt_id", "timestamp", "lesson_id", "competency_ids", "type", "outcome", "author", "rubric_level", "rationale")
        if key in event
    }


def _source_warnings(sources: dict[str, object]) -> list[dict[str, object]]:
    raw_sources = sources.get("sources")
    warnings: list[dict[str, object]] = []
    if not isinstance(raw_sources, list):
        return warnings
    for source in raw_sources:
        if not isinstance(source, dict) or source.get("freshness") == "verified":
            continue
        warnings.append({key: source[key] for key in ("id", "publisher", "version", "freshness") if key in source})
    return warnings


def _validate_supersession(event: dict[str, object], evidence: list[dict[str, object]]) -> None:
    superseded_id = event.get("supersedes_event_id")
    if superseded_id is None:
        return
    prior = next((item for item in evidence if item.get("event_id") == superseded_id), None)
    if prior is None:
        raise UserInputError(f"unknown superseded evidence event {superseded_id}")
    for field in ("lesson_id", "context", "competency_ids", "type"):
        if event.get(field) != prior.get(field):
            raise UserInputError(f"superseding evidence must preserve {field}")


def _allowed_actions(progress: dict[str, object]) -> list[str]:
    lesson_id = progress.get("active_lesson_id")
    lessons = progress.get("lessons")
    entry = lessons.get(lesson_id) if isinstance(lessons, dict) and isinstance(lesson_id, str) else None
    state = entry.get("state") if isinstance(entry, dict) else None
    actions = ["sources", "status", "render", "validate", "recover"]
    if state in {"active", "remediation"}:
        return ["record", "evaluate", "skip", *actions]
    if state in {"passed", "skipped", "waived"}:
        return ["advance", *actions]
    return actions


def status_data(store: CourseStore) -> dict[str, object]:
    """Project the compact teaching context without exposing the full journal."""
    course, curriculum, progress, sources = _load_state(store)
    lessons = _lesson_map(curriculum)
    active_lesson_id = progress.get("active_lesson_id")
    active_lesson = lessons.get(active_lesson_id) if isinstance(active_lesson_id, str) else None
    required_ids = active_lesson.get("required_competencies", []) if isinstance(active_lesson, dict) else []
    if not isinstance(required_ids, list):
        required_ids = []
    competency_items = curriculum.get("competencies")
    competencies = {
        item.get("id"): item
        for item in competency_items if isinstance(competency_items, list) and isinstance(item, dict)
        and isinstance(item.get("id"), str)
    }
    progress_competencies = progress.get("competencies")
    required_competencies = []
    for competency_id in required_ids:
        competency = competencies.get(competency_id) if isinstance(competency_id, str) else None
        entry = progress_competencies.get(competency_id) if isinstance(progress_competencies, dict) else None
        if competency is not None:
            required_competencies.append({
                "id": competency_id,
                "title": competency.get("title"),
                "target_level": competency.get("target_level"),
                "current_level": entry.get("level", 0) if isinstance(entry, dict) else 0,
                "required_evidence_types": competency.get("required_evidence_types", []),
            })

    relevant_evidence = []
    required_set = set(required_ids)
    for event in reversed(store.read_evidence()):
        event_competencies = event.get("competency_ids")
        if event.get("lesson_id") == active_lesson_id or (
            isinstance(event_competencies, list) and required_set.intersection(event_competencies)
        ):
            relevant_evidence.append(_summary(event))
        if len(relevant_evidence) == 10:
            break
    milestones = curriculum.get("milestones")
    milestone_progress = progress.get("milestones")
    milestone_summary = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "state": milestone_progress.get(item.get("id"), {}).get("state") if isinstance(milestone_progress, dict) and isinstance(milestone_progress.get(item.get("id")), dict) else None,
        }
        for item in milestones if isinstance(milestones, list) and isinstance(item, dict)
    ]
    lesson_progress = progress.get("lessons")
    active_entry = lesson_progress.get(active_lesson_id) if isinstance(lesson_progress, dict) and isinstance(active_lesson_id, str) else None
    return {
        "course_id": course.get("id"),
        "subject": course.get("subject"),
        "active_lesson_id": active_lesson_id,
        "active_lesson_title": active_lesson.get("title") if active_lesson else None,
        "milestones": milestone_summary,
        "required_competencies": required_competencies,
        "latest_relevant_evidence": relevant_evidence,
        "open_remediation_gaps": active_entry.get("remediation_for") if isinstance(active_entry, dict) and active_entry.get("remediation_for") is not None else {},
        "source_freshness_warnings": _source_warnings(sources),
        "allowed_next_actions": _allowed_actions(progress),
    }


def _validate_state(store: CourseStore) -> list[str]:
    course, curriculum, progress, sources = _load_state(store)
    errors = validate_initialization({"course": course, "curriculum": curriculum, "sources": sources})
    errors.extend(validate_progress(progress, curriculum))
    try:
        evidence = store.read_evidence()
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read evidence journal: {exc}"]
    evidence_errors = [
        f"evidence[{index}] {error}"
        for index, event in enumerate(evidence)
        for error in validate_evidence(event, curriculum)
    ]
    errors.extend(evidence_errors)
    event_ids = {
        event_id
        for event in evidence
        if isinstance((event_id := event.get("event_id")), str)
    }
    competencies = progress.get("competencies")
    if isinstance(competencies, dict):
        for entry in competencies.values():
            if not isinstance(entry, dict) or not isinstance(entry.get("evidence_event_ids"), list):
                continue
            for event_id in entry["evidence_event_ids"]:
                if isinstance(event_id, str) and event_id not in event_ids:
                    errors.append(f"progress references unknown evidence event {event_id}")
    if not evidence_errors:
        try:
            reconstructed = reconstruct_progress(curriculum, evidence)
        except ValueError as exc:
            errors.append(f"evidence journal cannot reconstruct progress: {exc}")
        else:
            stored_lessons = progress.get("lessons")
            recovered_lessons = reconstructed.get("lessons")
            if isinstance(stored_lessons, dict) and isinstance(recovered_lessons, dict):
                for lesson_id, entry in stored_lessons.items():
                    recovered = recovered_lessons.get(lesson_id)
                    if (
                        isinstance(entry, dict)
                        and _terminal_lesson_state(entry.get("state"))
                        and isinstance(recovered, dict)
                        and recovered.get("state") != entry.get("state")
                    ):
                        errors.append(
                            f"progress.lessons[{lesson_id}].state is not supported by the evidence journal"
                        )
            recovered_competencies = reconstructed.get("competencies")
            if isinstance(competencies, dict) and isinstance(recovered_competencies, dict):
                for competency_id, entry in competencies.items():
                    recovered = recovered_competencies.get(competency_id)
                    if (
                        isinstance(entry, dict)
                        and isinstance(entry.get("level"), int)
                        and isinstance(recovered, dict)
                        and isinstance(recovered.get("level"), int)
                        and entry["level"] > recovered["level"]
                    ):
                        errors.append(
                            f"progress.competencies[{competency_id}].level exceeds journal-derived mastery"
                        )
    return errors


def _terminal_lesson_state(state: object) -> bool:
    return state in {"passed", "skipped", "waived"}


def dispatch(arguments: argparse.Namespace) -> dict[str, object]:
    store = CourseStore(arguments.root)
    command = arguments.command
    if command == "init":
        store.initialize(_read_json(arguments.input))
        return {"course_root": str(arguments.root)}
    if command == "status":
        return status_data(store)
    if command == "record":
        _, curriculum, progress, _ = _load_state(store)
        event = normalize_evidence(_read_json(arguments.input))
        errors = validate_evidence(event, curriculum)
        if errors:
            raise UserInputError("; ".join(errors))
        if event.get("type") == "disposition":
            raise UserInputError("disposition evidence must be recorded with skip")
        lesson_id = event.get("lesson_id")
        lesson_progress = progress.get("lessons")
        lesson_entry = lesson_progress.get(lesson_id) if isinstance(lesson_progress, dict) else None
        if (
            lesson_id != progress.get("active_lesson_id")
            or not isinstance(lesson_entry, dict)
            or lesson_entry.get("state") not in {"active", "remediation"}
        ):
            raise UserInputError(f"evidence lesson {lesson_id} is not active")
        _validate_supersession(event, store.read_evidence())
        store.append_evidence(event)
        return {"event": event}
    if command == "sources":
        source = _read_json(arguments.input)
        store.upsert_source(source)
        return {"source": source}
    if command == "evaluate":
        _, curriculum, progress, _ = _load_state(store)
        if progress.get("active_lesson_id") != arguments.lesson:
            raise UserInputError(f"lesson {arguments.lesson} is not active")
        evaluation = evaluate_lesson(arguments.lesson, curriculum, store.read_evidence())
        updated = apply_evaluation(progress, evaluation, curriculum)
        store.write_progress(updated)
        return {"evaluation": evaluation, "progress": updated}
    if command == "advance":
        _, curriculum, progress, _ = _load_state(store)
        updated = advance(progress, curriculum)
        store.write_progress(updated)
        return {"progress": updated}
    if command == "skip":
        _, curriculum, progress, _ = _load_state(store)
        if progress.get("active_lesson_id") != arguments.lesson:
            raise UserInputError(f"lesson {arguments.lesson} is not active")
        updated = advance(skip_lesson(progress, arguments.lesson, arguments.disposition, curriculum), curriculum)
        event = normalize_evidence({
            "lesson_id": arguments.lesson,
            "competency_ids": [],
            "type": "disposition",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 0,
            "rationale": arguments.disposition,
        })
        errors = validate_evidence(event, curriculum)
        if errors:
            raise UserInputError("; ".join(errors))
        store.commit_disposition(event, updated)
        return {"event": event, "progress": updated}
    if command == "render":
        course, curriculum, progress, _ = _load_state(store)
        (arguments.root / "README.md").write_text(render_readme(course, curriculum, progress), encoding="utf-8")
        (arguments.root / "ROADMAP.md").write_text(render_roadmap(curriculum, progress), encoding="utf-8")
        return {"files": ["README.md", "ROADMAP.md"]}
    if command == "validate":
        errors = _validate_state(store)
        if errors:
            raise UserInputError("; ".join(errors))
        return {"valid": True}
    if command == "recover":
        # Recovery intentionally does not read progress.json: it is the file this
        # command repairs, so it may be malformed or otherwise unreadable.
        try:
            curriculum = store.load_curriculum()
        except (OSError, json.JSONDecodeError) as exc:
            raise UserInputError(f"cannot load authoritative course state: {exc}") from exc
        candidate = reconstruct_progress(curriculum, store.read_evidence())
        if arguments.apply:
            store.replace_progress_with_recovery(candidate)
        return {"applied": arguments.apply, "progress": candidate}
    raise UserInputError("a command is required")


def _command_from_argv(argv: Sequence[str]) -> str:
    commands = {"init", "status", "record", "sources", "evaluate", "advance", "skip", "render", "validate", "recover"}
    return next((argument for argument in argv if argument in commands), "unknown")


def main(argv: Sequence[str] | None = None) -> int:
    arguments_list = list(sys.argv[1:] if argv is None else argv)
    command = _command_from_argv(arguments_list)
    parser = _parser()
    try:
        if "--help" in arguments_list:
            data = {"usage": parser.format_help()}
        else:
            arguments = parser.parse_args(arguments_list)
            command = arguments.command or command
            if arguments.command is None:
                raise UserInputError("a command is required")
            data = dispatch(arguments)
    except (UserInputError, StateValidationError, StateTransitionError, ValueError) as exc:
        envelope = {"ok": False, "command": command, "data": {}, "errors": [str(exc)]}
        exit_code = 2
    except (StateWriteError, OSError) as exc:
        envelope = {"ok": False, "command": command, "data": {}, "errors": [str(exc)]}
        exit_code = 3
    except Exception as exc:  # pragma: no cover - emergency boundary
        if os.environ.get("LEARNING_AGENT_DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        envelope = {"ok": False, "command": command, "data": {}, "errors": [str(exc)]}
        exit_code = 3
    else:
        envelope = {"ok": True, "command": command, "data": data, "errors": []}
        exit_code = 0
    print(json.dumps(envelope, ensure_ascii=False, sort_keys=True))
    return exit_code
