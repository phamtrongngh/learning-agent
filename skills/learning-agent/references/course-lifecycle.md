# Course lifecycle

## Route natural-language intent

Interpret the learner's request and the current directory together. Do not require slash commands or expose the state CLI as a learner task.

| Learner intent | Tutor action |
| --- | --- |
| Learn, study, zero-to-hero, or build a learning project | Start the new-course flow. |
| Continue, resume, current lesson, or “where was I?” | Use the existing-course resume flow. |
| Progress, roadmap, or what is next | Read validated status and explain the generated view. |
| Hint, assessment, retry, or why did not pass | Resume status first, then route to the teaching or mastery reference. |
| A non-technical subject | Explain V0 is technical-skills-first and offer reduced mode without claiming executable mastery validation. |

If no course directory is supplied, ask only for the intended directory when it materially affects creation. If `.learning/` is present, it is the course record; do not reconstruct state from chat history, README prose, or a learner's memory.

## New course flow

1. Ask only for outcome, relevant experience, available time or pace, and environment constraints.
2. Run a small adaptive diagnostic: a few targeted questions plus a mini-task when practical. Stop as soon as there is enough evidence to place the learner; do not administer a long entrance exam.
3. Record accepted diagnostic evidence only when it meets declared evidence requirements. Self-reported experience can choose questions but cannot itself establish mastery.
4. Propose a visible competency graph: milestones, stable competency IDs, prerequisites, target levels, required evidence types, expected projects, and any diagnostic placement. Preserve every required outcome.
5. Obtain learner approval of that curriculum before initialization. Do not initialize or silently remove outcomes before approval.
6. Initialize the approved course through the state engine, materialize only the roadmap, first lesson, and immediately useful scaffolding, then render and inspect status.

Use `assets/course/lesson.md.tmpl` for each just-in-time lesson. Create later lesson detail only when it becomes active, so changing sources and learner evidence can still shape it.

## Existing course and resume flow

For every existing course, run `validate` and then `status` before teaching. Use the status response—not prior-session assumptions—to identify the active lesson, required competencies, recent evidence, remediation gaps, source freshness warnings, and allowed next action. Render generated views when state changed or the learner asks to inspect them.

If state is malformed or inconsistent, stop teaching and follow the repair procedure in `state-engine.md`. Do not edit `.learning/progress.json` manually.

## Adaptation and course-contract changes

Vary lesson depth, examples, optional practice, remediation, pace, challenges, and lab domain without changing the approved competency graph. V0 does not mutate lesson order, prerequisites, target competencies, or required outcomes after `init`.

If the learner needs a substantive contract change, explain it and record the proposal in the current session summary. After approval, initialize a new course directory with the revised curriculum; do not silently transfer mastery from the old course. Use the session template for a compact summary, never a full transcript.

## Unsupported-subject reduced mode

For a subject without credible executable practice or validators, say clearly that the technical-skill state model cannot certify executable mastery. Offer a reduced, evidence-aware coaching mode: observable goals, learner explanations, source-backed practice, and transparent limitations. Do not fabricate lab results, rubric evidence, or state-engine mastery claims.
