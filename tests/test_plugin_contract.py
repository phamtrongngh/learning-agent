import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginContractTests(unittest.TestCase):
    def test_manifest_and_component_roots_exist(self) -> None:
        manifest_path = ROOT / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest_path.is_file())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "learning-agent")
        self.assertTrue(manifest["description"].strip())
        self.assertTrue((ROOT / "skills" / "learning-agent").is_dir())
        self.assertTrue((ROOT / "scripts").is_dir())
        self.assertTrue((ROOT / "assets").is_dir())

    def test_readme_documents_user_and_developer_flows(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "I want to learn Terraform from zero to hero",
            "Continue my current lesson",
            "python3 -m unittest discover -s tests -v",
            "Python 3.11",
            "explicit confirmation",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
