# Learning Agent Codex Plugin — Design Specification

**Date:** 2026-09-02  
**Status:** Approved in chat; awaiting written-spec review  
**Plugin name:** `learning-agent`

## 1. Purpose

`learning-agent` turns Codex into a persistent, interactive tutor for technical
skills such as Terraform, AWS, and programming. A learner asks to study a
subject, and the plugin creates a self-contained course directory. That
directory holds the roadmap, lessons, labs, projects, evidence, and durable
learning state, so the course can continue across Codex sessions without a web
application, hosted LMS, database, or reliance on chat history.

The plugin must behave like a tutor rather than a tutorial generator or a
coding agent that completes exercises for the learner. It teaches in short
interactive loops, protects productive struggle, gathers multiple forms of
evidence, and advances only when the required competencies have been
demonstrated.

## 2. Product principles

1. **Technical skills first.** V0 is optimized for subjects that support
   terminal-based practice, observable artifacts, and executable validation.
   Its domain model remains general enough to support other subjects later.
2. **Visible destination, adaptive path.** Milestones and target competencies
   are stable and visible. Lesson detail, pace, remediation, and optional
   branches adapt to the learner's evidence.
3. **Evidence over confidence.** Neither a passing test nor a persuasive LLM
   judgment is sufficient by itself. Mastery requires the evidence types
   declared by the competency rubric.
4. **Coach before collaborator.** Codex observes, asks, and provides escalating
   hints before editing learner work. Agent-authored work is never represented
   as independent learner mastery.
5. **Local and inspectable.** Course state is stored as human-readable files in
   the course directory and can be versioned with Git.
6. **Deterministic state transitions.** The LLM teaches and makes semantic
   assessments; a local state engine validates schemas and enforces progression
   rules.
7. **Small interactions, not walls of text.** A lesson pauses at meaningful
   checkpoints and uses the learner's response to choose what comes next.

## 3. Goals

- Start a new technical course from a natural-language request.
- Diagnose the learner's baseline without requiring a long entrance exam.
- Produce a competency-based roadmap from the learner's goal.
- Teach one active lesson at a time through explanation, prediction, practice,
  reflection, and transfer.
- Generate labs, validators, milestone challenges, and a capstone project when
  appropriate to the subject.
- Attribute hints and agent assistance so assisted work is not misclassified.
- Record durable evidence and resume accurately in a new Codex session.
- Support remediation and independent retry after a failed or assisted attempt.
- Keep technical content version-aware and traceable to current sources.
- Validate plugin, skill, state engine, and end-to-end course flows before
  delivery.

## 4. Non-goals for V0

- A hosted LMS, browser UI, mobile application, or web dashboard.
- Accounts, cloud synchronization, collaboration, analytics, or leaderboards.
- A remote MCP service or persistent database.
- Guaranteed support for non-technical subjects.
- Cryptographic anti-cheat or protection against a learner manually modifying
  local state. The engine prevents accidental inconsistency, not hostile
  tampering.
- Pre-authoring complete curricula for every supported technology.
- Generating every lesson in full when the course is initialized.

## 5. Architecture

The plugin uses a hybrid architecture with two primary layers.

### 5.1 Tutor Skill

The Tutor Skill is the pedagogical control plane. It defines how Codex:

- recognizes new-course, resume, progress, hint, assessment, and retry intents;
- conducts the baseline diagnostic;
- constructs a competency graph and milestone roadmap;
- teaches interactively and avoids premature solution disclosure;
- chooses labs and evidence types appropriate to a competency;
- scores semantic evidence with a written rationale;
- selects remediation or the next lesson based on validated state;
- checks source freshness and applies lab safety policy.

The skill accepts natural language. The learner does not need to know the
state-engine commands.

### 5.2 Local State Engine

The Local State Engine is a bundled, dependency-free Python command-line tool
called by Codex. It:

