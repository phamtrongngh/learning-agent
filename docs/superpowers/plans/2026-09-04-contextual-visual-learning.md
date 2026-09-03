# Contextual Visual Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional contextual-visual teaching policy to Learning Agent without adding a renderer, dependency, service, or state-engine field.

**Architecture:** Extend the existing Markdown skill contract at the bounded-concept stage of the teaching loop. Use host-provided Mermaid, interactive visualization, and image-generation capabilities when available, with text/code/ASCII fallback; expose the capability through the manifest and README while keeping `.learning/` unchanged.

**Tech Stack:** Markdown skill instructions, JSON plugin manifest, Python 3.10+ standard-library `unittest`

**Spec:** `docs/superpowers/specs/2026-09-04-contextual-visual-learning-design.md`

## Global Constraints

- Do not add a renderer, service, dashboard, dependency, or authoritative learning state.
- Do not modify `scripts/`, `assets/course/`, state-engine tests, or structured course schemas.
- Stop at the first sufficient medium: text/code/table/ASCII, Mermaid, interactive web visual, then generated image.
- Visual capability is optional; missing or failed capability falls back without blocking the lesson or lowering mastery.
- Every visual must lead to learner prediction, manipulation, inspection, or explanation.
- Classify graded visual assistance by information disclosed and preserve existing hint-level and authorship caps.
- Do not proactively provide visual hints during milestone or transfer attempts.
- Persist a visual only after explicit learner approval, outside `.learning/`.
- Require source accuracy, secret protection, a text equivalent, and keyboard accessibility.

---

## File Structure

- `skills/learning-agent/SKILL.md`: routes visual learning requests to the teaching loop and retains safety-first routing.
- `skills/learning-agent/references/teaching-loop.md`: owns visual triggers, media selection, learner interaction, assessment attribution, persistence, accessibility, and fallback behavior.
- `skills/learning-agent/references/safety-and-sources.md`: applies source, secret, and lab-safety rules to visual content.
- `tests/test_skill_contract.py`: locks the internal visual teaching contract.
- `.codex-plugin/plugin.json`: advertises the optional learner-facing capability.
- `README.md`: explains contextual visuals, fallback, persistence, and the optional course folder.
- `tests/test_plugin_contract.py`: locks the public manifest and documentation contract.

No new file is needed outside this plan. A course-level `visuals/` directory is created at runtime only after a learner approves saving a visual; it is not added to this plugin repository.

### Task 1: Contextual Visual Teaching Contract

**Files:**
- Modify: `tests/test_skill_contract.py`
- Modify: `skills/learning-agent/SKILL.md`
- Modify: `skills/learning-agent/references/teaching-loop.md`
- Modify: `skills/learning-agent/references/safety-and-sources.md`

**Interfaces:**
- Consumes: the existing teaching-loop stages, hint levels 1-5, mastery caps, source workflow, and lab safety gate.
- Produces: a prose contract named “Contextual visuals” that Task 2 documents publicly; it adds no Python or JSON state interface.

- [ ] **Step 1: Add failing visual contract tests**

Append these methods to `SkillContractTests` in `tests/test_skill_contract.py`:

```python
    def test_visual_requests_route_to_the_teaching_loop(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        visual_route = next(
            line for line in text.splitlines()
            if "visual" in line.lower() and "references/teaching-loop.md" in line
        )
        self.assertRegex(visual_route, re.compile(r"request|explanation", re.IGNORECASE))

    def test_contextual_visuals_use_the_ordered_media_ladder_and_interaction(self) -> None:
        text = (
            ROOT / "skills" / "learning-agent" / "references" / "teaching-loop.md"
        ).read_text(encoding="utf-8")
        lowered = text.lower()
        for phrase in (
            "learner explicitly asks",
            "dependencies or topology",
            "predict, manipulate, inspect, or explain",
        ):
            self.assertIn(phrase, lowered)
        media = (
            "text, code, a markdown table, or ascii",
            "mermaid",
            "interactive web visual",
            "generated image",
        )
        positions = [lowered.index(item) for item in media]
        self.assertEqual(positions, sorted(positions))

    def test_visuals_preserve_mastery_persistence_and_accessibility_rules(self) -> None:
        text = (
            ROOT / "skills" / "learning-agent" / "references" / "teaching-loop.md"
        ).read_text(encoding="utf-8").lower()
        for phrase in (
            "information disclosed",
            "hint level 3",
            "hint level 4",
            "hint level 5",
            "no proactive visual hints",
            "explicit learner approval",
            "`visuals/<lesson-id>/`",
            "outside `.learning/`",
            "text equivalent",
            "keyboard",
            "reduced-motion",
            "does not lower mastery",
            "text or ascii fallback",
        ):
            self.assertIn(phrase, text)

    def test_visual_content_obeys_source_and_safety_policy(self) -> None:
        text = (
            ROOT / "skills" / "learning-agent" / "references" / "safety-and-sources.md"
        ).read_text(encoding="utf-8").lower()
        for phrase in (
            "version-sensitive visual",
            "primary or official publisher source",
            "must not expose secrets",
            "does not bypass the lab safety gate",
        ):
            self.assertIn(phrase, text)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_skill_contract -v
```

Expected: `test_visual_requests_route_to_the_teaching_loop` errors because no matching route exists, and the other new tests fail because the visual contract text is absent.

- [ ] **Step 3: Route visual requests from the root skill**

In `skills/learning-agent/SKILL.md`, replace the active-lesson routing bullet with:

