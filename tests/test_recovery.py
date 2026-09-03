import copy
import tempfile
import unittest
from pathlib import Path

from scripts.learning_engine.progression import reconstruct_progress
from scripts.learning_engine.store import CourseStore, StateValidationError
from tests.helpers import passing_lesson_one_evidence, valid_initialization


class RecoveryTests(unittest.TestCase):
    def test_reconstructs_passed_lesson_from_journal(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        progress = reconstruct_progress(curriculum, passing_lesson_one_evidence())
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "passed")
        self.assertEqual(progress["active_lesson_id"], "lesson-2")

    def test_rejects_unknown_evidence_reference(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        evidence = passing_lesson_one_evidence()
        evidence[0]["lesson_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "unknown lesson missing"):
            reconstruct_progress(curriculum, evidence)

    def test_recovery_rejects_an_ambiguous_lesson_attempt(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        evidence = passing_lesson_one_evidence()
        evidence[1]["lesson_id"] = "lesson-2"
        with self.assertRaisesRegex(ValueError, "attempt a1 spans multiple lessons"):
            reconstruct_progress(curriculum, evidence)

    def test_recovery_candidate_is_validated_before_replacing_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            before = copy.deepcopy(store.load_progress())
            candidate = copy.deepcopy(before)
            candidate["active_lesson_id"] = "missing"

            with self.assertRaisesRegex(StateValidationError, "unknown active lesson missing"):
                store.replace_progress_with_recovery(candidate)

            self.assertEqual(store.load_progress(), before)

    def test_recovery_replacement_rejects_an_unlocked_prerequisite_violation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            before = copy.deepcopy(store.load_progress())
            candidate = copy.deepcopy(before)
            candidate["active_lesson_id"] = "lesson-2"
            candidate["lessons"]["lesson-1"]["state"] = "locked"
            candidate["lessons"]["lesson-2"]["state"] = "active"

            with self.assertRaisesRegex(StateValidationError, "prerequisites are not terminal"):
                store.replace_progress_with_recovery(candidate)

            self.assertEqual(store.load_progress(), before)

    def test_recovery_replacement_rejects_an_available_lesson_with_locked_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            before = copy.deepcopy(store.load_progress())
            candidate = copy.deepcopy(before)
            candidate["lessons"]["lesson-1"]["state"] = "locked"
            candidate["lessons"]["lesson-2"]["state"] = "available"
            candidate["active_lesson_id"] = None

            with self.assertRaisesRegex(StateValidationError, "prerequisites are not terminal"):
                store.replace_progress_with_recovery(candidate)

            self.assertEqual(store.load_progress(), before)

    def test_recovery_does_not_treat_ordinary_evidence_as_a_disposition(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        evidence = passing_lesson_one_evidence()[:1]
        evidence[0]["rationale"] = "skipped"

        progress = reconstruct_progress(curriculum, evidence)

        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "remediation")
        self.assertNotEqual(progress["lessons"]["lesson-1"]["state"], "skipped")

    def test_recovery_requires_prerequisites_before_a_disposition(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        disposition = passing_lesson_one_evidence()[0]
        disposition.update({
            "event_id": "skip-2",
            "attempt_id": "skip-2",
            "lesson_id": "lesson-2",
            "type": "disposition",
            "competency_ids": [],
            "rationale": "skipped",
        })

        with self.assertRaisesRegex(ValueError, "before its prerequisites permit it"):
            reconstruct_progress(curriculum, [disposition])

    def test_recovery_rejects_an_unknown_superseded_event_reference(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        evidence = passing_lesson_one_evidence()
        evidence[1]["supersedes_event_id"] = "missing-event"

        with self.assertRaisesRegex(ValueError, "unknown superseded evidence event missing-event"):
            reconstruct_progress(curriculum, evidence)

    def test_recovery_rejects_unaccepted_dispositions(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        for outcome in ("rejected", "inconclusive"):
            with self.subTest(outcome=outcome):
                disposition = copy.deepcopy(passing_lesson_one_evidence()[0])
                disposition.update({
                    "event_id": f"skip-{outcome}",
                    "attempt_id": f"skip-{outcome}",
                    "type": "disposition",
                    "outcome": outcome,
                    "competency_ids": [],
                    "rationale": "skipped",
                })

                with self.assertRaisesRegex(ValueError, "disposition event .* must be accepted"):
                    reconstruct_progress(curriculum, [disposition])

    def test_recovery_excludes_diagnostic_evidence_superseded_by_rejected_correction(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        diagnostic_practical = copy.deepcopy(passing_lesson_one_evidence()[0])
        diagnostic_practical.update({
            "event_id": "diagnostic-practical",
            "attempt_id": "diagnostic",
            "lesson_id": None,
            "context": "diagnostic",
        })
        diagnostic_explanation = copy.deepcopy(passing_lesson_one_evidence()[1])
        diagnostic_explanation.update({
            "event_id": "diagnostic-explanation",
            "attempt_id": "diagnostic",
            "lesson_id": None,
            "context": "diagnostic",
        })
        rejected_correction = copy.deepcopy(diagnostic_practical)
        rejected_correction.update({
            "event_id": "diagnostic-practical-correction",
            "outcome": "rejected",
            "supersedes_event_id": "diagnostic-practical",
        })

        progress = reconstruct_progress(
            curriculum,
            [diagnostic_practical, diagnostic_explanation, rejected_correction],
        )

        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "active")
        self.assertEqual(progress["lessons"]["lesson-2"]["state"], "locked")
        self.assertNotIn(
            "diagnostic-practical",
            progress["competencies"]["c1"]["evidence_event_ids"],
        )

    def test_recovery_rejects_non_contiguous_attempt_before_future_evidence_unlocks_it(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        practical, explanation = passing_lesson_one_evidence()
        disposition = copy.deepcopy(practical)
        disposition.update({
            "event_id": "skip-lesson-2",
            "attempt_id": "skip-lesson-2",
            "lesson_id": "lesson-2",
            "type": "disposition",
            "competency_ids": [],
            "rationale": "skipped",
        })

        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            reconstruct_progress(curriculum, [practical, disposition, explanation])


if __name__ == "__main__":
    unittest.main()
