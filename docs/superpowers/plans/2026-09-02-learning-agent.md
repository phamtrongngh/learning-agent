# Learning Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and install a personal Codex plugin that turns Codex into a persistent, evidence-based tutor for terminal-practical technical skills.

**Architecture:** A Tutor Skill owns pedagogy, natural-language routing, source policy, and semantic assessment. A dependency-free Python state engine owns validated course state, evidence attribution, deterministic mastery gates, atomic persistence, recovery, rendering, and a JSON CLI. Each generated course remains a portable, human-readable directory with structured state under `.learning/`.

**Tech Stack:** Codex plugin manifest and Skill Markdown; Python 3.11+ standard library; `unittest`; JSON/JSONL; Git; official Codex plugin and skill validators.

**Spec:** `docs/superpowers/specs/2026-09-02-learning-agent-design.md`

## Global Constraints

- Plugin name is exactly `learning-agent`.
- Python runtime code uses only the standard library and supports Python 3.11+.
- V0 targets terminal-practical technical subjects; the core must not import Terraform-specific logic.
- Structured files under `.learning/` are authoritative; `README.md` and `ROADMAP.md` are rendered views.
- Learner work, agent work, and collaborative work must have distinct evidence provenance.
- Hint levels 4 and 5 cannot establish independent mastery for the associated attempt.
- Lesson mastery requires every required competency at level 2 or higher and every evidence type declared by its rubric.
- Selected milestone competencies may require level 3 transfer evidence.
- State changes use validated atomic writes; `evidence.jsonl` is append-only.
- A validation failure must never partially advance course state.
- Natural-language usage is primary; the Python CLI is an internal interface.
- Version-sensitive facts prefer current official sources and retain verification metadata.
- Cost-bearing, destructive, credentialed, production, or public-exposure labs require explicit confirmation.
- No MCP server, database, hosted service, account system, analytics, or external runtime package is introduced.

---

## Planned file map

| Path | Responsibility |
| --- | --- |
| `.codex-plugin/plugin.json` | Valid Codex plugin identity and description |
| `README.md` | Installation, user workflow, examples, development commands |
| `skills/learning-agent/SKILL.md` | Trigger conditions, tutor orchestration, reference routing |
| `skills/learning-agent/references/course-lifecycle.md` | Diagnostic, curriculum proposal, resume, revision rules |
| `skills/learning-agent/references/teaching-loop.md` | Interactive lesson rhythm and coach-first hint ladder |
| `skills/learning-agent/references/mastery-and-evidence.md` | Evidence schema, semantic scoring, retry and milestone policy |
| `skills/learning-agent/references/safety-and-sources.md` | Lab safety, secret handling, source freshness, failure classification |
| `skills/learning-agent/references/state-engine.md` | Exact CLI protocol and required call order |
| `assets/course/lesson.md.tmpl` | Just-in-time lesson brief template |
| `assets/course/session.md.tmpl` | Compact session summary template |
| `scripts/learning_state.py` | Executable Python entrypoint |
| `scripts/learning_engine/constants.py` | Schema version, enums, filenames, mastery and hint constants |
| `scripts/learning_engine/validation.py` | Explicit validators for course, curriculum, progress, sources, evidence |
| `scripts/learning_engine/store.py` | Atomic JSON writes, durable JSONL append, loading, initialization |
| `scripts/learning_engine/graph.py` | Prerequisite graph validation and ordering |
| `scripts/learning_engine/evidence.py` | Evidence normalization, attribution, aggregation |
| `scripts/learning_engine/progression.py` | Initial progress, mastery evaluation, advance, reconstruction |
| `scripts/learning_engine/rendering.py` | Deterministic learner-facing README and roadmap rendering |
| `scripts/learning_engine/cli.py` | Argument parsing, command dispatch, JSON response envelope |
| `tests/` | Unit, contract, scenario, and CLI smoke tests |
| `tests/fixtures/terraform_initialization.json` | Domain-realistic but core-independent fixture |

---

### Task 1: Scaffold the plugin and lock the manifest contract

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `README.md`
- Create: `skills/learning-agent/`
- Create: `scripts/`
- Create: `assets/`
- Create: `tests/test_plugin_contract.py`

**Interfaces:**
- Consumes: Official plugin-creator scaffold script.
- Produces: Plugin root named `learning-agent`; manifest readable as JSON with `name == "learning-agent"`; empty component directories for later tasks.

- [ ] **Step 1: Write the failing manifest contract test**

```python
# tests/test_plugin_contract.py
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginContractTests(unittest.TestCase):
    def test_manifest_and_component_roots_exist(self) -> None:
        manifest_path = ROOT / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "learning-agent")
        self.assertTrue(manifest["description"].strip())
        self.assertTrue((ROOT / "skills" / "learning-agent").is_dir())
        self.assertTrue((ROOT / "scripts").is_dir())
        self.assertTrue((ROOT / "assets").is_dir())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the contract test and verify failure**

Run: `python3 -m unittest tests.test_plugin_contract -v`

Expected: FAIL because `.codex-plugin/plugin.json` does not exist.

- [ ] **Step 3: Run the official scaffold against the existing repository**

Run from the repository root:

```bash
python3 /root/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py \
  learning-agent \
  --path .. \
  --with-skills \
  --with-scripts \
  --with-assets \
  --force
