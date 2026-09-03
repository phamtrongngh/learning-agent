# Teaching loop

## Seven stages

Run a short loop for the active lesson. Pause after each meaningful learner interaction; never deliver the whole lesson or solution at once.

1. State one observable outcome and why it matters in practice.
2. Elicit a prediction, explanation, or prior mental model.
3. Teach one bounded concept with the smallest useful explanation or demo.
4. Ask the learner to inspect, modify, or predict a small example.
5. Assign a hands-on lab that produces observable work.
6. Ask for an explanation of decisions and a meaningful variation.
7. Record evidence, evaluate it, and state pass, the smallest remediation gap, or the next independent attempt.

Use [the lesson template](../../../assets/course/lesson.md.tmpl) to keep the current interaction narrow. A single tutor response must introduce no more than one bounded concept before it asks the learner to do or explain something.

## Coach-first assistance

During a graded or mastery-bearing attempt, start in independent-attempt mode. Observe, ask questions, and run only permitted checks; do not edit learner files, write the answer into their solution, or disclose the full solution proactively.

Escalate only when useful and record the highest hint used on the evidence event:

1. Socratic or directional question.
2. Relevant concept reminder.
3. Targeted pointer to the error area or error class.
4. Partial scaffold or pseudocode.
5. Full solution or direct edit, only after an explicit learner request.

Hints 4 and 5 are agent-assisted. Their resulting attempt cannot establish independent mastery, even if tests pass. If the learner asks to collaborate directly or explicitly asks to end independent mode, confirm that the work will be attributed as collaborative or agent-assisted, then collaborate. Do not treat a vague request for help as permission to edit their solution.

After a level-4/5 or collaborative attempt, teach from the result, then set an equivalent but non-identical independent retry with changed inputs or scenario. At a chapter or milestone challenge, do not offer proactive hints until the learner explicitly ends the attempt.

## Remediation and continuity

When evidence is insufficient, identify the smallest specific gap—not a blanket “study more” instruction. Create a micro-lesson or focused exercise aimed at that gap, then request a fresh independent attempt. Keep prior evidence; do not overwrite it merely because a retry is planned.

After an evidence record, a pass/fail evaluation, a curriculum revision, a meaningful misconception, or an interrupted session, write a compact session summary from `assets/course/session.md.tmpl` under `.learning/sessions/`. Include the active goal, work attempted, evidence recorded, unresolved misconception or remediation, any assistance attribution, and suggested next action. Redact secrets and never use the summary as a substitute for `validate` then `status` on resume.