- creates and validates course state;
- records append-only evidence events;
- checks prerequisites and rubric requirements;
- calculates allowed state transitions;
- opens the next lesson only when its prerequisites are satisfied;
- renders human-facing dashboards from structured state;
- performs atomic writes and state recovery.

The state engine does not generate lessons or decide whether an explanation is
conceptually correct. The Tutor Skill supplies structured semantic assessments;
the engine validates their shape, provenance, required evidence coverage, and
transition rules.

### 5.3 Plugin contents

The installable plugin will contain:

- `.codex-plugin/plugin.json` with validated plugin metadata;
- `skills/learning-agent/SKILL.md` for tutor behavior and routing;
- focused reference files for diagnostics, lesson delivery, mastery, safety,
  source policy, and state-engine usage;
- `scripts/learning_state.py` and small internal Python modules;
- reusable course templates and schema fixtures;
- automated tests and developer documentation.

V0 does not add an MCP server, app connector, hook, external package, or
authentication requirement.

## 6. Course directory

Each course is an independent directory, for example
`terraform-zero-to-hero/`.

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

`README.md` and `ROADMAP.md` are generated views for the learner. The structured
files under `.learning/` are authoritative. Learner artifacts live outside
`.learning/` so their work is clearly separated from control state.

Only the roadmap, competency definitions, first lesson, and immediately useful
scaffolding are materialized at course creation. Later lesson detail is
generated just in time, preventing stale content and large inactive tutorial
trees.

## 7. State model

### 7.1 `course.json`

Stores the schema version, course identifier, subject, learner goal, language,
time constraints, expected environment, creation time, and current course
status.

### 7.2 `curriculum.json`

Stores milestones, lessons, competencies, prerequisite edges, target levels,
required evidence types, and rubric rules. The prerequisite graph must be
acyclic. Stable identifiers are used so lesson titles can change without
breaking evidence references.

### 7.3 `progress.json`

Stores the active lesson, lesson states, competency mastery levels, milestone
states, remediation links, and available next actions. It is modified only by
the state engine.

### 7.4 `evidence.jsonl`

An append-only event journal. Each event includes:

- unique event and attempt identifiers;
- competency and lesson identifiers;
- evidence type and artifact reference;
- test or command summary when applicable;
- author provenance: learner, agent, or collaborative;
- highest hint level used;
- rubric level and evaluator rationale;
- timestamp and supersession relationship when reassessed.

Large raw command output and full chat transcripts are not copied into state.
State keeps concise summaries and stable paths to relevant artifacts.

### 7.5 `sources.json`

Stores the source URL or identifier, publisher, subject version, retrieval or
verification date, and freshness status. Current official documentation is
preferred for version-sensitive technical facts.

### 7.6 `sessions/`

Stores compact session summaries containing the active goal, work attempted,
evidence recorded, unresolved misconceptions, and suggested next action. These
summaries support continuity without recreating the conversation transcript.

## 8. State engine interface

The state engine exposes internal operations:

- `init`: validate an approved curriculum and initialize a course.
- `status`: return the minimal state needed for the current teaching turn.
- `record`: append a validated evidence event.
- `evaluate`: apply mastery and progression rules to current evidence.
- `advance`: transition to the next available lesson or milestone.
- `render`: regenerate `README.md` and `ROADMAP.md` from structured state.
- `validate`: check schemas, graph integrity, evidence references, and state
  consistency.
- `recover`: reconstruct derived progress from the evidence journal when safe.

Commands return machine-readable JSON to the Tutor Skill and a non-zero exit
status on failure. User-facing explanations remain the Tutor Skill's
responsibility.

State updates use temporary files plus atomic replacement. A failed validation
cannot partially advance a course. Recovery never silently discards evidence;
if reconstruction is ambiguous, the tutor stops progression and explains what
must be resolved.

## 9. Course initialization and diagnostic

The tutor first asks only for information that affects the course: target
outcome, relevant prior experience, available time or pace, and environment
constraints. It then runs an adaptive diagnostic with a small set of questions
and a mini-task.

