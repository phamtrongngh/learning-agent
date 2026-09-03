"""Durable, human-readable course storage."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Iterator
import uuid

from .constants import COURSE_FILES
from .evidence import normalize_evidence
from .progression import build_initial_progress, validate_progress
from .validation import validate_evidence, validate_initialization, validate_sources


class StateWriteError(RuntimeError):
    """Raised when a state mutation cannot be safely persisted."""


class StateValidationError(ValueError):
    """Raised when a proposed state payload violates the course schema."""


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    """Write JSON durably, replacing the old file only after a full write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise StateWriteError(f"cannot atomically write {path}: {exc}") from exc


class CourseStore:
    """Own the authoritative `.learning` state rooted at a course directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_root = root / ".learning"

    def _path(self, name: str) -> Path:
        return self.state_root / COURSE_FILES[name]

    def _disposition_operation_path(self) -> Path:
        """Return the durable marker for a two-file disposition mutation."""
        return self.state_root / "disposition-operation.json"

    @contextmanager
    def _evidence_append_lock(self) -> Iterator[None]:
        """Serialize cooperating evidence appends across processes."""
        lock_path = self.state_root / "evidence.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as handle:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _source_upsert_lock(self) -> Iterator[None]:
        """Serialize cooperating source read-modify-write transactions."""
        lock_path = self.state_root / "sources.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as handle:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load_json(self, name: str) -> dict[str, object]:
        with self._path(name).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise StateValidationError(f"{COURSE_FILES[name]} must contain an object")
        return payload

    def load_course(self) -> dict[str, object]:
        return self._load_json("course")

    def load_curriculum(self) -> dict[str, object]:
        return self._load_json("curriculum")

    def load_progress(self) -> dict[str, object]:
        self.recover_pending_disposition()
        return self._load_json("progress")

    def load_sources(self) -> dict[str, object]:
        return self._load_json("sources")

    def upsert_source(self, source: dict[str, object]) -> dict[str, object]:
        """Validate and atomically add or replace one source record by its stable ID."""
        if not isinstance(source, dict):
            raise StateValidationError("source must be an object")
        errors = validate_sources({"sources": [source]})
        if errors:
            raise StateValidationError("; ".join(errors))

        with self._source_upsert_lock():
            current = self.load_sources()
            errors = validate_sources(current)
            if errors:
                raise StateValidationError("; ".join(errors))
            existing = current.get("sources")
            assert isinstance(existing, list)
            source_id = source["id"]
            assert isinstance(source_id, str)
            replacement = [
                source if item.get("id") == source_id else item
                for item in existing
                if isinstance(item, dict)
            ]
            if not any(item.get("id") == source_id for item in existing if isinstance(item, dict)):
                replacement.append(source)
            updated = {"sources": replacement}
            atomic_write_json(self._path("sources"), updated)
            return updated

    def initialize(self, payload: dict[str, object]) -> None:
        if self._path("course").exists():
            raise StateValidationError("course is already initialized")
        errors = validate_initialization(payload)
        curriculum = payload.get("curriculum") if isinstance(payload, dict) else None
        raw_diagnostic_evidence = payload.get("diagnostic_evidence", []) if isinstance(payload, dict) else []
        if raw_diagnostic_evidence is None:
            raw_diagnostic_evidence = []
        diagnostic_evidence: list[dict[str, object]] = []
        if not isinstance(raw_diagnostic_evidence, list):
            errors.append("diagnostic_evidence must be a list")
        elif isinstance(curriculum, dict):
            diagnostic_event_ids: set[str] = set()
            for index, event in enumerate(raw_diagnostic_evidence):
                if not isinstance(event, dict):
                    errors.append(f"diagnostic_evidence[{index}] must be an object")
                    continue
                try:
                    event = normalize_evidence(event)
                except ValueError as exc:
                    errors.append(f"diagnostic_evidence[{index}] {exc}")
                    continue
                diagnostic_evidence.append(event)
                errors.extend(validate_evidence(event, curriculum))
                event_id = event.get("event_id")
                if isinstance(event_id, str) and event_id:
                    if event_id in diagnostic_event_ids:
                        errors.append(f"duplicate diagnostic evidence event_id {event_id}")
                    else:
                        diagnostic_event_ids.add(event_id)
        if errors:
            raise StateValidationError("; ".join(errors))

        self.state_root.mkdir(parents=True, exist_ok=True)
        (self.state_root / "sessions").mkdir(exist_ok=True)
        for directory in ("lessons", "projects", "notes"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._path("course"), payload["course"])
        atomic_write_json(self._path("curriculum"), payload["curriculum"])
        atomic_write_json(self._path("sources"), payload["sources"])
        evidence_path = self._path("evidence")
        evidence_path.touch(exist_ok=True)

        for event in diagnostic_evidence:
            self.append_evidence(event)
        self.write_progress(build_initial_progress(payload["curriculum"], diagnostic_evidence))

    def write_progress(self, progress: dict[str, object]) -> None:
        if not isinstance(progress, dict):
            raise StateValidationError("progress must be an object")
        atomic_write_json(self._path("progress"), progress)

    def _read_disposition_operation(self) -> dict[str, object] | None:
        path = self._disposition_operation_path()
        if not path.exists():
            return None
        try:
            with path.open(encoding="utf-8") as handle:
                operation = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise StateWriteError(f"cannot read disposition operation: {exc}") from exc
        if not isinstance(operation, dict):
            raise StateWriteError("disposition operation must contain an object")
        return operation

    def _clear_disposition_operation(self) -> None:
        try:
            self._disposition_operation_path().unlink(missing_ok=True)
        except OSError as exc:
            raise StateWriteError(f"cannot clear disposition operation: {exc}") from exc

    def _recover_pending_disposition_locked(self) -> None:
        """Roll back or complete an interrupted disposition using its journal fact."""
        operation = self._read_disposition_operation()
        if operation is None:
            return
        event = operation.get("event")
        previous_progress = operation.get("previous_progress")
        updated_progress = operation.get("updated_progress")
        if not isinstance(event, dict) or not isinstance(previous_progress, dict) or not isinstance(updated_progress, dict):
            raise StateWriteError("disposition operation is malformed")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise StateWriteError("disposition operation event_id must be a non-empty string")

        # A journal entry is authoritative once present.  Otherwise the pending
        # progress-only half of the operation is rolled back before it is exposed.
        has_event = any(existing.get("event_id") == event_id for existing in self.read_evidence())
        self.write_progress(updated_progress if has_event else previous_progress)
        self._clear_disposition_operation()

    def recover_pending_disposition(self) -> None:
        """Converge a previously interrupted disposition mutation, if any."""
        with self._evidence_append_lock():
            self._recover_pending_disposition_locked()

    def _disposition_is_committed_locked(
        self,
        event_id: str,
        updated_progress: dict[str, object],
    ) -> bool:
        """Return whether a disposition reached its durable commit point."""
        return (
            self._load_json("progress") == updated_progress
            and any(existing.get("event_id") == event_id for existing in self.read_evidence())
        )

    def commit_disposition(self, event: dict[str, object], updated_progress: dict[str, object]) -> None:
        """Persist a disposition journal event and its progress transition together.

        The marker lets the next read reconcile an interruption: an appended journal
        event completes its matching progress transition, while a progress-only
        transition is rolled back.  The journal therefore never remains accepted
        without the matching progress state.
        """
        if not isinstance(updated_progress, dict):
            raise StateValidationError("progress must be an object")
        try:
            normalized_event = normalize_evidence(event)
        except ValueError as exc:
            raise StateValidationError(str(exc)) from exc
        event_id = normalized_event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise StateValidationError("evidence.event_id must be a non-empty string")

        with self._evidence_append_lock():
            self._recover_pending_disposition_locked()
            previous_progress = self._load_json("progress")
            if any(existing.get("event_id") == event_id for existing in self.read_evidence()):
                raise StateWriteError(f"duplicate evidence event_id {event_id}")
            atomic_write_json(self._disposition_operation_path(), {
                "event": normalized_event,
                "previous_progress": previous_progress,
                "updated_progress": updated_progress,
            })
            try:
                self.write_progress(updated_progress)
                self._append_evidence_locked(normalized_event)
                self._clear_disposition_operation()
            except Exception:
                # This either restores the old progress (no journal event) or
                # completes the new progress (journal event present).  Once both
                # durable facts are present, cleanup failure is not a failed
                # mutation: reporting it as one would make a retry unsafe.
                try:
                    self._recover_pending_disposition_locked()
                except Exception:
                    if self._disposition_is_committed_locked(event_id, updated_progress):
                        return
                    raise
                if self._disposition_is_committed_locked(event_id, updated_progress):
                    return
                raise

    def replace_progress_with_recovery(self, candidate: dict[str, object]) -> None:
        """Atomically replace progress only after a fully reconstructed candidate validates."""
        if not isinstance(candidate, dict):
            raise StateValidationError("progress must be an object")
        errors = validate_progress(candidate, self.load_curriculum())
        if errors:
            raise StateValidationError("; ".join(errors))
        atomic_write_json(self._path("progress"), candidate)

    def append_evidence(self, event: dict[str, object]) -> None:
        if not isinstance(event, dict):
            raise StateValidationError("evidence event must be an object")
        try:
            event = normalize_evidence(event)
        except ValueError as exc:
            raise StateValidationError(str(exc)) from exc
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise StateValidationError("evidence.event_id must be a non-empty string")
        with self._evidence_append_lock():
            self._append_evidence_locked(event)

    def _append_evidence_locked(self, event: dict[str, object]) -> None:
        """Append one already-normalized event while holding the evidence lock."""
        event_id = event.get("event_id")
        assert isinstance(event_id, str) and event_id
        if any(existing.get("event_id") == event_id for existing in self.read_evidence()):
            raise StateWriteError(f"duplicate evidence event_id {event_id}")

        encoded = (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        descriptor = os.open(self._path("evidence"), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        try:
            original_size = os.fstat(descriptor).st_size
            try:
                written = os.write(descriptor, encoded)
            except OSError as exc:
                self._restore_evidence_journal(descriptor, original_size)
                raise StateWriteError(f"cannot append evidence: {exc}") from exc
            if written != len(encoded):
                self._restore_evidence_journal(descriptor, original_size)
                raise StateWriteError("cannot append complete evidence event")
            os.fsync(descriptor)
        except OSError as exc:
            raise StateWriteError(f"cannot append evidence: {exc}") from exc
        finally:
            os.close(descriptor)

    @staticmethod
    def _restore_evidence_journal(descriptor: int, original_size: int) -> None:
        """Discard a partial JSONL append while the append lock is held."""
        try:
            os.ftruncate(descriptor, original_size)
            os.fsync(descriptor)
        except OSError as exc:
            raise StateWriteError(f"cannot restore evidence journal: {exc}") from exc

    def read_evidence(self) -> list[dict[str, object]]:
        path = self._path("evidence")
        if not path.exists():
            return []
        events: list[dict[str, object]] = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise StateValidationError(f"evidence.jsonl line {line_number} must contain an object")
                events.append(event)
        return events
