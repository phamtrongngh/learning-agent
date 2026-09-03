# Learning Agent walkthrough

This walkthrough uses a local `terraform-zero-to-hero/` course directory. The learner uses natural-language requests and course exercises; the state engine commands shown below are **agent-internal**, run by Learning Agent to keep durable state valid.

## 1. Start with a goal and diagnostic

The learner says: “I want to learn Terraform from zero to hero.” Learning Agent asks only for the intended outcome, current experience, available pace, and environment constraints. It then gives a small diagnostic, such as asking the learner to predict the result of a variable and state resource configuration, plus a safe mini-task when practical. Self-reported experience guides the questions but does not itself establish mastery.

Learning Agent proposes a visible roadmap with milestones, stable competency IDs, prerequisites, evidence requirements, target levels, and a first lesson. The learner reviews it and says that the roadmap is approved. That explicit approval is required before initialization.

**Agent-internal command — not a learner exercise:**

```bash
python3 scripts/learning_state.py --root terraform-zero-to-hero init --input approved-initialization.json
python3 scripts/learning_state.py --root terraform-zero-to-hero render
python3 scripts/learning_state.py --root terraform-zero-to-hero status
```

The agent uses the resulting status to introduce only the active lesson. The learner works in their own Terraform files and can use their ordinary shell, editor, formatter, or local validator as appropriate; those are **learner-run course exercises**, not state-engine commands.

## 2. Complete one lesson, then retry independently

For the active lesson, Learning Agent states an observable outcome, asks the learner for a prediction, explains one bounded concept, then asks for a small hands-on change and an explanation of the learner's choices. Evidence records both the practical work and the explanation when the rubric requires both.

Suppose the learner gets stuck and asks for a partial scaffold. Learning Agent identifies the highest hint as level 4, gives only the requested assistance, and records that attempt as assisted. It does not claim independent mastery from the assisted result, even if a local check succeeds. The agent evaluates the evidence and names the smallest gap.

**Agent-internal commands — not learner exercises:**

```bash
python3 scripts/learning_state.py --root terraform-zero-to-hero record --input assisted-evidence.json
python3 scripts/learning_state.py --root terraform-zero-to-hero evaluate --lesson terraform-variables
python3 scripts/learning_state.py --root terraform-zero-to-hero render
python3 scripts/learning_state.py --root terraform-zero-to-hero status
```

Learning Agent then creates a similar but non-identical independent retry. The learner performs the work and explains it without material help. After accepted independent evidence satisfies every required type and target level, the agent evaluates and advances the course.

**Agent-internal commands — not learner exercises:**

```bash
python3 scripts/learning_state.py --root terraform-zero-to-hero record --input independent-evidence.json
python3 scripts/learning_state.py --root terraform-zero-to-hero evaluate --lesson terraform-variables
python3 scripts/learning_state.py --root terraform-zero-to-hero advance
python3 scripts/learning_state.py --root terraform-zero-to-hero render
python3 scripts/learning_state.py --root terraform-zero-to-hero status
```

The learner can now ask, “Show my progress.” Learning Agent translates the validated status into a short explanation of the active lesson, completed evidence, remaining gaps, and the next allowed action.

## 3. Resume in a new session

In a later Codex thread, the learner opens the same course directory and says: “Continue my current lesson.” Learning Agent does not rely on the earlier conversation. It validates the course, reads the recorded status, checks any relevant source-freshness warnings, and resumes at the actual active lesson.

**Agent-internal commands — not learner exercises:**

```bash
python3 scripts/learning_state.py --root terraform-zero-to-hero validate
python3 scripts/learning_state.py --root terraform-zero-to-hero status
```

If validation detects malformed state, Learning Agent stops progression and uses the recovery workflow rather than editing `.learning/progress.json` manually. Before a lab could create cost, use credentials, modify shared infrastructure, or expose a service, it explains the impact and asks for explicit confirmation.
