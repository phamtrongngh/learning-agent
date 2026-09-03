import unittest

from scripts.learning_engine.progression import build_initial_progress
from scripts.learning_engine.rendering import render_readme, render_roadmap
from tests.helpers import valid_initialization


class RenderingTests(unittest.TestCase):
    def test_readme_identifies_active_lesson(self) -> None:
        payload = valid_initialization()
        progress = build_initial_progress(payload["curriculum"])

        rendered = render_readme(payload["course"], payload["curriculum"], progress)

        self.assertIn("# Terraform Zero to Hero", rendered)
        self.assertIn("Current lesson: Foundations", rendered)

    def test_roadmap_uses_stable_status_markers(self) -> None:
        payload = valid_initialization()
        progress = build_initial_progress(payload["curriculum"])

        rendered = render_roadmap(payload["curriculum"], progress)

        self.assertIn("▶ `lesson-1` Foundations", rendered)
        self.assertIn("🔒 `lesson-2` State and collaboration", rendered)

    def test_rendered_views_are_deterministic_and_explain_their_source(self) -> None:
        payload = valid_initialization()
        progress = build_initial_progress(payload["curriculum"])

        readme = render_readme(payload["course"], payload["curriculum"], progress)
        roadmap = render_roadmap(payload["curriculum"], progress)

        self.assertEqual(readme, render_readme(payload["course"], payload["curriculum"], progress))
        self.assertEqual(roadmap, render_roadmap(payload["curriculum"], progress))
        self.assertIn("generated from `.learning/`", readme)
        self.assertIn("Completed lessons: 0 / 2", readme)
        self.assertIn("Competency levels", readme)
        self.assertIn("Milestones", roadmap)


if __name__ == "__main__":
    unittest.main()
