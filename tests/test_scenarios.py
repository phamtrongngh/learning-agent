import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.learning_engine.evidence import effective_level
from scripts.learning_engine.progression import (
    advance,
    apply_evaluation,
    build_initial_progress,
    evaluate_lesson,
    skip_lesson,
)
from tests.helpers import load_terraform_fixture


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "learning_state.py"


def evidence(
    event_id: str,
    attempt_id: str,
    lesson_id: str | None,
    competency_id: str,
    evidence_type: str,
    rubric_level: int,
    *,
    hint_level: int = 0,
    outcome: str = "accepted",
    supersedes_event_id: str | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "event_id": event_id,
        "attempt_id": attempt_id,
        "lesson_id": lesson_id,
        "context": "diagnostic" if lesson_id is None else "lesson",
        "competency_ids": [competency_id],
        "type": evidence_type,
        "outcome": outcome,
        "author": "learner",
        "hint_level": hint_level,
        "rubric_level": rubric_level,
        "rationale": f"Local fixture assessment {event_id}",
        "command_summary": "fixture: local validator completed without network access",
    }
    if supersedes_event_id is not None:
        event["supersedes_event_id"] = supersedes_event_id
    return event


class ScenarioTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ENTRYPOINT), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )

    def run_json_cli(self, *arguments: str) -> dict[str, object]:
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"], envelope)
        return envelope

    def test_assisted_attempt_requires_fresh_independent_retry(self) -> None:
        """Removing independent retry evidence must leave assisted work below target."""
        curriculum = load_terraform_fixture()["curriculum"]
        assisted = [
            {"event_id":"p1","attempt_id":"a1","lesson_id":"tf-lesson-1","competency_ids":["tf-config"],"type":"practical","author":"learner","hint_level":4,"rubric_level":2,"rationale":"Completed from scaffold"},
            {"event_id":"e1","attempt_id":"a1","lesson_id":"tf-lesson-1","competency_ids":["tf-config"],"type":"explanation","author":"learner","hint_level":4,"rubric_level":2,"rationale":"Explained after scaffold"},
        ]
        self.assertEqual(effective_level(assisted[0]), 1)
        self.assertFalse(evaluate_lesson("tf-lesson-1", curriculum, assisted)["passed"])

        retry = [
            {"event_id":"p2","attempt_id":"a2","lesson_id":"tf-lesson-1","competency_ids":["tf-config"],"type":"practical","author":"learner","hint_level":1,"rubric_level":2,"rationale":"Independent changed scenario"},
            {"event_id":"e2","attempt_id":"a2","lesson_id":"tf-lesson-1","competency_ids":["tf-config"],"type":"explanation","author":"learner","hint_level":1,"rubric_level":2,"rationale":"Independent explanation"},
        ]
        self.assertTrue(evaluate_lesson("tf-lesson-1", curriculum, assisted + retry)["passed"])

    def test_passing_validator_with_assisted_explanation_stays_in_remediation(self) -> None:
        """Changing the explanation assistance cap must affect the remediation branch."""
        curriculum = load_terraform_fixture()["curriculum"]
        result = evaluate_lesson("tf-lesson-1", curriculum, [
            evidence("validator", "attempt-1", "tf-lesson-1", "tf-config", "practical", 2),
            evidence("explanation", "attempt-1", "tf-lesson-1", "tf-config", "explanation", 2, hint_level=4),
        ])

        updated = apply_evaluation(build_initial_progress(curriculum), result, curriculum)

        self.assertFalse(result["passed"])
        self.assertEqual(result["below_target"], {"tf-config": {"actual": 1, "required": 2}})
        self.assertEqual(updated["lessons"]["tf-lesson-1"]["state"], "remediation")

    def test_diagnostic_evidence_sets_declared_competency_to_level_two(self) -> None:
        """Removing either diagnostic evidence type must stop the diagnostic pass."""
        curriculum = load_terraform_fixture()["curriculum"]
        progress = build_initial_progress(curriculum, [
            evidence("diagnostic-practical", "diagnostic", None, "tf-config", "practical", 2),
            evidence("diagnostic-explanation", "diagnostic", None, "tf-config", "explanation", 2),
        ])

        self.assertEqual(progress["competencies"]["tf-config"]["level"], 2)
        self.assertEqual(progress["lessons"]["tf-lesson-1"]["state"], "passed")
        self.assertEqual(progress["active_lesson_id"], "tf-lesson-2")

    def test_transfer_requires_level_three_transfer_evidence(self) -> None:
        """Lowering transfer evidence below level three must block the transfer lesson."""
        curriculum = load_terraform_fixture()["curriculum"]
        insufficient = [
            evidence("transfer-practical", "transfer-1", "tf-lesson-4", "tf-transfer", "practical", 3),
            evidence("transfer", "transfer-1", "tf-lesson-4", "tf-transfer", "transfer", 2),
        ]
        failed = evaluate_lesson("tf-lesson-4", curriculum, insufficient)
        passed = evaluate_lesson("tf-lesson-4", curriculum, insufficient[:-1] + [
            evidence("transfer-retry", "transfer-2", "tf-lesson-4", "tf-transfer", "transfer", 3)
        ])

        self.assertFalse(failed["passed"])
        self.assertEqual(failed["below_target"], {"tf-transfer": {"actual": 2, "required": 3}})
        self.assertTrue(passed["passed"])

    def test_skipped_prerequisite_keeps_its_competency_at_zero(self) -> None:
        """Granting mastery during a skip would make this prerequisite falsely pass."""
        curriculum = load_terraform_fixture()["curriculum"]
        skipped = skip_lesson(build_initial_progress(curriculum), "tf-lesson-1", "skipped")
        advanced = advance(skipped, curriculum)

        self.assertEqual(advanced["lessons"]["tf-lesson-1"]["state"], "skipped")
        self.assertEqual(advanced["competencies"]["tf-config"]["level"], 0)
        self.assertEqual(advanced["active_lesson_id"], "tf-lesson-2")

    def test_inconclusive_network_failure_does_not_lower_diagnostic_mastery(self) -> None:
        """Treating an inconclusive environment event as negative evidence would fail this."""
        curriculum = load_terraform_fixture()["curriculum"]
        diagnostic = [
            evidence("diagnostic-practical", "diagnostic", None, "tf-config", "practical", 2),
            evidence("diagnostic-explanation", "diagnostic", None, "tf-config", "explanation", 2),
        ]
        network_failure = evidence(
            "network-unavailable", "diagnostic", None, "tf-config", "environment", 0,
            outcome="inconclusive",
        )

        baseline = build_initial_progress(curriculum, diagnostic)
        after_failure = build_initial_progress(curriculum, diagnostic + [network_failure])

        self.assertEqual(after_failure["competencies"]["tf-config"], baseline["competencies"]["tf-config"])
        self.assertEqual(after_failure["competencies"]["tf-config"]["level"], 2)

    def test_superseding_event_replaces_incorrect_semantic_assessment(self) -> None:
        """Keeping an over-scored practical event would incorrectly pass this lesson."""
        curriculum = load_terraform_fixture()["curriculum"]
        result = evaluate_lesson("tf-lesson-1", curriculum, [
            evidence("incorrect-practical", "attempt-1", "tf-lesson-1", "tf-config", "practical", 3),
            evidence(
                "corrected-practical", "attempt-1", "tf-lesson-1", "tf-config", "practical", 1,
                supersedes_event_id="incorrect-practical",
            ),
            evidence("explanation", "attempt-1", "tf-lesson-1", "tf-config", "explanation", 2),
        ])

        self.assertFalse(result["passed"])
        self.assertEqual(result["competency_levels"], {"tf-config": 1})
        self.assertEqual(result["considered_event_ids"], ["corrected-practical", "explanation"])

    def test_new_status_process_reads_active_context_from_disk(self) -> None:
        """A status command that relied on prior process memory would lose this context."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialization = root / "initialization.json"
            initialization.write_text(json.dumps(load_terraform_fixture()), encoding="utf-8")
            self.run_json_cli("--root", str(root), "init", "--input", str(initialization))

            status = self.run_json_cli("--root", str(root), "status")["data"]

            self.assertEqual(status["active_lesson_id"], "tf-lesson-1")
            self.assertEqual(status["active_lesson_title"], "Validate a local configuration")

    def test_recover_replaces_malformed_progress_from_valid_journal(self) -> None:
        """Recover must read the journal even when progress.json cannot be parsed."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialization = root / "initialization.json"
            initialization.write_text(json.dumps(load_terraform_fixture()), encoding="utf-8")
            self.run_json_cli("--root", str(root), "init", "--input", str(initialization))
            for event_id, evidence_type in (("practical", "practical"), ("explanation", "explanation")):
                payload = root / f"{event_id}.json"
                payload.write_text(json.dumps(evidence(
                    event_id, "attempt-1", "tf-lesson-1", "tf-config", evidence_type, 2,
                )), encoding="utf-8")
                self.run_json_cli("--root", str(root), "record", "--input", str(payload))
            (root / ".learning" / "progress.json").write_text("{malformed", encoding="utf-8")

            recovered = self.run_json_cli("--root", str(root), "recover", "--apply")["data"]
            resumed = self.run_json_cli("--root", str(root), "status")["data"]

            self.assertTrue(recovered["applied"])
            self.assertEqual(recovered["progress"]["lessons"]["tf-lesson-1"]["state"], "passed")
            self.assertEqual(resumed["active_lesson_id"], "tf-lesson-2")


if __name__ == "__main__":
    unittest.main()