```

`--force` is intentional because the repository already contains approved
design documents; confirm those documents remain unchanged after scaffolding.

- [ ] **Step 4: Set the manifest description and create a minimal README**

Set the manifest description to:

```json
{
  "name": "learning-agent",
  "description": "Turn Codex into a persistent, evidence-based tutor for terminal-practical technical skills."
}
```

Keep every additional field generated by the scaffold unchanged. Create
`README.md` with these concrete sections: Purpose, Requirements, Installation,
Start a Course, Resume a Course, Inspect Progress, Development, and Safety.

- [ ] **Step 5: Run the contract and official plugin validators**

Run:

```bash
python3 -m unittest tests.test_plugin_contract -v
python3 /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Expected: both commands PASS.

- [ ] **Step 6: Commit the scaffold**

```bash
git add .codex-plugin README.md skills scripts assets tests/test_plugin_contract.py
git commit -m "chore: scaffold learning-agent plugin"
```

---

### Task 2: Implement constants, validation, and durable storage

**Files:**
- Create: `scripts/learning_engine/__init__.py`
- Create: `scripts/learning_engine/constants.py`
- Create: `scripts/learning_engine/validation.py`
- Create: `scripts/learning_engine/store.py`
- Create: `tests/__init__.py`
- Create: `tests/helpers.py`
- Create: `tests/test_validation.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Consumes: JSON-compatible `dict[str, object]` payloads.
- Produces:
  - `validate_initialization(payload: dict[str, object]) -> list[str]`
  - `validate_evidence(event: dict[str, object], curriculum: dict[str, object]) -> list[str]`
  - `CourseStore(root: Path)` with `initialize`, `load_*`, `write_progress`, `append_evidence`, and `read_evidence` methods.

- [ ] **Step 1: Write failing validator tests**

```python
# tests/test_validation.py
import unittest

from scripts.learning_engine.validation import validate_initialization


class InitializationValidationTests(unittest.TestCase):
    def test_rejects_missing_course_goal(self) -> None:
        payload = {
            "course": {"schema_version": 1, "id": "terraform", "subject": "Terraform"},
            "curriculum": {"milestones": [], "competencies": [], "lessons": []},
            "sources": {"sources": []},
        }
        errors = validate_initialization(payload)
        self.assertIn("course.goal must be a non-empty string", errors)

    def test_rejects_unknown_required_competency(self) -> None:
        payload = {
            "course": {
                "schema_version": 1,
                "id": "terraform",
                "subject": "Terraform",
                "goal": "Provision maintainable infrastructure",
                "language": "vi",
                "status": "active",
            },
            "curriculum": {
                "competencies": [],
                "milestones": [],
                "lessons": [{
                    "id": "lesson-1",
                    "title": "State",
                    "milestone_id": "m1",
                    "prerequisites": [],
                    "required_competencies": ["missing"],
                }],
            },
            "sources": {"sources": []},
        }
        errors = validate_initialization(payload)
        self.assertIn(
            "curriculum.lessons[lesson-1] references unknown competency missing",
            errors,
        )
```

- [ ] **Step 2: Run validator tests and verify import failure**

Run: `python3 -m unittest tests.test_validation -v`

Expected: FAIL with `ModuleNotFoundError` for `scripts.learning_engine`.

- [ ] **Step 3: Define constants and explicit validation helpers**

```python
# scripts/learning_engine/constants.py
SCHEMA_VERSION = 1
MASTERY_LEVELS = {"unobserved": 0, "assisted": 1, "independent": 2, "transfer": 3}
EVIDENCE_TYPES = {"explanation", "practical", "test", "debugging", "transfer"}
EVENT_TYPES = EVIDENCE_TYPES | {"disposition", "environment"}
EVENT_OUTCOMES = {"accepted", "inconclusive", "rejected"}
AUTHORS = {"learner", "agent", "collaborative"}
LESSON_STATES = {"locked", "available", "active", "remediation", "passed", "skipped", "waived"}
COURSE_FILES = {
    "course": "course.json",
    "curriculum": "curriculum.json",
    "progress": "progress.json",
    "evidence": "evidence.jsonl",
    "sources": "sources.json",
}
```

In `validation.py`, add `_require_string`, `_require_list`, unique-ID checks,
reference checks, allowed enum checks, mastery target checks from 0 through 3,
hint checks from 0 through 5, and source fields `publisher`, `version`,
`verified_at`, and `freshness` where freshness is `verified`, `stale`, or
`unverified`. Evidence events accept `outcome` from `EVENT_OUTCOMES`, defaulting
to `accepted`. Diagnostic evidence uses `context: "diagnostic"` and a null
`lesson_id`; lesson evidence uses `context: "lesson"` and a known lesson ID.
Only events whose type belongs to `EVIDENCE_TYPES` and whose outcome is
`accepted` can affect mastery. Validators return every detected error in
deterministic order.

- [ ] **Step 4: Write failing atomic storage and journal tests**

```python
# tests/test_store.py
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.learning_engine.store import CourseStore, StateWriteError
from tests.helpers import valid_initialization