```markdown
- For an active lesson, practice, an explanation, a visual request or visual-worthy explanation, a hint, a lab, independent-attempt behavior, remediation, or session continuity, read [teaching loop](references/teaching-loop.md).
```

Replace the safety routing bullet with:

```markdown
- For any lab or environment concern, and for a source, version-sensitive claim or visual, missing tool, network or test fault, credential, cloud, destructive, production, or public-exposure concern, read [safety and sources](references/safety-and-sources.md) before teaching, visual generation, or lab execution. Also read the teaching loop for a lab's instructional interaction.
```

- [ ] **Step 4: Add the contextual visual policy to the teaching loop**

Insert this section after the seven teaching stages and before “Coach-first assistance” in `skills/learning-agent/references/teaching-loop.md`:

```markdown
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
```

- [ ] **Step 5: Extend source and safety policy to visual content**

Insert this section after “Source policy” and before “Lab safety gate” in `skills/learning-agent/references/safety-and-sources.md`:

```markdown
## Visual accuracy and safety

A technical visual must agree with the source material, code, commands, or observed system state used in the lesson. Before presenting a version-sensitive visual as current, verify its claims against a current primary or official publisher source and record that source through the approved state workflow. If verification is unavailable, limit the visual to stable foundations and mark affected claims stale or unverified.

Generated imagery must not invent interfaces, command output, provider behavior, resource topology, or precise implementation details. Visual content must not expose secrets or reproduce raw sensitive output. Creating or displaying a visual does not bypass the lab safety gate for costly, destructive, privileged, shared, production, or publicly exposed actions.
```

- [ ] **Step 6: Run the focused tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_skill_contract -v
```

Expected: all `SkillContractTests` pass.

- [ ] **Step 7: Commit the internal teaching contract**

Run:

```bash
git add tests/test_skill_contract.py skills/learning-agent/SKILL.md skills/learning-agent/references/teaching-loop.md skills/learning-agent/references/safety-and-sources.md
git commit -m "feat: add contextual visual teaching policy"
```

### Task 2: Public Plugin Capability and Documentation

**Files:**
- Modify: `tests/test_plugin_contract.py`
- Modify: `.codex-plugin/plugin.json`
- Modify: `README.md`

**Interfaces:**
- Consumes: the “Contextual visuals” behavior and fallback contract produced by Task 1.
- Produces: manifest capability string `Contextual visual explanations` and learner-facing documentation for optional visuals and persistence.

- [ ] **Step 1: Add a failing public contract test**

Append this method to `PluginContractTests` in `tests/test_plugin_contract.py`:

```python
    def test_public_contract_documents_optional_contextual_visuals(self) -> None:
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            "Contextual visual explanations",
            manifest["interface"]["capabilities"],
        )

        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "## Contextual visuals",
            "only when it materially improves",
            "text or ASCII fallback",
            "explicit approval",
            "visuals/<lesson-id>/",
            "never mastery evidence",
        ):
            self.assertIn(phrase, text)
```

- [ ] **Step 2: Run the public contract test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_plugin_contract -v
```

Expected: `test_public_contract_documents_optional_contextual_visuals` fails because the capability and README section do not exist.

- [ ] **Step 3: Advertise the capability in the manifest**

In `.codex-plugin/plugin.json`, append the following string to `interface.capabilities` after `Evidence-based assessment` and keep valid JSON punctuation:

```json
"Contextual visual explanations"
```

The resulting array must be:

```json
"capabilities": [
  "Interactive tutoring",
  "Local course state",
  "Evidence-based assessment",
  "Contextual visual explanations"
]
```

Do not change the plugin version in this task; release versioning is outside the approved feature scope.

- [ ] **Step 4: Document contextual visuals and optional persistence**

Insert this section in `README.md` after “Start, continue, and inspect a course” and before “Course files”:

```markdown
## Contextual visuals

During a lesson, Learning Agent can use a diagram, interactive explanation, or image only when it materially improves one bounded concept or when the learner asks for one. It uses visual capabilities available in the Codex host and continues with a text or ASCII fallback when they are unavailable, so visuals are optional rather than a course requirement.

Each visual leads back to learner work: predict a result, manipulate an input, inspect a relationship, or explain what changed. The visual itself is never mastery evidence, and visual assistance during graded work follows the same hint and authorship rules as text assistance.

Visuals remain in the conversation by default. When one has lasting review value, Learning Agent asks for explicit approval before embedding it in a lesson or saving an export under `visuals/<lesson-id>/`. Saved visuals remain outside `.learning/` and are not required to validate or resume the course.
```

In the course tree under “Course files”, insert this optional directory between `notes/` and `.learning/`:

```text
├── visuals/                    # optional, learner-approved visual exports
```

- [ ] **Step 5: Run the public contract tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_plugin_contract -v
```

Expected: all `PluginContractTests` pass.

- [ ] **Step 6: Run the full repository verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/learning-agent
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/plugin-creator/scripts/validate_plugin.py" .
git diff --check
```

Expected:

- the full `unittest` suite reports `OK`;
- the skill validator reports the skill is valid;
- the plugin validator reports the plugin is valid;
- `git diff --check` prints no output and exits 0.

- [ ] **Step 7: Commit the public capability**

Run:

```bash
git add tests/test_plugin_contract.py .codex-plugin/plugin.json README.md
git commit -m "docs: expose contextual visual learning"
```

## Completion Check

After both task commits, run:

```bash
git status --short
git log -3 --oneline
```

Expected: only pre-existing unrelated user files remain untracked or modified; the two implementation commits appear after the design-spec commit `5632d85`.
