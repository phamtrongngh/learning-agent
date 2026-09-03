"""Deterministic prerequisite-graph validation and traversal."""

from __future__ import annotations


def _lessons_by_id(curriculum: dict[str, object]) -> dict[str, dict[str, object]]:
    lessons = curriculum.get("lessons")
    if not isinstance(lessons, list):
        return {}
    return {
        lesson_id: lesson
        for lesson in lessons
        if isinstance(lesson, dict)
        and isinstance((lesson_id := lesson.get("id")), str)
        and lesson_id
    }


def _prerequisites(lesson: dict[str, object]) -> list[str]:
    prerequisites = lesson.get("prerequisites")
    if not isinstance(prerequisites, list):
        return []
    return [prerequisite for prerequisite in prerequisites if isinstance(prerequisite, str) and prerequisite]


def validate_prerequisite_graph(curriculum: dict[str, object]) -> list[str]:
    """Return unknown-reference and cycle errors in deterministic order."""
    lessons = _lessons_by_id(curriculum)
    errors: list[str] = []
    for lesson_id in sorted(lessons):
        for prerequisite in _prerequisites(lessons[lesson_id]):
            if prerequisite not in lessons:
                errors.append(
                    f"curriculum.lessons[{lesson_id}] references unknown prerequisite {prerequisite}"
                )

    states: dict[str, str] = {}
    path: list[str] = []

    def visit(lesson_id: str) -> None:
        state = states.get(lesson_id)
        if state == "done":
            return
        if state == "visiting":
            cycle_start = path.index(lesson_id)
            errors.append(f"prerequisite cycle: {' -> '.join(path[cycle_start:] + [lesson_id])}")
            return

        states[lesson_id] = "visiting"
        path.append(lesson_id)
        for prerequisite in _prerequisites(lessons[lesson_id]):
            if prerequisite in lessons:
                visit(prerequisite)
        path.pop()
        states[lesson_id] = "done"

    for lesson_id in sorted(lessons):
        visit(lesson_id)
    return errors


def topological_lessons(curriculum: dict[str, object]) -> list[str]:
    """Return a stable lesson order with every prerequisite before its lesson."""
    lessons = _lessons_by_id(curriculum)
    visited: set[str] = set()
    ordered: list[str] = []

    def visit(lesson_id: str) -> None:
        if lesson_id in visited:
            return
        visited.add(lesson_id)
        for prerequisite in _prerequisites(lessons[lesson_id]):
            if prerequisite in lessons:
                visit(prerequisite)
        ordered.append(lesson_id)

    for lesson_id in sorted(lessons):
        visit(lesson_id)
    return ordered
