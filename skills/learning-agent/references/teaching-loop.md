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

## Contextual visuals

Create or offer a visual when the learner explicitly asks to see, visualize, diagram, simulate, compare, or explore a concept, or when it materially clarifies dependencies or topology, causal or execution flow, state changing over time, spatial relationships or motion, or a data pattern that is hard to inspect from raw values. Do not create one merely because the subject can be illustrated, to decorate a response, or to repeat a short explanation.

Stop at the first sufficient medium:

1. Text, code, a Markdown table, or ASCII.
2. Mermaid for a static structure fully explained by labeled nodes and edges.
3. An interactive web visual for adjustable, dynamic, spatial, simulation, or step-through behavior.
4. A generated image for a physical, spatial, or metaphorical illustration that does not require precise technical labels.

Include interaction only when changing a control teaches something. After showing the visual, ask the learner to predict, manipulate, inspect, or explain; assess only the learner's response or work. A visual is a teaching aid, never mastery evidence.

During a graded attempt, classify visual assistance by the information disclosed, not its format. A neutral rendering of information already in the prompt does not by itself make the attempt assisted. Directing attention to the relevant error area or class is hint level 3; showing a partial scaffold, pseudocode, or solution structure is hint level 4; showing the full solution or directly editing learner work is hint level 5. Existing assistance caps and independent-retry rules still apply. Give no proactive visual hints during milestone or transfer attempts.

Visuals are ephemeral by default. Offer to save one only when it has lasting review value, and persist it only after explicit learner approval. Embed approved Mermaid in the active lesson Markdown or store approved standalone HTML or image files under `visuals/<lesson-id>/` and link them from the lesson. Saved visuals stay outside `.learning/` and are optional for course validation and continuity.

Every visual needs a concise text equivalent. Interactive visuals need semantic, keyboard-accessible controls, visible labels, and non-color cues; essential information and the learner's next action must remain available without hover, motion, or the visual. Motion must honor reduced-motion preferences when the host supports animation.

If a visual capability is missing, fails, times out, renders incorrectly, or raises an accuracy concern, give a text or ASCII fallback and continue the interaction. A visual failure does not lower mastery or create negative learner evidence, and a failed visual is not saved. Mention the unavailable visual only when that helps the learner act.

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

After an evidence record, a pass/fail evaluation, a meaningful misconception, or an interrupted session, write a compact session summary from `assets/course/session.md.tmpl` under `.learning/sessions/`. Name it with the UTC timestamp `YYYYMMDDTHHMMSSZ.md`. Include the active goal, work attempted, evidence recorded, unresolved misconception or remediation, any assistance attribution, any proposed course-contract change, and suggested next action. Redact secrets and never use the summary as a substitute for `validate` then `status` on resume.
