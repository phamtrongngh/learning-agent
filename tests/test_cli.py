from argparse import Namespace
from contextlib import redirect_stdout
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from scripts.learning_engine.cli import dispatch, main
from scripts.learning_engine.store import CourseStore, StateWriteError
from tests.helpers import passing_lesson_one_evidence, valid_initialization


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "learning_state.py"


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ENTRYPOINT), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_envelope(self, result: subprocess.CompletedProcess[str], command: str, ok: bool) -> dict[str, object]:
        payload = json.loads(result.stdout)
        self.assertEqual(payload["command"], command)
        self.assertEqual(payload["ok"], ok)
        self.assertIsInstance(payload["data"], dict)
        self.assertIsInstance(payload["errors"], list)
        return payload

    def initialize(self, root: Path) -> None:
        payload = root / "initialization.json"
        payload.write_text(json.dumps(valid_initialization()), encoding="utf-8")
        result = self.run_cli("--root", str(root), "init", "--input", str(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_envelope(result, "init", True)

    def run_main(self, *arguments: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(arguments)
        return exit_code, json.loads(output.getvalue())

    def test_help_does_not_require_a_course_root(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = self.assert_envelope(result, "unknown", True)
        self.assertIn("usage:", payload["data"]["usage"])
        self.assertIn("--root", payload["data"]["usage"])

    def test_no_arguments_preserves_the_required_root_user_error(self) -> None:
        result = self.run_cli()

        self.assertEqual(result.returncode, 2, result.stderr)
        payload = self.assert_envelope(result, "unknown", False)
        self.assertEqual(payload["data"], {})
        self.assertEqual(payload["errors"], ["the following arguments are required: --root"])

    def test_init_status_validate_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)

            status = self.run_cli("--root", str(root), "status")
            self.assertEqual(status.returncode, 0, status.stderr)
            data = self.assert_envelope(status, "status", True)["data"]
            self.assertEqual(data["active_lesson_id"], "lesson-1")
            self.assertEqual(data["active_lesson_title"], "Foundations")
            self.assertEqual(data["course_id"], "terraform-zero-to-hero")
            self.assertEqual(data["subject"], "Terraform")
            self.assertNotIn("evidence", data)
            self.assertEqual(data["open_remediation_gaps"], {})
            self.assertIn("record", data["allowed_next_actions"])
            self.assertIn("sources", data["allowed_next_actions"])
            self.assertEqual(self.run_cli("--root", str(root), "validate").returncode, 0)
            rendered = self.run_cli("--root", str(root), "render")
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assert_envelope(rendered, "render", True)
            self.assertTrue((root / "README.md").is_file())
            self.assertTrue((root / "ROADMAP.md").is_file())

    def test_init_rejects_an_existing_course_without_overwriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            before = (root / ".learning" / "course.json").read_text(encoding="utf-8")
            payload = valid_initialization()
            payload["course"]["subject"] = "Pulumi"
            replacement = root / "replacement.json"
            replacement.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_cli("--root", str(root), "init", "--input", str(replacement))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                self.assert_envelope(result, "init", False)["errors"],
                ["course is already initialized"],
            )
            self.assertEqual((root / ".learning" / "course.json").read_text(encoding="utf-8"), before)

    def test_validate_rejects_progress_not_supported_by_the_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            progress_path = root / ".learning" / "progress.json"
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            progress["lessons"]["lesson-1"]["state"] = "passed"
            progress["lessons"]["lesson-2"]["state"] = "active"
            progress["active_lesson_id"] = "lesson-2"
            progress["competencies"]["c1"] = {"level": 2, "evidence_event_ids": ["forged"]}
            progress_path.write_text(json.dumps(progress), encoding="utf-8")

            result = self.run_cli("--root", str(root), "validate")

            self.assertEqual(result.returncode, 2)
            errors = self.assert_envelope(result, "validate", False)["errors"][0]
            self.assertIn("progress references unknown evidence event forged", errors)
            self.assertIn("progress.lessons[lesson-1].state is not supported by the evidence journal", errors)

    def test_sources_upserts_validated_official_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            source = root / "source.json"
            source.write_text(json.dumps({
                "id": "terraform-language",
                "url": "https://developer.hashicorp.com/terraform/language",
                "publisher": "HashiCorp",
                "version": "1.9",
                "verified_at": "2026-09-03",
                "freshness": "verified",
            }), encoding="utf-8")

            first = self.run_cli("--root", str(root), "sources", "--input", str(source))
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(
                self.assert_envelope(first, "sources", True)["data"]["source"]["freshness"],
                "verified",
            )

            source.write_text(json.dumps({
                "id": "terraform-language",
                "url": "https://developer.hashicorp.com/terraform/language",
                "publisher": "HashiCorp",
                "version": "1.10",
                "verified_at": "2026-09-04",
                "freshness": "stale",
            }), encoding="utf-8")
            updated = self.run_cli("--root", str(root), "sources", "--input", str(source))
            self.assertEqual(updated.returncode, 0, updated.stderr)
            self.assertEqual(
                self.assert_envelope(updated, "sources", True)["data"]["source"]["version"],
                "1.10",
            )
            stored = json.loads((root / ".learning" / "sources.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["sources"], [json.loads(source.read_text(encoding="utf-8"))])

    def test_sources_rejects_invalid_input_without_replacing_existing_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            source = root / "source.json"
            source.write_text(json.dumps({
                "id": "terraform-language",
                "publisher": "HashiCorp",
                "version": "1.9",
                "verified_at": "2026-09-03",
                "freshness": "verified",
            }), encoding="utf-8")
            self.assertEqual(self.run_cli("--root", str(root), "sources", "--input", str(source)).returncode, 0)
            before = (root / ".learning" / "sources.json").read_text(encoding="utf-8")

            source.write_text(json.dumps({
                "id": "terraform-language",
                "publisher": "HashiCorp",
                "version": "1.10",
                "verified_at": "2026-09-04",
                "freshness": "unknown",
            }), encoding="utf-8")
            result = self.run_cli("--root", str(root), "sources", "--input", str(source))

            self.assertEqual(result.returncode, 2)
            self.assert_envelope(result, "sources", False)
            self.assertEqual((root / ".learning" / "sources.json").read_text(encoding="utf-8"), before)

    def test_record_evaluate_and_advance_persist_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            for index, event in enumerate(passing_lesson_one_evidence()):
                evidence = root / f"evidence-{index}.json"
                evidence.write_text(json.dumps(event), encoding="utf-8")
                recorded = self.run_cli("--root", str(root), "record", "--input", str(evidence))
                self.assertEqual(recorded.returncode, 0, recorded.stderr)
                self.assert_envelope(recorded, "record", True)

            evaluated = self.run_cli("--root", str(root), "evaluate", "--lesson", "lesson-1")
            self.assertEqual(evaluated.returncode, 0, evaluated.stderr)
            self.assertTrue(self.assert_envelope(evaluated, "evaluate", True)["data"]["evaluation"]["passed"])
            advanced = self.run_cli("--root", str(root), "advance")
            self.assertEqual(advanced.returncode, 0, advanced.stderr)
            self.assertEqual(self.assert_envelope(advanced, "advance", True)["data"]["progress"]["active_lesson_id"], "lesson-2")

    def test_record_rejects_evidence_for_a_locked_lesson(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            evidence = root / "locked-evidence.json"
            event = passing_lesson_one_evidence()[0]
            event["lesson_id"] = "lesson-2"
            evidence.write_text(json.dumps(event), encoding="utf-8")

            result = self.run_cli("--root", str(root), "record", "--input", str(evidence))

            self.assertEqual(result.returncode, 2)
            payload = self.assert_envelope(result, "record", False)
            self.assertEqual(payload["errors"], ["evidence lesson lesson-2 is not active"])
            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")

    def test_record_rejects_dispositions_reserved_for_skip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            evidence = root / "disposition.json"
            event = passing_lesson_one_evidence()[0]
            event.update({"type": "disposition", "competency_ids": [], "rubric_level": 0})
            evidence.write_text(json.dumps(event), encoding="utf-8")

            result = self.run_cli("--root", str(root), "record", "--input", str(evidence))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                self.assert_envelope(result, "record", False)["errors"],
                ["disposition evidence must be recorded with skip"],
            )
            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")

    def test_record_rejects_an_unknown_superseded_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            evidence = root / "correction.json"
            event = passing_lesson_one_evidence()[0]
            event["supersedes_event_id"] = "missing"
            evidence.write_text(json.dumps(event), encoding="utf-8")

            result = self.run_cli("--root", str(root), "record", "--input", str(evidence))

            self.assertEqual(result.returncode, 2)
            self.assertEqual(
                self.assert_envelope(result, "record", False)["errors"],
                ["unknown superseded evidence event missing"],
            )
            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")

    def test_skip_appends_a_disposition_and_recover_is_dry_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            skipped = self.run_cli(
                "--root", str(root), "skip", "--lesson", "lesson-1", "--disposition", "skipped"
            )
            self.assertEqual(skipped.returncode, 0, skipped.stderr)
            self.assertEqual(self.assert_envelope(skipped, "skip", True)["data"]["progress"]["lessons"]["lesson-1"]["state"], "skipped")
            journal = (root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type":"disposition"', journal)

            before = (root / ".learning" / "progress.json").read_text(encoding="utf-8")
            recovered = self.run_cli("--root", str(root), "recover")
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            recovered_data = self.assert_envelope(recovered, "recover", True)["data"]
            self.assertFalse(recovered_data["applied"])
            self.assertEqual(recovered_data["progress"], json.loads(before))
            self.assertEqual((root / ".learning" / "progress.json").read_text(encoding="utf-8"), before)

    def test_invalid_user_input_has_a_json_envelope_and_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_cli("--root", str(root), "status")

            self.assertEqual(result.returncode, 2)
            payload = self.assert_envelope(result, "status", False)
            self.assertTrue(payload["errors"])

    def test_invalid_skip_does_not_append_a_disposition_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)

            result = self.run_cli(
                "--root", str(root), "skip", "--lesson", "missing", "--disposition", "skipped"
            )

            self.assertEqual(result.returncode, 2)
            self.assert_envelope(result, "skip", False)
            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")

    def test_skip_rejects_a_locked_lesson_without_journaling_a_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            before = (root / ".learning" / "progress.json").read_text(encoding="utf-8")

            result = self.run_cli(
                "--root", str(root), "skip", "--lesson", "lesson-2", "--disposition", "skipped"
            )

            self.assertEqual(result.returncode, 2)
            self.assert_envelope(result, "skip", False)
            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")
            self.assertEqual((root / ".learning" / "progress.json").read_text(encoding="utf-8"), before)

    def test_failed_skip_progress_write_rolls_back_without_journaling_a_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            before = (root / ".learning" / "progress.json").read_text(encoding="utf-8")
            original_write_progress = CourseStore.write_progress
            failed = False

            def fail_once(store: CourseStore, progress: dict[str, object]) -> None:
                nonlocal failed
                if not failed:
                    failed = True
                    raise StateWriteError("injected progress write failure")
                original_write_progress(store, progress)

            arguments = Namespace(
                root=root,
                command="skip",
                lesson="lesson-1",
                disposition="skipped",
            )
            with mock.patch.object(CourseStore, "write_progress", new=fail_once):
                with self.assertRaisesRegex(StateWriteError, "injected progress write failure"):
                    dispatch(arguments)

            self.assertEqual((root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8"), "")
            self.assertEqual((root / ".learning" / "progress.json").read_text(encoding="utf-8"), before)
            self.assertFalse((root / ".learning" / "disposition-operation.json").exists())

    def test_skip_reports_success_when_marker_clear_fails_after_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            original_clear = CourseStore._clear_disposition_operation
            failed = False

            def fail_once(store: CourseStore) -> None:
                nonlocal failed
                if not failed:
                    failed = True
                    raise StateWriteError("injected marker clear failure")
                original_clear(store)

            with mock.patch.object(CourseStore, "_clear_disposition_operation", new=fail_once):
                exit_code, envelope = self.run_main(
                    "--root", str(root), "skip", "--lesson", "lesson-1", "--disposition", "skipped"
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "skip")
            self.assertEqual(envelope["data"]["progress"]["active_lesson_id"], "lesson-2")
            self.assertFalse((root / ".learning" / "disposition-operation.json").exists())
            journal = (root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8")
            self.assertEqual(journal.count('"type":"disposition"'), 1)

    def test_skip_reports_success_when_append_raises_after_durable_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            original_append = CourseStore._append_evidence_locked

            def append_then_fail(store: CourseStore, event: dict[str, object]) -> None:
                original_append(store, event)
                raise StateWriteError("injected post-append failure")

            with mock.patch.object(CourseStore, "_append_evidence_locked", new=append_then_fail):
                exit_code, envelope = self.run_main(
                    "--root", str(root), "skip", "--lesson", "lesson-1", "--disposition", "skipped"
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "skip")
            self.assertEqual(envelope["data"]["progress"]["active_lesson_id"], "lesson-2")
            self.assertFalse((root / ".learning" / "disposition-operation.json").exists())
            journal = (root / ".learning" / "evidence.jsonl").read_text(encoding="utf-8")
            self.assertEqual(journal.count('"type":"disposition"'), 1)


if __name__ == "__main__":
    unittest.main()
