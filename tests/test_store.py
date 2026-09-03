import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.learning_engine.store import CourseStore, StateValidationError, StateWriteError, atomic_write_json
from tests.helpers import valid_initialization


def _append_evidence_in_process(
    root: str,
    event: dict[str, object],
    started: object,
    completed: object,
    results: object,
) -> None:
    started.set()
    try:
        CourseStore(Path(root)).append_evidence(event)
    except Exception as exc:  # pragma: no cover - asserted by the parent process
        results.put(f"{type(exc).__name__}: {exc}")
    else:
        results.put(None)
    finally:
        completed.set()


def _upsert_source_in_process(
    root: str,
    source: dict[str, object],
    started: object,
    completed: object,
    results: object,
) -> None:
    started.set()
    try:
        CourseStore(Path(root)).upsert_source(source)
    except Exception as exc:  # pragma: no cover - asserted by the parent process
        results.put(f"{type(exc).__name__}: {exc}")
    else:
        results.put(None)
    finally:
        completed.set()


class StoreTests(unittest.TestCase):
    def test_initialize_creates_authoritative_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            self.assertEqual(store.load_course()["id"], "terraform-zero-to-hero")
            self.assertEqual(store.read_evidence(), [])

    def test_initialize_creates_curriculum_derived_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            self.assertEqual(store.load_progress(), {
                "schema_version": 1,
                "revision": 0,
                "active_lesson_id": "lesson-1",
                "lessons": {
                    "lesson-1": {"state": "active", "attempts": 0, "remediation_for": None},
                    "lesson-2": {"state": "locked", "attempts": 0, "remediation_for": None},
                },
                "competencies": {"c1": {"level": 0, "evidence_event_ids": []}},
                "milestones": {"m1": {"state": "active"}},
            })

    def test_failed_replace_preserves_previous_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            before = store.load_progress()
            with patch("scripts.learning_engine.store.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(StateWriteError):
                    store.write_progress({**before, "active_lesson_id": "changed"})
            self.assertEqual(store.load_progress(), before)

    def test_append_evidence_normalizes_raw_events_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-1"})
            self.assertEqual(store.read_evidence()[0]["event_id"], "event-1")
            journal = Path(directory) / ".learning" / "evidence.jsonl"
            persisted = json.loads(journal.read_text(encoding="utf-8"))
            self.assertEqual(persisted["attempt_id"], "attempt-1")
            self.assertEqual(persisted["event_id"], "event-1")
            self.assertEqual(persisted["outcome"], "accepted")
            self.assertEqual(persisted["context"], "diagnostic")
            self.assertTrue(persisted["timestamp"].endswith("Z"))

    def test_append_evidence_rejects_duplicate_event_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-1"})
            with self.assertRaisesRegex(StateWriteError, "duplicate evidence event_id event-1"):
                store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-2"})

    def test_initialize_rejects_duplicate_diagnostic_events_before_creating_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = valid_initialization()
            payload["diagnostic_evidence"] = [
                {
                    "event_id": "diagnostic-1",
                    "attempt_id": "baseline",
                    "lesson_id": None,
                    "context": "diagnostic",
                    "competency_ids": ["c1"],
                    "type": "practical",
                    "author": "learner",
                    "hint_level": 0,
                    "rubric_level": 2,
                    "rationale": "Independent baseline task.",
                },
                {
                    "event_id": "diagnostic-1",
                    "attempt_id": "baseline",
                    "lesson_id": None,
                    "context": "diagnostic",
                    "competency_ids": ["c1"],
                    "type": "explanation",
                    "author": "learner",
                    "hint_level": 0,
                    "rubric_level": 2,
                    "rationale": "Independent baseline explanation.",
                },
            ]

            with self.assertRaisesRegex(StateValidationError, "duplicate diagnostic evidence event_id diagnostic-1"):
                CourseStore(Path(directory)).initialize(payload)

            self.assertFalse((Path(directory) / ".learning").exists())

    def test_short_evidence_write_restores_previous_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            journal = Path(directory) / ".learning" / "evidence.jsonl"
            before = journal.read_bytes()
            real_write = os.write

            def write_prefix(descriptor: int, data: bytes) -> int:
                return real_write(descriptor, data[:3])

            with patch("scripts.learning_engine.store.os.write", side_effect=write_prefix):
                with self.assertRaisesRegex(StateWriteError, "cannot append complete evidence event"):
                    store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-1"})

            self.assertEqual(journal.read_bytes(), before)

    def test_partial_evidence_write_exception_restores_previous_journal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            journal = Path(directory) / ".learning" / "evidence.jsonl"
            before = journal.read_bytes()
            real_write = os.write

            def write_prefix_then_fail(descriptor: int, data: bytes) -> int:
                real_write(descriptor, data[:3])
                raise OSError("disk")

            with patch("scripts.learning_engine.store.os.write", side_effect=write_prefix_then_fail):
                with self.assertRaisesRegex(StateWriteError, "cannot append evidence: disk"):
                    store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-1"})

            self.assertEqual(journal.read_bytes(), before)

    def test_cooperating_append_waits_during_partial_write_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = CourseStore(root)
            store.initialize(valid_initialization())
            write_started = threading.Event()
            release_write = threading.Event()
            parent_errors: list[Exception] = []
            real_write = os.write

            def write_prefix_then_wait(descriptor: int, data: bytes) -> int:
                real_write(descriptor, data[:3])
                write_started.set()
                self.assertTrue(release_write.wait(timeout=5))
                return 3

            def append_parent_event() -> None:
                try:
                    store.append_evidence({"event_id": "parent", "attempt_id": "attempt-1"})
                except Exception as exc:
                    parent_errors.append(exc)

            context = multiprocessing.get_context("spawn")
            child_started = context.Event()
            child_completed = context.Event()
            child_results = context.Queue()
            parent = threading.Thread(target=append_parent_event)
            child = context.Process(
                target=_append_evidence_in_process,
                args=(str(root), {"event_id": "child", "attempt_id": "attempt-2"}, child_started, child_completed, child_results),
            )

            with patch("scripts.learning_engine.store.os", wraps=os) as store_os:
                store_os.write.side_effect = write_prefix_then_wait
                parent.start()
                self.assertTrue(write_started.wait(timeout=5))
                child.start()
                self.assertTrue(child_started.wait(timeout=5))
                self.assertFalse(child_completed.wait(timeout=0.5))
                release_write.set()
                parent.join(timeout=5)

            child.join(timeout=5)
            self.assertFalse(parent.is_alive())
            self.assertFalse(child.is_alive())
            self.assertEqual(child.exitcode, 0)
            self.assertIsInstance(parent_errors[0], StateWriteError)
            self.assertIsNone(child_results.get(timeout=5))
            child_event = store.read_evidence()[0]
            self.assertEqual(child_event["attempt_id"], "attempt-2")
            self.assertEqual(child_event["event_id"], "child")
            self.assertEqual(child_event["outcome"], "accepted")
            self.assertEqual(child_event["context"], "diagnostic")

    def test_cooperating_source_upserts_preserve_both_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = CourseStore(root)
            store.initialize(valid_initialization())
            first_write_started = threading.Event()
            release_first_write = threading.Event()
            parent_errors: list[Exception] = []
            first_source = {
                "id": "terraform-language",
                "url": "https://developer.hashicorp.com/terraform/language",
                "publisher": "HashiCorp",
                "version": "1.9",
                "verified_at": "2026-09-03",
                "freshness": "verified",
            }
            second_source = {
                "id": "terraform-cli",
                "url": "https://developer.hashicorp.com/terraform/cli",
                "publisher": "HashiCorp",
                "version": "1.9",
                "verified_at": "2026-09-03",
                "freshness": "verified",
            }

            def wait_before_first_replace(path: Path, payload: dict[str, object]) -> None:
                first_write_started.set()
                self.assertTrue(release_first_write.wait(timeout=5))
                atomic_write_json(path, payload)

            def upsert_first_source() -> None:
                try:
                    store.upsert_source(first_source)
                except Exception as exc:
                    parent_errors.append(exc)

            context = multiprocessing.get_context("spawn")
            child_started = context.Event()
            child_completed = context.Event()
            child_results = context.Queue()
            parent = threading.Thread(target=upsert_first_source)
            child = context.Process(
                target=_upsert_source_in_process,
                args=(str(root), second_source, child_started, child_completed, child_results),
            )

            with patch("scripts.learning_engine.store.atomic_write_json", side_effect=wait_before_first_replace):
                parent.start()
                self.assertTrue(first_write_started.wait(timeout=5))
                child.start()
                self.assertTrue(child_started.wait(timeout=5))
                self.assertFalse(child_completed.wait(timeout=0.5))
                release_first_write.set()
                parent.join(timeout=5)

            child.join(timeout=5)
            self.assertFalse(parent.is_alive())
            self.assertFalse(child.is_alive())
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(parent_errors, [])
            self.assertIsNone(child_results.get(timeout=5))
            sources = store.load_sources()["sources"]
            self.assertEqual({source["id"] for source in sources}, {"terraform-language", "terraform-cli"})


if __name__ == "__main__":
    unittest.main()
