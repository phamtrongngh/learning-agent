import unittest
from datetime import datetime
from uuid import UUID

from scripts.learning_engine.evidence import effective_level, normalize_evidence


class EvidenceAttributionTests(unittest.TestCase):
    def test_agent_authored_work_is_at_most_assisted(self) -> None:
        event = {"author": "agent", "hint_level": 0, "rubric_level": 3}
        self.assertEqual(effective_level(event), 1)

    def test_material_hint_is_at_most_assisted(self) -> None:
        event = {"author": "learner", "hint_level": 4, "rubric_level": 3}
        self.assertEqual(effective_level(event), 1)

    def test_independent_transfer_remains_level_three(self) -> None:
        event = {"author": "learner", "hint_level": 2, "rubric_level": 3}
        self.assertEqual(effective_level(event), 3)

    def test_inconclusive_or_administrative_events_cannot_raise_mastery(self) -> None:
        self.assertEqual(
            effective_level({"outcome": "inconclusive", "rubric_level": 3}), 0
        )
        self.assertEqual(effective_level({"type": "environment", "rubric_level": 3}), 0)
        self.assertEqual(effective_level({"type": "disposition", "rubric_level": 3}), 0)


class EvidenceNormalizationTests(unittest.TestCase):
    def test_normalization_adds_missing_identity_defaults_and_context(self) -> None:
        normalized = normalize_evidence({
            "lesson_id": None,
            "competency_ids": ["c2", "c1"],
            "type": "practical",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 1,
            "rationale": "Completed independently.",
        })

        UUID(normalized["event_id"])
        self.assertTrue(normalized["timestamp"].endswith("Z"))
        datetime.fromisoformat(normalized["timestamp"].replace("Z", "+00:00"))
        self.assertEqual(normalized["outcome"], "accepted")
        self.assertEqual(normalized["context"], "diagnostic")
        self.assertEqual(normalized["competency_ids"], ["c1", "c2"])

    def test_normalization_preserves_supplied_provenance(self) -> None:
        event = {
            "event_id": "event-1",
            "attempt_id": "attempt-1",
            "timestamp": "2026-09-02T12:00:00Z",
            "lesson_id": "lesson-1",
            "competency_ids": ["c1"],
            "type": "explanation",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 1,
            "rubric_level": 2,
            "rationale": "Explains locking.",
        }

        normalized = normalize_evidence(event)

        self.assertEqual(normalized["event_id"], "event-1")
        self.assertEqual(normalized["attempt_id"], "attempt-1")
        self.assertEqual(normalized["timestamp"], "2026-09-02T12:00:00Z")
        self.assertEqual(normalized["context"], "lesson")

    def test_normalization_rejects_unknown_grading_field(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown evidence field"):
            normalize_evidence({"rubric_level": 3, "override_level": 3})
