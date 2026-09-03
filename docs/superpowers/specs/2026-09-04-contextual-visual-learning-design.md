# Contextual Visual Learning Design

**Date:** 2026-09-04  
**Status:** Approved for implementation planning  
**Plugin:** `learning-agent`

## Purpose

Add optional, context-sensitive visuals to Learning Agent so learners can inspect difficult relationships, flows, state changes, and spatial concepts without turning every lesson into a presentation or adding a web application to the plugin.

The feature extends the existing teaching loop. It does not add a renderer, service, dashboard, dependency, or authoritative learning state.

## Goals

- Use a visual when it materially improves one bounded concept or when the learner asks for one.
- Prefer interactive visuals when manipulating a parameter or stepping through a process improves understanding.
- Make every visual part of an evidence-bearing interaction by asking the learner to predict, manipulate, inspect, or explain something.
- Preserve the existing rules for independent attempts, hint attribution, evidence, source freshness, and course continuity.
- Continue the lesson with a text or ASCII fallback when a visual capability is unavailable or fails.
- Persist only visuals that the learner explicitly agrees are useful for later review.

## Non-goals

- A hosted LMS, browser UI, visual gallery, dashboard, or asset-management subsystem.
- A bundled SVG, chart, image, or HTML renderer.
- Pre-generating visuals for every lesson or curriculum item.
- Adding visual metadata to `.learning/` or treating a visual as mastery evidence.
- Installing visual tools or making them prerequisites for a course.
- Testing Codex-owned rendering behavior inside this plugin.

## Architecture

Learning Agent remains the only orchestration layer. At stage 3 of the teaching loop, where the tutor teaches one bounded concept with the smallest useful explanation or demo, it decides whether a visual materially improves the interaction.

The plugin uses visual capabilities already available in the Codex host:

- Markdown text, code, tables, or ASCII remain the default when they are sufficient.
- Mermaid is used for static structures whose meaning is fully expressed by labeled nodes and edges.
- The host's interactive visualization capability is used for dynamics, spatial motion, adjustable inputs, simulations, and step-through explanations.
- The host's image-generation capability is used sparingly for spatial concepts, physical objects, or explanatory metaphors. It is not used for precise technical diagrams containing factual labels or code.

These capabilities are optional. Learning Agent checks availability through the normal skill/tool context exposed by Codex. It does not attempt installation. Missing, failed, or unsuitable visual capability falls back to the smallest text, code, Mermaid, or ASCII explanation that works.

No Python state-engine code or structured state schema changes.

## Visual Trigger Policy

Learning Agent creates or offers a visual when either condition is true:

1. The learner explicitly asks to see, visualize, diagram, simulate, compare, or explore the concept.
2. The tutor determines that a visual materially clarifies at least one of:
   - dependencies or topology;
   - causal or execution flow;
   - state changing over time;
   - spatial relationships or motion;
   - a data pattern that is hard to inspect from raw values.

It does not create a visual merely because the subject can be illustrated, to decorate a response, or to repeat information already clear in a short explanation.

## Media Selection Ladder

Stop at the first medium that fully supports the learning interaction:

1. Text, code, a Markdown table, or ASCII.
2. Mermaid for a static labeled graph or sequence.
3. Interactive web visual for adjustable, dynamic, spatial, or step-through behavior.
4. Generated image for a physical, spatial, or metaphorical illustration that does not require exact technical labels.

An interactive control is included only when changing it teaches something. A static visual is preferred when interaction would not change the learner's reasoning task.

## Teaching Flow

The visual flow is:

```text
identify a bounded concept
-> decide whether a visual materially helps
-> choose the first sufficient medium
-> show the visual or fallback
-> ask the learner to predict, manipulate, inspect, or explain
-> assess only the learner's response or work
```

The tutor still pauses after one bounded concept. A visual does not authorize a longer lesson dump or a complete solution.

## Assessment and Hint Attribution

A visual is a teaching aid, not evidence. Only the learner's observable work or explanation can satisfy a rubric evidence requirement.

During a graded attempt, assistance is classified by the information disclosed, not by the visual format:

- A neutral rendering of information already present in the prompt does not by itself make the attempt assisted.
- Directing attention to the relevant error area or error class is hint level 3.
- Showing a partial scaffold, pseudocode, or solution structure is hint level 4.
- Showing the full solution or directly editing the learner's work is hint level 5.

Existing caps continue to apply: hint levels 4 and 5, agent authorship, or collaborative authorship cap effective credit at assisted level 1. After material visual assistance, the learner receives a fresh, non-identical independent retry.

