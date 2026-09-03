# Learning Agent

Learning Agent turns Codex into a persistent, evidence-based tutor for terminal-practical technical skills. It teaches one bounded step at a time, keeps course state in the course directory, and advances only when the declared evidence supports mastery.

## Requirements

- Codex with terminal access.
- Python 3.10 or later; the bundled state engine uses only the standard library.
- A writable local directory for each course and its exercises.
- Git is recommended so a learner can version their notes, projects, and generated course views.

## Installation

Install the `learning-agent` plugin from a Codex marketplace that provides it. In the default personal marketplace, use the Codex plugin UI or run:

```bash
codex plugin add learning-agent@personal
```

Start a new Codex thread after installation so the skill is available. The learner talks to the agent in natural language; the bundled state CLI is an agent-internal tool, not a course exercise.

## Start, continue, and inspect a course

For example, tell Codex:

- “I want to learn Terraform from zero to hero.”
- “Continue my current lesson.”
- “Show my progress and the next available action.”
- “Give me a hint, but keep this attempt independent.”

For a new course, Learning Agent asks about the desired outcome, relevant experience, pace, and environment; runs a short adaptive diagnostic; proposes milestones, competencies, prerequisites, targets, and evidence; then waits for your approval. It does not initialize or remove agreed outcomes without explicit confirmation of the proposed curriculum.

For an existing course it validates durable state and reads status before teaching, rather than relying on prior chat context. See [the worked usage example](docs/usage.md).

## Course files

Each course is self-contained. Generated learner-facing files are convenient views; `.learning/` is authoritative. Structured state is changed only through the state engine; session summaries are Markdown notes written from the bundled template.

```text
terraform-zero-to-hero/
├── README.md
├── ROADMAP.md
├── lessons/
├── projects/
├── notes/
└── .learning/
    ├── course.json
    ├── curriculum.json
    ├── progress.json
    ├── evidence.jsonl
    ├── sources.json
    └── sessions/
```

Only the roadmap, first lesson, and immediately useful scaffolding are materialized at creation. Later lessons are created when they become active, which keeps content current and responsive to the learner's evidence.

## Mastery and assistance

Evidence has a written rationale and is attributed honestly:

| Level | Meaning |
| --- | --- |
| 0 — unobserved | No accepted relevant evidence. |
| 1 — assisted | Material guidance or agent/collaborative authorship was required. |
| 2 — independent | The learner performed and explained the target without material help. |
| 3 — transfer | The learner independently applied it in a meaningfully new situation. |

A competency is mastered only when every rubric-required evidence type is accepted at its target level. A practical result normally needs both observable work and an explanation; a passing check alone is not enough. Agent and collaborative work is recorded separately and is capped at assisted credit. Hint levels 4 and 5 are also assisted, even when the resulting work passes. After an assisted attempt, Learning Agent assigns a fresh, non-identical independent retry rather than relabeling the assisted work.

## Git and safety

Keep the course directory in a Git repository when practical, and commit learner artifacts, notes, and useful generated views at meaningful checkpoints. Do not commit secrets, credentials, tokens, or raw sensitive command output. The append-only evidence journal preserves assessment history; do not hand-edit structured `.learning/` state or rewrite evidence to make progress appear complete. The sole direct-write exception is a redacted Markdown session summary under `.learning/sessions/`.

Labs prefer local, sandboxed, emulated, or containerized environments. Before any action that could incur cost, alter or delete data or infrastructure, use real credentials, affect shared or production systems, or expose a service publicly, Learning Agent explains the scope, impact, cleanup path, and a safer alternative, then obtains explicit confirmation for that specific action. It does not treat network, environment, or flaky-test failures as learner failure. Version-sensitive guidance is checked against current primary sources and marked stale or unverified when it cannot be confirmed.

## Development and validation

Run these commands from this repository:

```bash
codex_system_skills="${CODEX_HOME:-$HOME/.codex}/skills/.system"
python3 -m unittest tests.test_plugin_contract -v
python3 -m unittest discover -s tests -v
python3 "$codex_system_skills/skill-creator/scripts/quick_validate.py" skills/learning-agent
python3 "$codex_system_skills/plugin-creator/scripts/validate_plugin.py" .
git diff --check
```

The first command checks the public plugin and documentation contract; the full suite covers the state engine, skill contract, realistic scenarios, and the public CLI.

## Uninstall

Remove the plugin through the Codex plugin UI or run:

```bash
codex plugin remove learning-agent
```

Uninstalling the plugin does not delete course directories. Archive or remove a course directory separately only when you no longer need its learner artifacts and `.learning/` history.
