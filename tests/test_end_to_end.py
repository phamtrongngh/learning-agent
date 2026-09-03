import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "learning_state.py"
FIXTURE = ROOT / "tests" / "fixtures" / "terraform_initialization.json"


class EndToEndCourseTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        result = subprocess.run(
            [sys.executable, str(ENTRYPOINT), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"], envelope)
        return result, envelope

    def test_local_terraform_course_completes_first_lesson_and_resumes(self) -> None:
        """Removing any lifecycle command or disk persistence breaks this public-CLI course flow."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialization = root / "initialization.json"
            initialization.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            practical = root / "practical.json"
            explanation = root / "explanation.json"
            practical.write_text(json.dumps({
                "event_id": "local-practical",
                "attempt_id": "first-attempt",
                "lesson_id": "tf-lesson-1",
                "context": "lesson",
                "competency_ids": ["tf-config"],
                "type": "practical",
                "outcome": "accepted",
                "author": "learner",
                "hint_level": 0,
                "rubric_level": 2,
                "rationale": "The fixture's local validation summary was independently reproduced.",
                "command_summary": "fixture: terraform validate simulated locally; no provider or network used"
            }), encoding="utf-8")
            explanation.write_text(json.dumps({
                "event_id": "local-explanation",
                "attempt_id": "first-attempt",
                "lesson_id": "tf-lesson-1",
                "context": "lesson",
                "competency_ids": ["tf-config"],
                "type": "explanation",
                "outcome": "accepted",
                "author": "learner",
                "hint_level": 0,
                "rubric_level": 2,
                "rationale": "The learner explained why a validated configuration still needs an explicit state strategy.",
                "command_summary": "fixture: explanation assessed locally; no provider or network used"
            }), encoding="utf-8")

            self.run_cli("--root", str(root), "init", "--input", str(initialization))
            self.run_cli("--root", str(root), "validate")
            _, initial_status = self.run_cli("--root", str(root), "status")
            self.assertEqual(initial_status["data"]["active_lesson_id"], "tf-lesson-1")
            self.run_cli("--root", str(root), "record", "--input", str(practical))
            self.run_cli("--root", str(root), "record", "--input", str(explanation))
            _, evaluated = self.run_cli("--root", str(root), "evaluate", "--lesson", "tf-lesson-1")
            self.assertTrue(evaluated["data"]["evaluation"]["passed"])
            _, advanced = self.run_cli("--root", str(root), "advance")
            self.assertEqual(advanced["data"]["progress"]["active_lesson_id"], "tf-lesson-2")
            self.run_cli("--root", str(root), "render")
            self.run_cli("--root", str(root), "validate")
            _, resumed_status = self.run_cli("--root", str(root), "status")

            self.assertEqual(resumed_status["data"]["active_lesson_id"], "tf-lesson-2")
            self.assertEqual(resumed_status["data"]["active_lesson_title"], "Inspect local state behavior")
            self.assertTrue((root / "README.md").is_file())
            self.assertTrue((root / "ROADMAP.md").is_file())


if __name__ == "__main__":
    unittest.main()
