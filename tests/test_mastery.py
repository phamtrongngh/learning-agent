import unittest

from scripts.learning_engine.progression import evaluate_lesson
from tests.helpers import valid_initialization


class MasteryTests(unittest.TestCase):
    def test_passing_test_without_explanation_does_not_pass(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        events = [{
            "event_id": "test-1",
            "attempt_id": "a1",
            "lesson_id": "lesson-1",
            "competency_ids": ["c1"],
            "type": "practical",
            "author": "learner",
            "hint_level": 0,
            "rubric_level": 2,
            "rationale": "Validator passed",
        }]
        result = evaluate_lesson("lesson-1", curriculum, events)
        self.assertFalse(result["passed"])
        self.assertEqual(result["missing_evidence"], {"c1": ["explanation"]})

    def test_independent_practical_and_explanation_pass(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        events = [
            {"event_id": "p", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "practical", "author": "learner", "hint_level": 1, "rubric_level": 2, "rationale": "Lab passes"},
            {"event_id": "e", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "explanation", "author": "learner", "hint_level": 1, "rubric_level": 2, "rationale": "Explains state locking"},
        ]
        result = evaluate_lesson("lesson-1", curriculum, events)
        self.assertTrue(result["passed"])
        self.assertEqual(result["competency_levels"], {"c1": 2})

    def test_pending_evidence_cannot_pass_a_lesson(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        events = [
            {"event_id": "p", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "practical", "outcome": "pending", "author": "learner", "hint_level": 0, "rubric_level": 2, "rationale": "Lab is awaiting review"},
            {"event_id": "e", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "explanation", "outcome": "pending", "author": "learner", "hint_level": 0, "rubric_level": 2, "rationale": "Explanation is awaiting review"},
        ]

        result = evaluate_lesson("lesson-1", curriculum, events)

        self.assertFalse(result["passed"])
        self.assertEqual(result["competency_levels"], {"c1": 0})

    def test_superseded_evidence_is_not_considered(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        events = [
            {"event_id": "p-old", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "practical", "author": "learner", "hint_level": 0, "rubric_level": 3, "rationale": "Originally over-scored"},
            {"event_id": "p-new", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "practical", "author": "learner", "hint_level": 0, "rubric_level": 1, "rationale": "Corrected score", "supersedes_event_id": "p-old"},
            {"event_id": "e", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "explanation", "author": "learner", "hint_level": 0, "rubric_level": 2, "rationale": "Explains state locking"},
        ]

        result = evaluate_lesson("lesson-1", curriculum, events)

        self.assertFalse(result["passed"])
        self.assertEqual(result["competency_levels"], {"c1": 1})
        self.assertEqual(result["below_target"], {"c1": {"actual": 1, "required": 2}})
        self.assertEqual(result["considered_event_ids"], ["p-new", "e"])

    def test_supersession_only_applies_to_an_earlier_event(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        events = [
            {"event_id": "correction", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "explanation", "author": "learner", "hint_level": 0, "rubric_level": 2, "rationale": "Explains state locking", "supersedes_event_id": "practical"},
            {"event_id": "practical", "attempt_id": "a1", "lesson_id": "lesson-1", "competency_ids": ["c1"], "type": "practical", "author": "learner", "hint_level": 0, "rubric_level": 2, "rationale": "Lab passes"},
        ]

        result = evaluate_lesson("lesson-1", curriculum, events)

        self.assertTrue(result["passed"])
        self.assertEqual(result["considered_event_ids"], ["correction", "practical"])