The diagnostic stops as soon as it has enough evidence to place the learner. A
learner can prove existing knowledge with a challenge and skip redundant
instruction. Self-declared experience may guide question selection but cannot
by itself mark a competency mastered.

The tutor proposes the resulting milestones, competencies, and expected
projects before initialization. After acceptance, the state engine persists
the curriculum and creates the first lesson.

## 10. Adaptive curriculum

Milestones and their target competencies form the visible contract of the
course. The tutor may adapt:

- lesson ordering when prerequisite constraints permit;
- lesson depth and number of examples;
- optional practice and remediation branches;
- whether a learner can challenge out of familiar material;
- the concrete domain used by labs and projects;
- pacing based on recent evidence and learner preference.

The tutor must not silently remove a required outcome. A substantive change to
the target competencies is explained and recorded as a curriculum revision.

## 11. Lesson loop

Each lesson uses a short interactive cycle:

1. State the outcome and its practical relevance.
2. Elicit a prediction, explanation, or prior model from the learner.
3. Teach one bounded concept using the smallest useful explanation or demo.
4. Ask the learner to inspect, modify, or predict a small example.
5. Assign a hands-on lab that produces observable work.
6. Ask the learner to explain decisions and handle a meaningful variation.
7. Record evidence and determine pass, remediation, or another attempt.

The tutor pauses at meaningful interaction points. It does not dump the entire
lesson or solution unless the learner explicitly requests that mode.

## 12. Coach-first behavior and hint ladder

During a graded or mastery-bearing attempt, Codex does not edit the learner's
solution by default. It observes, asks questions, runs permitted validators,
and escalates support through this ladder:

1. Socratic or directional question.
2. Relevant concept reminder.
3. Targeted pointer to the area or class of error.
4. Partial scaffold or pseudocode.
5. Full solution or direct edit, only after an explicit request.

The highest hint level is attached to the attempt. Evidence produced after
levels 4 or 5 is assisted and cannot establish independent mastery. The tutor
creates an equivalent but non-identical retry after the learner studies the
solution.

If the learner asks Codex to collaborate directly, Codex may do so, but the
resulting work is attributed as collaborative rather than independent.

## 13. Mastery and progression

Competency evidence uses four levels:

- `0 — unobserved`: no relevant evidence;
- `1 — assisted`: succeeds only with material guidance or agent-authored work;
- `2 — independent`: performs and explains the target without material help;
- `3 — transfer`: applies the competency in a meaningfully new situation.

Each competency declares required evidence types. For V0 technical courses,
lesson mastery normally requires both practical evidence and explanatory
evidence. A passing automated test cannot replace understanding, and a correct
verbal answer cannot replace performance when the competency is practical.

A lesson passes only when every required competency reaches at least level 2
and its required evidence types are satisfied. A milestone challenge tests
transfer without hints and may require level 3 for selected competencies.

When evidence is insufficient, the tutor identifies the smallest specific gap,
creates a micro-lesson or focused exercise, and schedules a fresh attempt. A
learner may override progression and skip content, but the state becomes
`waived` or `skipped`; it is never relabeled as `mastered`.

## 14. Assessment integrity

The system is a learning aid, not a proctored examination platform. Its
integrity model is transparent attribution:

- all evidence records assistance and authorship;
- solution disclosure invalidates that attempt as independent evidence;
- retries use changed inputs or scenarios;
- chapter and milestone challenges disable proactive hints until the learner
  ends the attempt;
- the tutor records the rationale for semantic scores;
- the engine enforces declared evidence and prerequisite rules.

## 15. Source freshness

When the topic depends on changing tools, the tutor checks current primary or
official sources before finalizing a curriculum or teaching version-specific
behavior. It records the relevant version and verification date in
`sources.json`.

If live verification is unavailable, the tutor may continue with stable
foundational material but marks version-sensitive claims as unverified or
stale. It does not present recalled commands, pricing, limits, or current
provider behavior as verified facts.

