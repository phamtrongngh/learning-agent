import unittest

from scripts.learning_engine.validation import validate_evidence, validate_initialization
from tests.helpers import valid_initialization


class InitializationValidationTests(unittest.TestCase):
    def test_rejects_missing_course_goal(self) -> None:
        payload = {
            "course": {"schema_version": 1, "id": "terraform", "subject": "Terraform"},
            "curriculum": {"milestones": [], "competencies": [], "lessons": []},
            "sources": {"sources": []},
        }
        errors = validate_initialization(payload)
        self.assertIn("course.goal must be a non-empty string", errors)

    def test_rejects_unknown_required_competency(self) -> None:
        payload = {
            "course": {
                "schema_version": 1,
                "id": "terraform",
                "subject": "Terraform",
                "goal": "Provision maintainable infrastructure",
                "language": "vi",
                "status": "active",
            },
            "curriculum": {
                "competencies": [],
                "milestones": [],
                "lessons": [{
                    "id": "lesson-1",
                    "title": "State",
                    "milestone_id": "m1",
                    "prerequisites": [],
                    "required_competencies": ["missing"],
                }],
            },
            "sources": {"sources": []},
        }
        errors = validate_initialization(payload)
        self.assertIn(
            "curriculum.lessons[lesson-1] references unknown competency missing",
            errors,
        )

    def test_rejects_prerequisite_cycle(self) -> None:
        payload = valid_initialization()
        curriculum = payload["curriculum"]
        assert isinstance(curriculum, dict)
        lessons = curriculum["lessons"]
        assert isinstance(lessons, list)
        lessons[0]["prerequisites"] = ["lesson-2"]

        self.assertEqual(validate_initialization(payload), [
            "prerequisite cycle: lesson-1 -> lesson-2 -> lesson-1",
        ])

    def test_rejects_invalid_competency_target_and_source_freshness(self) -> None:
        payload = valid_initialization()
        curriculum = payload["curriculum"]
        assert isinstance(curriculum, dict)
        competencies = curriculum["competencies"]
        assert isinstance(competencies, list)
        competencies[0]["target_level"] = 4
        sources = payload["sources"]
        assert isinstance(sources, dict)
        sources["sources"] = [{
            "id": "terraform-docs",
            "publisher": "HashiCorp",
            "version": "1.9",
            "verified_at": "2026-09-02",
            "freshness": "old",
        }]

        self.assertEqual(
            validate_initialization(payload),
            [
                "curriculum.competencies[c1].target_level must be an integer from 0 through 3",
                "sources.sources[terraform-docs].freshness must be one of: stale, unverified, verified",
            ],
        )

    def test_rejects_lesson_evidence_with_diagnostic_context(self) -> None:
        errors = validate_evidence({
            "event_id": "event-1",
            "attempt_id": "attempt-1",
            "lesson_id": "lesson-1",
            "context": "diagnostic",
            "competency_ids": ["c1"],
            "type": "practical",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "A valid practical result.",
        }, valid_initialization()["curriculum"])

        self.assertEqual(errors, ["evidence.context must be lesson when lesson_id is set"])

    def test_rejects_unhashable_enum_value_without_raising(self) -> None:
        payload = valid_initialization()
        sources = payload["sources"]
        assert isinstance(sources, dict)
        sources["sources"] = [{
            "id": "terraform-docs",
            "publisher": "HashiCorp",
            "version": "1.9",
            "verified_at": "2026-09-02",
            "freshness": ["verified"],
        }]

        self.assertEqual(validate_initialization(payload), [
            "sources.sources[terraform-docs].freshness must be one of: stale, unverified, verified",
        ])

    def test_rejects_unknown_evidence_fields(self) -> None:
        event = {
            "event_id": "event-1",
            "attempt_id": "attempt-1",
            "lesson_id": "lesson-1",
            "competency_ids": ["c1"],
            "type": "practical",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "A valid practical result.",
            "override_level": 3,
        }

        self.assertEqual(validate_evidence(event, valid_initialization()["curriculum"]), [
            "evidence contains unknown field override_level",
        ])

    def test_rejects_malformed_evidence_metadata(self) -> None:
        event = {
            "event_id": "event-1",
            "attempt_id": "attempt-1",
            "timestamp": "not-a-timestamp",
            "lesson_id": "lesson-1",
            "context": "lesson",
            "competency_ids": ["c1"],
            "type": "practical",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "A valid practical result.",
            "artifact_reference": 123,
            "command_summary": False,
        }

        self.assertEqual(validate_evidence(event, valid_initialization()["curriculum"]), [
            "evidence.timestamp must be an ISO 8601 timestamp with a timezone",
            "evidence.artifact_reference must be a non-empty string",
            "evidence.command_summary must be a non-empty string",
        ])


if __name__ == "__main__":
    unittest.main()
