import copy
import unittest

from scripts.learning_engine.progression import (
    advance,
    apply_evaluation,
    build_initial_progress,
    skip_lesson,
    validate_progress,
)
from tests.helpers import valid_initialization


class AdvancementTests(unittest.TestCase):
    def test_failed_evaluation_keeps_next_lesson_locked(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)
        updated = apply_evaluation(progress, {
            "lesson_id": "lesson-1",
            "passed": False,
            "competency_levels": {"c1": 1},
            "missing_evidence": {"c1": ["explanation"]},
            "below_target": {"c1": {"actual": 1, "required": 2}},
            "considered_event_ids": ["event-1"],
        }, curriculum)
        self.assertEqual(updated["lessons"]["lesson-1"]["state"], "remediation")
        self.assertEqual(updated["lessons"]["lesson-2"]["state"], "locked")

    def test_pass_unlocks_and_activates_next_lesson(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)
        evaluated = apply_evaluation(progress, {
            "lesson_id": "lesson-1",
            "passed": True,
            "competency_levels": {"c1": 2},
            "missing_evidence": {},
            "below_target": {},
            "considered_event_ids": ["p", "e"],
        }, curriculum)
        updated = advance(evaluated, curriculum)
        self.assertEqual(updated["lessons"]["lesson-1"]["state"], "passed")
        self.assertEqual(updated["active_lesson_id"], "lesson-2")

    def test_milestone_state_tracks_lesson_outcomes(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)
        self.assertEqual(progress["milestones"]["m1"]["state"], "active")

        first = apply_evaluation(progress, {
            "lesson_id": "lesson-1",
            "passed": True,
            "competency_levels": {"c1": 2},
            "missing_evidence": {},
            "below_target": {},
            "considered_event_ids": ["p", "e"],
        }, curriculum)
        ready = advance(first, curriculum)
        complete = apply_evaluation(ready, {
            "lesson_id": "lesson-2",
            "passed": True,
            "competency_levels": {"c1": 2},
            "missing_evidence": {},
            "below_target": {},
            "considered_event_ids": ["p2", "e2"],
        }, curriculum)

        self.assertEqual(complete["milestones"]["m1"]["state"], "passed")

    def test_progress_rejects_an_invalid_milestone_state(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)
        progress["milestones"]["m1"]["state"] = "banana"

        self.assertIn("progress.milestones[m1].state is invalid", validate_progress(progress, curriculum))

    def test_progress_rejects_multiple_active_lessons(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        curriculum["lessons"][1]["prerequisites"] = []
        progress = build_initial_progress(curriculum)
        progress["lessons"]["lesson-2"]["state"] = "active"

        self.assertIn("progress must not contain multiple active lessons", validate_progress(progress, curriculum))

    def test_transition_is_copy_on_write_and_increments_revision_once(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)
        before = copy.deepcopy(progress)

        updated = apply_evaluation(progress, {
            "lesson_id": "lesson-1",
            "passed": False,
            "competency_levels": {"c1": 1},
            "missing_evidence": {"c1": ["explanation"]},
            "below_target": {"c1": {"actual": 1, "required": 2}},
            "considered_event_ids": ["event-1"],
        }, curriculum)

        self.assertEqual(progress, before)
        self.assertEqual(updated["revision"], before["revision"] + 1)

    def test_advance_rejects_a_nonterminal_active_lesson(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        with self.assertRaisesRegex(ValueError, "not terminal"):
            advance(build_initial_progress(curriculum), curriculum)

    def test_passing_state_requires_the_curriculum_target_level(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        with self.assertRaisesRegex(ValueError, "does not meet target"):
            apply_evaluation(build_initial_progress(curriculum), {
                "lesson_id": "lesson-1",
                "passed": True,
                "competency_levels": {"c1": 1},
                "missing_evidence": {},
                "below_target": {},
                "considered_event_ids": ["p", "e"],
            }, curriculum)

    def test_skip_records_only_an_explicit_disposition_without_mastery(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = build_initial_progress(curriculum)

        updated = skip_lesson(progress, "lesson-1", "skipped", curriculum)

        self.assertEqual(updated["lessons"]["lesson-1"]["state"], "skipped")
        self.assertEqual(updated["active_lesson_id"], "lesson-1")
        self.assertEqual(updated["competencies"]["c1"]["level"], 0)
        self.assertEqual(updated["revision"], progress["revision"] + 1)
        with self.assertRaisesRegex(ValueError, "skipped or waived"):
            skip_lesson(progress, "lesson-1", "passed", curriculum)
        with self.assertRaisesRegex(ValueError, "lesson lesson-2 is not active"):
            skip_lesson(progress, "lesson-2", "skipped", curriculum)

    def test_skip_after_a_prerequisite_passes_preserves_existing_mastery(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        passed = apply_evaluation(build_initial_progress(curriculum), {
            "lesson_id": "lesson-1",
            "passed": True,
            "competency_levels": {"c1": 2},
            "missing_evidence": {},
            "below_target": {},
            "considered_event_ids": ["p", "e"],
        }, curriculum)
        ready = advance(passed, curriculum)

        skipped = skip_lesson(ready, "lesson-2", "waived", curriculum)

        self.assertEqual(skipped["lessons"]["lesson-2"]["state"], "waived")
        self.assertEqual(skipped["competencies"]["c1"]["level"], 2)
        self.assertEqual(skipped["revision"], ready["revision"] + 1)


if __name__ == "__main__":
    unittest.main()
