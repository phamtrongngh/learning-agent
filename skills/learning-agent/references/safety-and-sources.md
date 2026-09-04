# Safety and sources

## Source policy

For version-sensitive tools, commands, pricing, limits, APIs, provider behavior, or security guidance, consult the current primary or official publisher source before finalizing the curriculum or teaching the claim. Record the source identifier or URL, publisher, applicable version, verification date, and freshness through the approved state workflow; do not hand-edit `.learning/sources.json`. For an existing course, use `sources --input <source.json>` as documented in `state-engine.md` to atomically create or refresh one source record, then run `validate` and `status` before teaching the claim.

If current verification is unavailable, continue only with stable foundational material. Mark affected claims unverified or stale; do not present recalled commands, current provider behavior, pricing, or limits as confirmed facts.

## Visual accuracy and safety

A technical visual must agree with the source material, code, commands, or observed system state used in the lesson. Before presenting a version-sensitive visual as current, verify its claims against a current primary or official publisher source and record that source through the approved state workflow. If verification is unavailable, limit the visual to stable foundations and mark affected claims stale or unverified.

Generated imagery must not invent interfaces, command output, provider behavior, resource topology, or precise implementation details. Visual content must not expose secrets or reproduce raw sensitive output. Creating or displaying a visual does not bypass the lab safety gate for costly, destructive, privileged, shared, production, or publicly exposed actions.

## Lab safety gate

Prefer local, sandboxed, emulated, or containerized labs. Before any operation that could create cost, delete or alter data/resources, use real credentials or privileged access, change shared or production infrastructure, or expose a service publicly, explain the operation, scope, likely impact, cost/cleanup path, and safer local alternative. Obtain explicit learner confirmation for that specific operation before proceeding.

Never place secrets in source files, evidence, command output summaries, session summaries, Git, or chat. Redact tokens, passwords, keys, and sensitive identifiers. Cloud or external labs must include cleanup and then verify the cleanup outcome; report any remaining resources plainly.

## Fault classification and response

| Condition | Tutor response |
| --- | --- |
| Missing tool | Make installation/setup an explicit prerequisite and verify it before the lab. |
| Network or environment fault | Record an `environment` event with `outcome: inconclusive`; isolate the fault and do not lower mastery. |
| Flaky or ambiguous test | Do not treat its output as decisive evidence; record uncertainty and seek a reproducible check or other evidence. |
| State fault | Stop progression, validate state, then use the recovery flow only when safe. |
| Stale or unavailable source | Mark affected version-sensitive material stale/unverified and avoid claiming it is current. |

Do not turn an infrastructure failure into learner failure. Before retrying an external operation, reassess the safety gate and confirmation if the scope changed.
