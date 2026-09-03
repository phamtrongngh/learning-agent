import unittest

from scripts.learning_engine.progression import build_initial_progress
from tests.helpers import valid_initialization


class InitialProgressTests(unittest.TestCase):
    def test_only_root_lesson_is_available(self) -> None:
        progress = build_initial_progress(valid_initialization()["curriculum"])
        self.assertEqual(progress["active_lesson_id"], "lesson-1")
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "active")
        self.assertEqual(progress["lessons"]["lesson-2"]["state"], "locked")
        self.assertEqual(progress["competencies"]["c1"]["level"], 0)

    def test_diagnostic_evidence_can_challenge_out_of_curriculum(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        diagnostic = [
            {"event_id":"dp","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"practical","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Independent mini-task"},
            {"event_id":"de","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"explanation","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Explained state implications"},
        ]
        progress = build_initial_progress(curriculum, diagnostic)
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "passed")
        self.assertEqual(progress["lessons"]["lesson-2"]["state"], "passed")
        self.assertIsNone(progress["active_lesson_id"])

    def test_diagnostic_evidence_passes_satisfied_descendant_lessons(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        diagnostic = [
            {"event_id":"dp","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"practical","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Independent mini-task"},
            {"event_id":"de","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"explanation","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Explained state implications"},
        ]
        progress = build_initial_progress(curriculum, diagnostic)
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "passed")
        self.assertEqual(progress["lessons"]["lesson-2"]["state"], "passed")
        self.assertIsNone(progress["active_lesson_id"])

    def test_other_roots_are_available_after_first_root_is_active(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        curriculum["lessons"].append({
            "id": "lesson-0",
            "title": "Another foundation",
            "milestone_id": "m1",
            "prerequisites": [],
            "required_competencies": ["c1"],
        })
        progress = build_initial_progress(curriculum)
        self.assertEqual(progress["active_lesson_id"], "lesson-0")
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "available")

    def test_partial_diagnostic_evidence_records_its_effective_level(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        diagnostic = [{
            "event_id": "partial",
            "attempt_id": "diagnostic",
            "lesson_id": None,
            "context": "diagnostic",
            "competency_ids": ["c1"],
            "type": "practical",
            "outcome": "accepted",
            "author": "learner",
            "hint_level": 4,
            "rubric_level": 3,
            "rationale": "Completed with a substantial hint",
        }]
        progress = build_initial_progress(curriculum, diagnostic)
        self.assertEqual(progress["competencies"]["c1"], {
            "level": 1,
            "evidence_event_ids": ["partial"],
        })
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "active")


if __name__ == "__main__":
    unittest.main()
