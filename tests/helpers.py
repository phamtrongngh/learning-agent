from __future__ import annotations

import json
from pathlib import Path


def load_terraform_fixture() -> dict[str, object]:
    """Load the entirely local Terraform course used by acceptance scenarios."""
    fixture = Path(__file__).parent / "fixtures" / "terraform_initialization.json"
    with fixture.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def valid_initialization() -> dict[str, object]:
    return {
        "course": {
            "schema_version": 1,
            "id": "terraform-zero-to-hero",
            "subject": "Terraform",
            "goal": "Provision maintainable infrastructure",
            "language": "vi",
            "status": "active",
        },
        "curriculum": {
            "milestones": [{"id": "m1", "title": "Foundations"}],
            "competencies": [{
                "id": "c1",
                "title": "Understand Terraform state",
                "target_level": 2,
                "required_evidence_types": ["practical", "explanation"],
            }],
            "lessons": [
                {
                    "id": "lesson-1",
                    "title": "Foundations",
                    "milestone_id": "m1",
                    "prerequisites": [],
                    "required_competencies": ["c1"],
                },
                {
                    "id": "lesson-2",
                    "title": "State and collaboration",
                    "milestone_id": "m1",
                    "prerequisites": ["lesson-1"],
                    "required_competencies": ["c1"],
                },
            ],
        },
        "sources": {"sources": []},
    }


def passing_lesson_one_evidence() -> list[dict[str, object]]:
    return [
        {
            "event_id": "p",
            "attempt_id": "a1",
            "lesson_id": "lesson-1",
            "context": "lesson",
            "competency_ids": ["c1"],
            "type": "practical",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "The lab completed independently.",
        },
        {
            "event_id": "e",
            "attempt_id": "a1",
            "lesson_id": "lesson-1",
            "context": "lesson",
            "competency_ids": ["c1"],
            "type": "explanation",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "The explanation covers state locking independently.",
        },
    ]
