# State engine

The state engine is tutor-internal. It returns JSON envelopes and nonzero exits; translate outcomes into learner-facing guidance. `.learning/` is authoritative. Never hand-edit any `.learning/` file, append arbitrary journal text, or mutate derived state outside this CLI.

## Exact command forms

Run these from the plugin repository, replacing placeholders with concrete paths:

```bash
python3 scripts/learning_state.py --root <course-root> init --input <approved-initialization.json>
python3 scripts/learning_state.py --root <course-root> status
python3 scripts/learning_state.py --root <course-root> record --input <evidence.json>
python3 scripts/learning_state.py --root <course-root> sources --input <source.json>
python3 scripts/learning_state.py --root <course-root> evaluate --lesson <active-lesson-id>
python3 scripts/learning_state.py --root <course-root> advance
python3 scripts/learning_state.py --root <course-root> skip --lesson <active-lesson-id> --disposition skipped
python3 scripts/learning_state.py --root <course-root> skip --lesson <active-lesson-id> --disposition waived
python3 scripts/learning_state.py --root <course-root> render
python3 scripts/learning_state.py --root <course-root> validate
python3 scripts/learning_state.py --root <course-root> recover
python3 scripts/learning_state.py --root <course-root> recover --apply
```

`init` and `record` consume JSON objects. For evidence, provide the valid event fields: `event_id`, `attempt_id`, `timestamp`, `lesson_id`, `context`, `competency_ids`, `type`, `outcome`, `author`, `hint_level`, `rubric_level`, `rationale`, optional supersession reference, and optional artifact or command summary. The engine, not the tutor, validates shape and transition eligibility.

`sources --input` is an additive source-state command for an existing initialized course. Its input is exactly one complete source-record object with `id`, `publisher`, `version`, `verified_at`, and `freshness` (`verified`, `stale`, or `unverified`); include `url` when available. It atomically creates the record or replaces the record with the same `id`, preserving every other stored source. After checking an official source, prepare the complete updated record, run `sources --input`, require `ok: true`, then run `validate` and `status`. Use the same command to mark a previously verified record stale or unverified; never edit `.learning/sources.json` directly.

## Required call order

```text
new course: diagnostic -> curriculum approval -> init -> render -> status
lesson evidence: record -> evaluate -> render -> status
pass: record -> evaluate -> advance -> render -> status
resume: validate -> status
repair: validate -> recover (dry run) -> explain -> recover --apply -> render -> status
```

On a failed command, read the JSON error envelope, stop the attempted transition, and explain the blocker. Never claim a mutation succeeded without an `ok: true` result. `recover` without `--apply` is a dry run; compare and explain its candidate state before applying it. Recovery must preserve journal evidence. Use `render` after successful state changes so learner-facing views reflect authoritative state.