At a milestone or transfer challenge, Learning Agent does not proactively generate a visual hint. It may neutrally render information already supplied by the challenge, or provide assistance only after the learner explicitly ends the independent attempt; the resulting attribution follows the rules above.

## Persistence

Visuals are ephemeral by default and remain in the conversation.

When a visual would be useful for later review, Learning Agent offers to save it. It persists the visual only after explicit learner approval:

- Mermaid may be embedded in the active lesson Markdown.
- Exportable standalone HTML or image files are stored under `visuals/<lesson-id>/` in the course directory and linked from the active lesson.
- The `visuals/` directory is created only when the first approved visual is saved.

Saved visuals are learner-facing course artifacts. They are not written under `.learning/`, referenced by authoritative progress state, or required to resume or validate the course.

## Accuracy, Sources, and Safety

- A technical visual must agree with the source material, code, commands, or observed system state used in the lesson.
- Version-sensitive claims shown visually follow the existing source policy. The tutor verifies and records the current primary source through the state engine before presenting the claim as current.
- If verification is unavailable, the visual is limited to stable foundational material and affected claims are marked stale or unverified.
- Generated imagery is not used to invent interfaces, command output, provider behavior, resource topology, or precise implementation details.
- Visual generation must not expose secrets or reproduce raw sensitive output.
- A visual that could encourage a costly, destructive, privileged, shared, production, or publicly exposed action does not bypass the existing lab safety gate.

## Accessibility

- Every visual includes a concise text equivalent or accessible description conveying the learning-relevant information.
- Interactive visuals use semantic controls, keyboard navigation, visible labels, and non-color cues.
- Essential information and the learner's next action remain available without hover, animation, or the visual itself.
- Motion honors reduced-motion preferences when the host capability supports animation.

## Failure Handling

Visual failure is a presentation fault, not a learner or environment failure. On missing capability, generation failure, timeout, invalid rendering, or an accuracy concern, Learning Agent:

1. does not lower mastery or record negative learner evidence;
2. gives the smallest useful text, code, Mermaid, or ASCII fallback;
3. continues the current teaching interaction;
4. mentions the unavailable visual only when that information helps the learner act.

A failed visual is not written to the course directory.

## Plugin Changes

- `skills/learning-agent/SKILL.md`: route visual requests and visual-worthy explanations through the teaching loop; preserve safety-first routing for sourced or version-sensitive visuals.
- `skills/learning-agent/references/teaching-loop.md`: add the trigger policy, media ladder, interaction requirement, assessment attribution, persistence rule, accessibility baseline, and fallback behavior.
- `skills/learning-agent/references/safety-and-sources.md`: apply source, secret, and safety policies to visual content.
- `.codex-plugin/plugin.json`: advertise contextual visual explanations as a capability without claiming a bundled renderer.
- `README.md`: document optional contextual visuals, fallback behavior, persistence, and the optional `visuals/` course directory.
- `tests/test_skill_contract.py`: assert the visual teaching contract and its mastery safeguards.
- `tests/test_plugin_contract.py`: assert the public capability and README contract.

The implementation does not modify `scripts/`, `assets/course/`, state-engine tests, or structured course schemas.

## Test Strategy

Contract tests verify that the skill instructions require:

- learner-requested and tutor-initiated contextual triggers;
- the ordered media-selection ladder;
- a learner prediction, manipulation, inspection, or explanation after a visual;
- text or ASCII fallback without a mastery penalty;
- information-based hint attribution and no proactive visual hints during milestone attempts;
- explicit approval before persistence outside `.learning/`;
- text equivalents and keyboard-accessible interaction;
- source verification and secret protection for visual content.

Plugin contract tests verify that the manifest and README describe optional contextual visuals without describing a bundled dashboard or required visual dependency.

No browser rendering, image-quality, screenshot, or snapshot tests are added. Those belong to the Codex host capabilities that produce the visual.

## Acceptance Criteria

1. A learner can explicitly request a visual during a lesson, and the skill instructions route the request through the media-selection ladder.
2. The tutor may initiate a visual only for a declared visual-worthy relationship and must attach a learner interaction.
3. Missing or failed visual capability cannot block the lesson or reduce learner mastery.
4. Visual assistance during graded work follows the existing hint and authorship caps.
5. Milestone and transfer attempts receive no proactive visual hints.
6. Persisted visuals require explicit learner approval, live outside `.learning/`, and are optional for course continuity.
7. Visuals meet the source, safety, secret-handling, and accessibility requirements in this design.
8. The full existing test suite, plugin validator, skill validator, and `git diff --check` pass.
