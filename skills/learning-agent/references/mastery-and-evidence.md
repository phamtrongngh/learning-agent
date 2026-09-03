# Mastery and evidence

## Transparent rubric

Score evidence with a written, concrete semantic rationale. The levels are:

| Level | Meaning |
| --- | --- |
| 0 — unobserved | No accepted relevant evidence. |
| 1 — assisted | Success required material guidance or agent-authored/collaborative work. |
| 2 — independent | Learner performs and explains the target without material help. |
| 3 — transfer | Learner independently applies it in a meaningfully new situation. |

For each competency, pair every declared required evidence type with accepted evidence for that competency. A practical competency normally needs both practical work and an explanation: a passing test does not replace understanding, and a verbal answer does not replace performance. A lesson passes only when every required competency meets its target—normally at least independent level 2—and every required type is present.

## Attribution, caps, and rationale

Use `author: learner`, `author: agent`, or `author: collaborative` honestly. Agent or collaborative authorship caps effective credit at level 1. A highest `hint_level` of 4 or 5 also caps effective credit at level 1, regardless of a higher reported rubric level. An inconclusive environment event and a disposition event provide no mastery credit.

The rationale must state what the learner did or explained, how it meets or misses the criterion, what assistance was used, and the smallest next gap. Do not accept assertions such as “looks good” or “tests pass” as a semantic rationale.

## Reassessment, retry, and transfer

Preserve the append-only evidence journal. When a later semantic assessment corrects a previous one, create a new event that identifies `supersedes_event_id`; evaluate the unsuperseded evidence rather than rewriting history.

After an assisted, agent-authored, or collaborative result, assign a fresh independent retry with a changed scenario or inputs. Do not combine the assisted work into an independent pass. For a milestone, use an independent transfer attempt with no proactive hints; competencies that require transfer need level 3 plus `transfer` evidence in the declared pairing.

## Progression and dispositions

On an incomplete evaluation, name the missing evidence type or below-target competency, create targeted remediation, and keep the learner at the active lesson. On a pass, use the state-engine pass call order to advance only after evaluation has persisted the valid result.

A learner may skip or waive an active lesson by explicit choice. Record the requested disposition exactly as `skipped` or `waived`; it leaves affected competencies unmet and prerequisite gaps visible. Never convert skip/waive into mastery, and never use it to satisfy a milestone or transfer requirement.
