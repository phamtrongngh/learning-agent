"""Deterministic Markdown projections of authoritative course state."""

from __future__ import annotations


_LESSON_MARKERS = {
    "locked": "🔒",
    "available": "○",
    "active": "▶",
    "remediation": "⚠",
    "passed": "✅",
    "skipped": "⏭",
    "waived": "⏭",
}


def _items(payload: dict[str, object], name: str) -> list[dict[str, object]]:
    value = payload.get(name)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _title(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value else fallback


def _course_title(course: dict[str, object]) -> str:
    explicit_title = course.get("title")
    if isinstance(explicit_title, str) and explicit_title:
        return explicit_title
    identifier = course.get("id")
    if not isinstance(identifier, str) or not identifier:
        return "Course"
    minor_words = {"and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "per", "the", "to", "via"}
    words = identifier.replace("-", " ").split()
    return " ".join(
        word if index not in {0, len(words) - 1} and word in minor_words else word[:1].upper() + word[1:]
        for index, word in enumerate(words)
    )


def _lesson(progress: dict[str, object], lesson_id: object) -> dict[str, object]:
    lessons = progress.get("lessons")
    if isinstance(lessons, dict) and isinstance(lesson_id, str):
        entry = lessons.get(lesson_id)
        if isinstance(entry, dict):
            return entry
    return {}


def _next_action(curriculum: dict[str, object], progress: dict[str, object]) -> str:
    active_lesson_id = progress.get("active_lesson_id")
    active_lesson = next(
        (lesson for lesson in _items(curriculum, "lessons") if lesson.get("id") == active_lesson_id),
        None,
    )
    if active_lesson is None:
        return "Course complete; review the roadmap and plan a transfer project."
    title = _title(active_lesson.get("title"), str(active_lesson_id))
    state = _lesson(progress, active_lesson_id).get("state")
    if state in {"passed", "skipped", "waived"}:
        return f"Advance from {title}."
    if state == "remediation":
        return f"Address the remediation gaps for {title}, then evaluate again."
    return f"Record evidence for {title}, then evaluate the lesson."


def render_readme(course: dict[str, object], curriculum: dict[str, object], progress: dict[str, object]) -> str:
    """Render a stable learner-facing summary without treating it as state."""
    lessons = _items(curriculum, "lessons")
    active_lesson_id = progress.get("active_lesson_id")
    active_lesson = next((lesson for lesson in lessons if lesson.get("id") == active_lesson_id), None)
    active_title = _title(active_lesson.get("title"), "None") if active_lesson else "None"
    completed = sum(_lesson(progress, lesson.get("id")).get("state") == "passed" for lesson in lessons)

    lines = [
        f"# {_course_title(course)}",
        "",
        "This file is generated from `.learning/`; do not edit it as course state.",
        "",
        "## Progress",
        "",
        f"Current lesson: {active_title}",
        f"Completed lessons: {completed} / {len(lessons)}",
        "",
        "## Competency levels",
        "",
    ]
    competencies = progress.get("competencies")
    for competency in _items(curriculum, "competencies"):
        competency_id = competency.get("id")
        entry = competencies.get(competency_id) if isinstance(competencies, dict) else None
        level = entry.get("level") if isinstance(entry, dict) else 0
        lines.append(
            f"- `{competency_id}` {_title(competency.get('title'), str(competency_id))}: level {level} / {competency.get('target_level', 0)}"
        )
    if not _items(curriculum, "competencies"):
        lines.append("- No competencies defined.")

    lines.extend(["", "## Next action", "", _next_action(curriculum, progress), ""])
    return "\n".join(lines)


def render_roadmap(curriculum: dict[str, object], progress: dict[str, object]) -> str:
    """Render a stable course roadmap with state-derived markers."""
    lessons = _items(curriculum, "lessons")
    milestones = _items(curriculum, "milestones")
    milestone_progress = progress.get("milestones")
    lines = [
        "# Course roadmap",
        "",
        "This file is generated from `.learning/`; do not edit it as course state.",
        "",
        "## Milestones",
        "",
    ]
    for milestone in milestones:
        milestone_id = milestone.get("id")
        entry = milestone_progress.get(milestone_id) if isinstance(milestone_progress, dict) else None
        state = entry.get("state") if isinstance(entry, dict) else "locked"
        lines.append(f"- `{milestone_id}` {_title(milestone.get('title'), str(milestone_id))}: {state}")
    if not milestones:
        lines.append("- No milestones defined.")

    lines.extend(["", "## Lessons", ""])
    for lesson in lessons:
        lesson_id = lesson.get("id")
        state = _lesson(progress, lesson_id).get("state")
        marker = _LESSON_MARKERS.get(state, "?")
        lines.append(f"- {marker} `{lesson_id}` {_title(lesson.get('title'), str(lesson_id))}")
    if not lessons:
        lines.append("- No lessons defined.")
    lines.extend(["", "## Next action", "", _next_action(curriculum, progress), ""])
    return "\n".join(lines)