class StoreTests(unittest.TestCase):
    def test_initialize_creates_authoritative_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            self.assertEqual(store.load_course()["id"], "terraform-zero-to-hero")
            self.assertEqual(store.read_evidence(), [])

    def test_failed_replace_preserves_previous_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            before = store.load_progress()
            with patch("scripts.learning_engine.store.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(StateWriteError):
                    store.write_progress({**before, "active_lesson_id": "changed"})
            self.assertEqual(store.load_progress(), before)

    def test_append_evidence_writes_one_valid_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CourseStore(Path(directory))
            store.initialize(valid_initialization())
            store.append_evidence({"event_id": "event-1", "attempt_id": "attempt-1"})
            self.assertEqual(store.read_evidence()[0]["event_id"], "event-1")
```

- [ ] **Step 5: Implement `CourseStore` and test helpers**

`CourseStore.initialize(payload)` must validate before creating `.learning/`,
create `sessions/`, `lessons/`, `projects/`, and `notes/`, then write
`course.json`, `curriculum.json`, and `sources.json`. Create `evidence.jsonl`
next. When `payload["diagnostic_evidence"]` is present, validate and append
those events before deriving and writing initial `progress.json`; otherwise the
journal starts empty and progress begins at the first available lesson.

Use this atomic JSON primitive:

```python
def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
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
```

Append evidence with one encoded line through an `os.open` descriptor using
`O_APPEND | O_CREAT | O_WRONLY`, a single `os.write`, and `os.fsync`. Reject an
event ID already present in the journal.

- [ ] **Step 6: Run storage and validation tests**

Run: `python3 -m unittest tests.test_validation tests.test_store -v`

Expected: PASS.

- [ ] **Step 7: Commit storage foundations**

```bash
git add scripts/learning_engine tests
git commit -m "feat: add validated durable course storage"
```

---

### Task 3: Validate prerequisite graphs and initialize progress

**Files:**
- Create: `scripts/learning_engine/graph.py`
- Create: `scripts/learning_engine/progression.py`
- Create: `tests/test_graph.py`
- Create: `tests/test_initial_progress.py`
- Modify: `scripts/learning_engine/validation.py`
- Modify: `scripts/learning_engine/store.py`

**Interfaces:**
- Consumes: Curriculum dictionaries validated for field shape.
- Produces:
  - `validate_prerequisite_graph(curriculum: dict[str, object]) -> list[str]`
  - `topological_lessons(curriculum: dict[str, object]) -> list[str]`
  - `build_initial_progress(curriculum: dict[str, object], diagnostic_evidence: list[dict[str, object]] | None = None) -> dict[str, object]`

- [ ] **Step 1: Write failing graph tests**

```python
# tests/test_graph.py
import unittest

from scripts.learning_engine.graph import topological_lessons, validate_prerequisite_graph
from tests.helpers import valid_initialization


class GraphTests(unittest.TestCase):
    def test_rejects_cycle_with_readable_path(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        curriculum["lessons"] = [
            {"id": "a", "title": "A", "milestone_id": "m1", "prerequisites": ["b"], "required_competencies": ["c1"]},
            {"id": "b", "title": "B", "milestone_id": "m1", "prerequisites": ["a"], "required_competencies": ["c1"]},
        ]
        self.assertEqual(validate_prerequisite_graph(curriculum), ["prerequisite cycle: a -> b -> a"])

    def test_topological_order_is_stable(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        self.assertEqual(topological_lessons(curriculum), ["lesson-1", "lesson-2"])
```

- [ ] **Step 2: Run graph tests and verify failure**

Run: `python3 -m unittest tests.test_graph -v`

Expected: FAIL because `graph.py` does not exist.

- [ ] **Step 3: Implement deterministic DFS validation and ordering**

Use sorted lesson IDs when selecting a new DFS root and preserve each lesson's
declared prerequisite order. Report unknown prerequisites before cycle errors.
Call `validate_prerequisite_graph` from `validate_initialization`.

- [ ] **Step 4: Write failing initial-progress tests**

```python
# tests/test_initial_progress.py
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

    def test_diagnostic_evidence_can_challenge_out_of_first_lesson(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        diagnostic = [
            {"event_id":"dp","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"practical","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Independent mini-task"},
            {"event_id":"de","attempt_id":"diagnostic","lesson_id":None,"context":"diagnostic","competency_ids":["c1"],"type":"explanation","outcome":"accepted","author":"learner","hint_level":0,"rubric_level":2,"rationale":"Explained state implications"},
        ]
        progress = build_initial_progress(curriculum, diagnostic)
        self.assertEqual(progress["lessons"]["lesson-1"]["state"], "passed")
        self.assertEqual(progress["active_lesson_id"], "lesson-2")
```

- [ ] **Step 5: Implement initial progress and connect store initialization**

The progress shape must be:

```python
{
    "schema_version": 1,
    "revision": 0,
    "active_lesson_id": "lesson-1",
    "lessons": {
        "lesson-1": {"state": "active", "attempts": 0, "remediation_for": None},
        "lesson-2": {"state": "locked", "attempts": 0, "remediation_for": None},
    },
    "competencies": {
        "c1": {"level": 0, "evidence_event_ids": []},
    },
    "milestones": {"m1": {"state": "active"}},
}
```

When several root lessons exist, activate only the first topological lesson and
mark other roots `available`. Before choosing an active lesson, apply accepted
diagnostic evidence using the same evidence-type and target-level rules as a
lesson. Lessons whose complete rubric is satisfied by diagnostic evidence are
marked `passed`; partial diagnostic evidence raises only the demonstrated
competency levels. `CourseStore.initialize` must call `build_initial_progress`
rather than accepting progress from the Tutor Skill.

- [ ] **Step 6: Run graph, validation, initialization, and store tests**

Run:

```bash
python3 -m unittest \
  tests.test_graph \
  tests.test_validation \
  tests.test_initial_progress \
  tests.test_store -v
```

Expected: PASS.

- [ ] **Step 7: Commit curriculum initialization**

```bash
git add scripts/learning_engine tests
git commit -m "feat: validate curricula and initialize progress"
```

---

### Task 4: Record evidence and compute mastery gates

**Files:**
- Create: `scripts/learning_engine/evidence.py`
- Create: `tests/test_evidence.py`
- Create: `tests/test_mastery.py`
- Modify: `scripts/learning_engine/progression.py`
- Modify: `scripts/learning_engine/validation.py`

**Interfaces:**
- Consumes: Valid evidence events and course curriculum.
- Produces:
  - `normalize_evidence(event: dict[str, object]) -> dict[str, object]`
  - `effective_level(event: dict[str, object]) -> int`
  - `evaluate_lesson(lesson_id: str, curriculum: dict[str, object], evidence: list[dict[str, object]]) -> dict[str, object]`

- [ ] **Step 1: Write failing attribution tests**

```python
# tests/test_evidence.py
import unittest

from scripts.learning_engine.evidence import effective_level


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
```

- [ ] **Step 2: Run attribution tests and verify failure**

Run: `python3 -m unittest tests.test_evidence -v`

Expected: FAIL because `evidence.py` does not exist.

- [ ] **Step 3: Implement normalization and effective-level rules**

`normalize_evidence` must add a UUID event ID and UTC ISO-8601 timestamp only
when absent, preserve a supplied attempt ID, default `outcome` to `accepted`,
infer `context` as `diagnostic` for a null lesson ID and `lesson` otherwise,
sort competency IDs, and reject unknown fields that could affect grading.
`effective_level` returns the minimum of the semantic rubric level and
attribution cap: cap 1 for agent or collaborative authorship, cap 1 for hint
level 4 or 5, otherwise cap 3.
Return level 0 immediately when `outcome` is `inconclusive` or `rejected`, or
when the event type is `environment` or `disposition`.

- [ ] **Step 4: Write failing multi-evidence mastery tests**

```python
# tests/test_mastery.py
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
```

- [ ] **Step 5: Implement lesson evaluation**

For each required competency, collect non-superseded events for the lesson,
calculate the maximum effective level by evidence type, and compare against the
competency's `target_level` and `required_evidence_types`. Return:

```python
{
    "lesson_id": lesson_id,
    "passed": bool,
    "competency_levels": {competency_id: level},
    "missing_evidence": {competency_id: [evidence_type, ...]},
    "below_target": {competency_id: {"actual": level, "required": target}},
    "considered_event_ids": [event_id, ...],
}
```

Superseded evidence remains in the journal but is excluded when a later event's
`supersedes_event_id` references it.

- [ ] **Step 6: Run evidence and mastery tests**

Run: `python3 -m unittest tests.test_evidence tests.test_mastery -v`

Expected: PASS.

- [ ] **Step 7: Commit evidence-based mastery**

```bash
git add scripts/learning_engine tests
git commit -m "feat: enforce evidence-based mastery gates"
```

---

### Task 5: Implement advancement, remediation, skip, and recovery

**Files:**
- Modify: `scripts/learning_engine/progression.py`
- Modify: `scripts/learning_engine/store.py`
- Create: `tests/test_advancement.py`
- Create: `tests/test_recovery.py`

**Interfaces:**
- Consumes: Current progress, curriculum, and complete evidence journal.
- Produces:
  - `apply_evaluation(progress, evaluation, curriculum) -> dict[str, object]`
  - `advance(progress, curriculum) -> dict[str, object]`
  - `skip_lesson(progress, lesson_id: str, disposition: str) -> dict[str, object]`
  - `reconstruct_progress(curriculum, evidence) -> dict[str, object]`

- [ ] **Step 1: Write failing advancement tests**

```python
# tests/test_advancement.py
import unittest

from scripts.learning_engine.progression import advance, apply_evaluation, build_initial_progress
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
```

- [ ] **Step 2: Run advancement tests and verify failure**

Run: `python3 -m unittest tests.test_advancement -v`

Expected: FAIL because the transition functions are absent.

- [ ] **Step 3: Implement copy-on-write transitions**

Every transition deep-copies input progress, increments `revision` exactly
once, and validates the resulting state before returning it. `advance` selects
the first topological lesson whose prerequisites are `passed`, `skipped`, or
`waived`, but preserves unmet competency gaps for skipped/waived prerequisites.
It must return a transition error if the current lesson is not terminal.

`skip_lesson` accepts only `skipped` and `waived`, records the disposition, and
never raises competency levels.

- [ ] **Step 4: Write failing recovery tests**

```python
# tests/test_recovery.py
import unittest

from scripts.learning_engine.progression import reconstruct_progress
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
```

- [ ] **Step 5: Implement deterministic recovery**

Recovery separates accepted diagnostic evidence from lesson attempts, starts
from `build_initial_progress(curriculum, diagnostic_evidence)`, groups the
remaining evidence by attempt and lesson in journal order, evaluates each
lesson, applies successful evaluations, and advances only when prerequisites
permit. Skip/waive transitions are recoverable only from explicit journal
events with type `disposition`.
Ambiguous or invalid events stop reconstruction without modifying disk.

Add `CourseStore.replace_progress_with_recovery(candidate)` that validates the
candidate and atomically replaces `progress.json` only after reconstruction
fully succeeds.

- [ ] **Step 6: Run transition and recovery tests**

Run: `python3 -m unittest tests.test_advancement tests.test_recovery -v`

Expected: PASS.

- [ ] **Step 7: Commit progression and recovery**

```bash
git add scripts/learning_engine tests
git commit -m "feat: add progression remediation and recovery"
```

---

### Task 6: Add rendering, status projection, and the JSON CLI

**Files:**
- Create: `scripts/learning_engine/rendering.py`
- Create: `scripts/learning_engine/cli.py`
- Create: `scripts/learning_state.py`
- Create: `tests/test_rendering.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `CourseStore` and command payload files.
- Produces:
  - `render_readme(course, curriculum, progress) -> str`
  - `render_roadmap(curriculum, progress) -> str`
  - CLI envelope `{ "ok": bool, "command": str, "data": object, "errors": list[str] }`.

- [ ] **Step 1: Write failing deterministic rendering tests**

```python
# tests/test_rendering.py
import unittest

from scripts.learning_engine.progression import build_initial_progress
from scripts.learning_engine.rendering import render_readme, render_roadmap
from tests.helpers import valid_initialization


class RenderingTests(unittest.TestCase):
    def test_readme_identifies_active_lesson(self) -> None:
        payload = valid_initialization()
        progress = build_initial_progress(payload["curriculum"])
        rendered = render_readme(payload["course"], payload["curriculum"], progress)
        self.assertIn("# Terraform Zero to Hero", rendered)
        self.assertIn("Current lesson: Foundations", rendered)

    def test_roadmap_uses_stable_status_markers(self) -> None:
        payload = valid_initialization()
        progress = build_initial_progress(payload["curriculum"])
        rendered = render_roadmap(payload["curriculum"], progress)
        self.assertIn("▶ `lesson-1` Foundations", rendered)
        self.assertIn("🔒 `lesson-2` State and collaboration", rendered)
```

- [ ] **Step 2: Run rendering tests and verify failure**

Run: `python3 -m unittest tests.test_rendering -v`

Expected: FAIL because `rendering.py` does not exist.

- [ ] **Step 3: Implement pure rendering functions**

Render stable headings, current lesson, completed lesson count, competency
levels, milestone states, next action, and an explicit notice that the files are
generated from `.learning/`. Do not include timestamps in rendered output so
unchanged state produces byte-identical Markdown.

- [ ] **Step 4: Write failing CLI tests**

```python
# tests/test_cli.py
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import valid_initialization


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

    def test_init_status_validate_and_render(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "initialization.json"
            payload.write_text(json.dumps(valid_initialization()), encoding="utf-8")
            initialized = self.run_cli("--root", str(root), "init", "--input", str(payload))
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            status = self.run_cli("--root", str(root), "status")
            self.assertEqual(json.loads(status.stdout)["data"]["active_lesson_id"], "lesson-1")
            self.assertEqual(self.run_cli("--root", str(root), "validate").returncode, 0)
            self.assertEqual(self.run_cli("--root", str(root), "render").returncode, 0)
            self.assertTrue((root / "README.md").is_file())
            self.assertTrue((root / "ROADMAP.md").is_file())
```

- [ ] **Step 5: Implement CLI dispatch and entrypoint**

Support these exact forms:

```text
learning_state.py --root COURSE init --input initialization.json
learning_state.py --root COURSE status
learning_state.py --root COURSE record --input evidence.json
learning_state.py --root COURSE evaluate --lesson LESSON_ID
learning_state.py --root COURSE advance
learning_state.py --root COURSE skip --lesson LESSON_ID --disposition skipped|waived
learning_state.py --root COURSE render
learning_state.py --root COURSE validate
learning_state.py --root COURSE recover
learning_state.py --root COURSE recover --apply
```

Exit 0 for success, 2 for invalid user or state input, and 3 for storage or
unexpected runtime failure. Every exit writes one JSON envelope to stdout.
Tracebacks go to stderr only when `LEARNING_AGENT_DEBUG=1`.

The `status` payload contains course ID, subject, active lesson ID/title,
milestone summary, required competencies, latest relevant evidence summaries,
open remediation gaps, source freshness warnings, and allowed next actions. It
must not return the whole evidence journal.

Command mutation semantics are exact: `record` appends one normalized event;
`evaluate` recomputes and atomically persists the active lesson's evaluation;
`advance` atomically persists the next allowed transition; `skip` appends a
disposition journal event and atomically persists the disposition; `recover`
is dry-run unless `--apply` is supplied.

- [ ] **Step 6: Run the complete engine suite**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS.

- [ ] **Step 7: Commit CLI and projections**

```bash
git add scripts tests
git commit -m "feat: add course state cli and dashboards"
```

---

### Task 7: Author the Tutor Skill and pedagogical references

**Files:**
- Create: `skills/learning-agent/SKILL.md`
- Create: `skills/learning-agent/references/course-lifecycle.md`
- Create: `skills/learning-agent/references/teaching-loop.md`
- Create: `skills/learning-agent/references/mastery-and-evidence.md`
- Create: `skills/learning-agent/references/safety-and-sources.md`
- Create: `skills/learning-agent/references/state-engine.md`
- Create: `assets/course/lesson.md.tmpl`
- Create: `assets/course/session.md.tmpl`
- Create: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Natural-language learner intent, current directory, and the CLI from Task 6.
- Produces: A tutor workflow that initializes, teaches, records, evaluates, advances, remediates, and resumes without relying on prior chat context.

- [ ] **Step 1: Write failing Skill contract tests**

```python
# tests/test_skill_contract.py
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "learning-agent" / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_skill_routes_to_every_required_reference(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for name in (
            "course-lifecycle.md",
            "teaching-loop.md",
            "mastery-and-evidence.md",
            "safety-and-sources.md",
            "state-engine.md",
        ):
            self.assertIn(f"references/{name}", text)

    def test_skill_forbids_unattributed_solution_work(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, re.compile(r"agent-assisted", re.IGNORECASE))
        self.assertRegex(text, re.compile(r"hint level 4|hint level 5", re.IGNORECASE))

    def test_skill_requires_status_before_resume(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Run `status` before teaching", text)
```

- [ ] **Step 2: Run Skill contract tests and verify failure**

Run: `python3 -m unittest tests.test_skill_contract -v`

Expected: FAIL because the scaffolded Skill does not contain the contract.

- [ ] **Step 3: Write `SKILL.md` as a router and invariant set**

Use this frontmatter and top-level contract:

```markdown
---
name: learning-agent
description: Turn Codex into a persistent interactive tutor for technical skills. Use when the user asks to learn, study, practice, continue a course, inspect learning progress, request a hint, take an assessment, or create a zero-to-hero learning project.
---

# Learning Agent

Teach through evidence-bearing interaction, not tutorial dumping.

## Invariants

- Run `status` before teaching in an existing course.
- Never mark a competency mastered without every rubric-required evidence type.
- Attribute learner, agent-assisted, and collaborative work separately.
- Hint level 4 or hint level 5 makes the attempt assisted.
- Do not edit a learner solution during an active graded attempt unless the learner explicitly ends independent mode.
- Use the state engine for every progress mutation; never hand-edit `progress.json`.
```

Route new course creation and resume to `course-lifecycle.md`; active lessons to
`teaching-loop.md`; scoring and retries to `mastery-and-evidence.md`; any lab,
source, credential, cloud, destructive, or environment concern to
`safety-and-sources.md`; and every state call to `state-engine.md`.

- [ ] **Step 4: Write the lifecycle and teaching references**

`course-lifecycle.md` defines natural-language intent routing, diagnostic stop
conditions, competency graph proposal, learner approval before initialization,
just-in-time lesson materialization, curriculum revision history, `status`
resume behavior, and unsupported-subject reduced mode.

`teaching-loop.md` defines the seven lesson stages from the spec, maximum one
bounded concept before interaction, the five hint levels, independent-attempt
mode, explicit learner requests that end independent mode, remediation, and
session-summary write timing.

Use the lesson template:

```markdown
# {{lesson_title}}

## Outcome
{{observable_outcome}}

## Why it matters
{{practical_relevance}}

## Current interaction
{{single_prompt_or_task}}

## Completion evidence
{{required_evidence_summary}}
```

- [ ] **Step 5: Write mastery, safety, source, and engine references**

`mastery-and-evidence.md` includes the 0–3 rubric, required evidence pairing,
effective-level caps, semantic rationale requirements, supersession, milestone
transfer attempts, changed-scenario retries, and skip/waive semantics.

`safety-and-sources.md` classifies missing tools, network faults, flaky tests,
state faults, and stale sources. It requires official current sources for
version-sensitive behavior, explicit confirmation for cost/destruction/
credentials/production/public exposure, secret redaction, and cleanup
verification.

`state-engine.md` gives the exact CLI forms from Task 6 and this call order:

```text
new course: diagnostic -> curriculum approval -> init -> render -> status
lesson evidence: record -> evaluate -> render -> status
pass: record -> evaluate -> advance -> render -> status
resume: validate -> status
repair: validate -> recover (dry run) -> explain -> recover --apply -> render -> status
```

- [ ] **Step 6: Run Skill contract and official skill validation**

Run:

```bash
python3 -m unittest tests.test_skill_contract -v
python3 /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/learning-agent
```

Expected: both commands PASS.

- [ ] **Step 7: Commit the Tutor Skill**

```bash
git add skills assets tests/test_skill_contract.py
git commit -m "feat: add evidence-based tutor skill"
```

---

### Task 8: Add realistic scenarios and end-to-end course tests

**Files:**
- Create: `tests/fixtures/terraform_initialization.json`
- Create: `tests/test_scenarios.py`
- Create: `tests/test_end_to_end.py`
- Modify: `tests/helpers.py`

**Interfaces:**
- Consumes: Public CLI only; no direct imports in end-to-end tests.
- Produces: Acceptance evidence for diagnostic placement data, independent pass, assisted retry, remediation, transfer, skip, resume, environment failure metadata, and recovery.

- [ ] **Step 1: Add the Terraform fixture**

The fixture defines two milestones, four lessons, and these competencies:

```json
[
  {"id":"tf-config","title":"Write and validate configuration","target_level":2,"required_evidence_types":["practical","explanation"]},
  {"id":"tf-state","title":"Reason about Terraform state","target_level":2,"required_evidence_types":["practical","explanation"]},
  {"id":"tf-modules","title":"Design reusable modules","target_level":2,"required_evidence_types":["practical","explanation"]},
  {"id":"tf-transfer","title":"Adapt a design to a new environment","target_level":3,"required_evidence_types":["practical","transfer"]}
]
```

Use fake local validator summaries and official-source metadata; no test may
contact Terraform Cloud, a cloud provider, or the internet.

- [ ] **Step 2: Write a failing assisted-retry scenario**

```python
# tests/test_scenarios.py
import unittest

from scripts.learning_engine.evidence import effective_level
from scripts.learning_engine.progression import evaluate_lesson
from tests.helpers import load_terraform_fixture


class ScenarioTests(unittest.TestCase):
    def test_assisted_attempt_requires_fresh_independent_retry(self) -> None:
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
```

- [ ] **Step 3: Run the scenario and verify it exposes any remaining gap**

Run: `python3 -m unittest tests.test_scenarios -v`

Expected before fixes: FAIL if evaluation incorrectly mixes assisted evidence
into an independent pass or requires one attempt to contain every evidence
event. Fix only the exposed engine defect, then rerun to PASS.

- [ ] **Step 4: Add the remaining scenario matrix**

Add named tests for:

- passing validator plus level-1 explanation remains remediation;
- diagnostic evidence can mark a declared competency at level 2;
- transfer competency requires level 3 and `transfer` evidence;
- skipped prerequisite leaves its competency at level 0;
- network failure event with outcome `inconclusive` does not lower mastery;
- a superseding event replaces an incorrect semantic assessment;
- new-session `status` returns active context without prior process memory;
- malformed `progress.json` is recovered from valid journal evidence.

- [ ] **Step 5: Write the end-to-end subprocess test**

`tests/test_end_to_end.py` creates a temporary course, then invokes only
`scripts/learning_state.py` to perform:

```text
init -> validate -> status -> record(practical) -> record(explanation)
-> evaluate -> advance -> render -> validate -> status
```

Assert exit code 0 for every command, lesson 1 becomes passed, lesson 2 becomes
active, both dashboard files exist, and a second status subprocess reports the
same active lesson.

- [ ] **Step 6: Run all tests twice to catch state leakage**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -v
```

Expected: both runs PASS with identical test counts and no files created under
the repository except Python cache directories.

- [ ] **Step 7: Commit scenarios and acceptance coverage**

```bash
git add tests
git commit -m "test: cover learning-agent course scenarios"
```

---

### Task 9: Finish documentation, validate, install, and package

**Files:**
- Modify: `README.md`
- Create: `docs/usage.md`
- Modify: `tests/test_plugin_contract.py`
- External generated file: `~/.agents/plugins/marketplace.json`
- Installed Git checkout: `~/plugins/learning-agent`

**Interfaces:**
- Consumes: Complete validated source repository.
- Produces: Committed source, a working personal marketplace entry, an installed plugin checkout, and a distributable source archive built from the verified commit.

- [ ] **Step 1: Write failing documentation contract assertions**

Extend `tests/test_plugin_contract.py`:

```python
    def test_readme_documents_user_and_developer_flows(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "I want to learn Terraform from zero to hero",
            "Continue my current lesson",
            "python3 -m unittest discover -s tests -v",
            "Python 3.11",
            "explicit confirmation",
        ):
            self.assertIn(phrase, text)
```

- [ ] **Step 2: Run the documentation contract and verify failure**

Run: `python3 -m unittest tests.test_plugin_contract -v`

Expected: FAIL until README contains every required workflow and safety phrase.

- [ ] **Step 3: Complete README and usage documentation**

README must include requirements, installation, natural-language examples,
generated course tree, mastery levels, hint attribution, Git guidance, safety,
development tests, validators, and uninstall instructions.

`docs/usage.md` must provide one coherent example from “I want to learn
Terraform from zero to hero” through diagnostic, roadmap approval, one lesson,
an assisted retry, independent pass, progress display, and resume in a new
session. Label shell commands shown inside that narrative as agent-internal or
learner-run so users do not confuse the state CLI with course exercises.

- [ ] **Step 4: Run all local verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/learning-agent
python3 /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
git diff --check
```

Expected: every command PASS.

- [ ] **Step 5: Commit the release-ready source**

```bash
git add README.md docs/usage.md tests/test_plugin_contract.py
git commit -m "docs: complete learning-agent usage guide"
git status --short --branch
```

Expected: branch `main` with no uncommitted changes.

- [ ] **Step 6: Create the personal marketplace entry with the official helper**

Run from the repository root:

```bash
python3 /root/.codex/skills/.system/plugin-creator/scripts/create_basic_plugin.py \
  learning-agent \
  --path .. \
  --with-marketplace \
  --force
```

Then run:

```bash
python3 /root/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py
python3 /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Expected: marketplace name `personal`; plugin validation PASS. Inspect the
repository diff and commit any scaffold-normalized source change before
installation. Do not hand-edit `marketplace.json`.

- [ ] **Step 7: Install the verified Git source at the marketplace path**

If `~/plugins/learning-agent` does not exist:

```bash
git clone "$(pwd)" ~/plugins/learning-agent
```

If it already exists and is the same repository, update it with:

```bash
git -C ~/plugins/learning-agent fetch origin main
git -C ~/plugins/learning-agent merge --ff-only origin/main
```

Stop instead of overwriting if the existing path is not the same repository or
contains uncommitted changes.

- [ ] **Step 8: Perform installed-path smoke validation**

Run:

```bash
python3 /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py ~/plugins/learning-agent
python3 ~/plugins/learning-agent/scripts/learning_state.py --help
python3 -m unittest discover -s ~/plugins/learning-agent/tests -v
```

Expected: plugin validator PASS, CLI help exits 0, all tests PASS.

- [ ] **Step 9: Build the distributable archive from the verified commit**

Record `git rev-parse HEAD`, then create an archive whose top-level directory is
`learning-agent/`:

```bash
git archive --format=zip --prefix=learning-agent/ -o ../learning-agent-source.zip HEAD
```

List the archive and verify it contains `.codex-plugin/plugin.json`,
`skills/learning-agent/SKILL.md`, `scripts/learning_state.py`, the approved
spec, the implementation plan, and tests.

- [ ] **Step 10: Final verification checkpoint**

Run:

```bash
git status --short --branch
git log --oneline --decorate -10
python3 -m unittest discover -s tests -v
python3 /root/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Expected: clean source tree and all verification PASS. Retain the commit SHA,
archive path, personal marketplace path, and installed plugin path for handoff.

---

## Spec coverage self-review

| Specification area | Implemented by |
| --- | --- |
| Hybrid Tutor Skill plus local engine | Tasks 1, 2, 6, 7 |
| Course directory and authoritative state | Tasks 2, 3, 6 |
| Adaptive diagnostic and curriculum | Task 7; fixture evidence in Task 8 |
| Interactive lesson loop and coach-first hints | Task 7 |
| Evidence attribution and 0–3 mastery | Tasks 4, 7, 8 |
| Remediation, retry, milestone transfer, skip/waive | Tasks 5, 7, 8 |
| Session-independent resume | Tasks 6, 7, 8 |
| Source freshness and lab safety | Task 7; docs contract in Task 9 |
| Atomic writes, validation, and recovery | Tasks 2, 5, 6, 8 |
| Natural-language user experience | Tasks 7 and 9 |
| Unit, scenario, installed-path, and end-to-end tests | Tasks 1–9 |
| Personal marketplace installation and source delivery | Task 9 |

The nine tasks form one subsystem: an installable plugin whose Tutor Skill and
state engine are jointly required for a working course. Each task leaves a
reviewable, testable commit, and the final task validates the exact installed
source before packaging.
