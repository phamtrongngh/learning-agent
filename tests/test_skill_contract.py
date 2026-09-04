import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "learning-agent" / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_skill_routes_to_every_required_reference(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for name in (
            "course-lifecycle.md",
            "teaching-loop.md",
            "mastery-and-evidence.md",
            "safety-and-sources.md",
            "state-engine.md",
        ):
            self.assertIn(f"references/{name}", text)

    def test_skill_forbids_unattributed_solution_work(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertRegex(text, re.compile(r"agent-assisted", re.IGNORECASE))
        self.assertRegex(text, re.compile(r"hint level 4|hint level 5", re.IGNORECASE))

    def test_skill_requires_status_before_resume(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Run `status` before teaching", text)

    def test_skill_routes_lab_and_environment_concerns_through_safety_first(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        safety_route = next(
            line for line in text.splitlines()
            if "references/safety-and-sources.md" in line
        )
        self.assertRegex(safety_route, re.compile(r"lab", re.IGNORECASE))
        self.assertRegex(safety_route, re.compile(r"environment", re.IGNORECASE))
        self.assertRegex(safety_route, re.compile(r"before teaching or lab execution", re.IGNORECASE))

    def test_session_summaries_have_one_explicit_state_write_exception(self) -> None:
        state_engine = (ROOT / "skills" / "learning-agent" / "references" / "state-engine.md").read_text(encoding="utf-8")
        teaching_loop = (ROOT / "skills" / "learning-agent" / "references" / "teaching-loop.md").read_text(encoding="utf-8")
        self.assertIn("only direct-write exception", state_engine)
        self.assertIn("YYYYMMDDTHHMMSSZ.md", teaching_loop)

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