## 16. Safety policy

Labs default to local, sandboxed, emulated, or containerized environments when
practical. The tutor must explain and obtain explicit confirmation before an
operation that may:

- create cloud charges;
- use real credentials or privileged access;
- modify shared or production infrastructure;
- delete resources or data;
- expose a service publicly.

Cloud labs include a cleanup step and verification. Secrets must not be written
into source files, evidence, session summaries, or Git. The tutor follows the
host Codex permission and sandbox model in addition to this pedagogical policy.

## 17. Natural-language interaction

Representative intents include:

- “I want to learn Terraform from zero to hero.”
- “Continue my current lesson.”
- “Show my progress.”
- “Give me one hint.”
- “Explain why this attempt did not pass.”
- “Let me retry this milestone.”
- “Skip this lesson for now.”

The skill recognizes intent from conversation and current directory state.
There is no required slash command or learner-facing CLI in V0.

## 18. Error handling

- **Missing tool:** setup becomes an explicit prerequisite step and is verified
  before the lab begins.
- **Environment or network failure:** the attempt is `inconclusive`, not a
  learner failure, until the fault is isolated.
- **Flaky or ambiguous validator:** automated output is not treated as decisive
  evidence; the tutor records the uncertainty.
- **Malformed or inconsistent state:** progression stops; `validate` and, when
  safe, `recover` are used before teaching continues.
- **Unavailable current source:** affected material is marked unverified.
- **Unsupported subject:** the tutor explains that V0 is technical-skills-first
  and offers a best-effort reduced mode without pretending executable mastery
  checks exist.
- **Manual skip:** the competency remains unmet and the prerequisite gap stays
  visible.

## 19. Testing strategy

### 19.1 Unit tests

Unit tests cover schema validation, stable identifiers, acyclic prerequisites,
mastery thresholds, required evidence combinations, hint attribution,
agent-authored evidence exclusion, atomic writes, rendering, and recovery.

### 19.2 Scenario tests

Fixture-driven scenarios cover:

- beginner and experienced-learner diagnostics;
- an independent pass;
- a passing test with an inadequate explanation;
- an assisted solution followed by independent retry;
- targeted remediation after a misconception;
- a milestone transfer challenge;
- skip/waive behavior;
- resume from a new session;
- malformed state and journal recovery;
- an inconclusive environment failure.

### 19.3 End-to-end validation

A Terraform fixture course exercises the full plugin flow without making the
core Terraform-specific. End-to-end smoke tests install the plugin from its
personal marketplace entry, initialize a temporary course, record evidence,
advance, render progress, resume, and validate final state.

Before delivery:

- the plugin manifest passes the plugin validator;
- the Tutor Skill passes the skill validator;
- all Python tests pass on the available platform;
- the generated source tree contains no placeholders or undeclared runtime
  dependencies.

## 20. Acceptance criteria

V0 is complete when:

1. The plugin installs through a personal Codex marketplace entry.
2. A natural-language request can start a technical course directory.
3. Diagnostic output can place or challenge an experienced learner without
   forcing a zero-level start.
4. The generated roadmap has stable competencies, prerequisites, and explicit
   rubrics.
5. A lesson can record explanatory and practical evidence.
6. Assisted or agent-authored work cannot satisfy independent mastery.
7. The state engine blocks invalid advancement and permits valid advancement.
8. Dashboard Markdown is regenerated from authoritative state.
9. A new Codex session can resume from the active lesson without prior chat
   context.
10. State corruption is detected and safe recovery preserves the evidence
    journal.
11. Destructive or cost-bearing labs require explicit learner confirmation.
12. Automated validators and end-to-end smoke tests pass.

## 21. Delivery boundary

The deliverable is an installable personal Codex plugin named
`learning-agent`, its local marketplace entry, complete source repository,
automated tests, and concise usage documentation. The initial implementation
does not include any V1 non-goals listed in this specification.
