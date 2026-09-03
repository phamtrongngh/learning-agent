import unittest

from scripts.learning_engine.graph import topological_lessons, validate_prerequisite_graph
from tests.helpers import valid_initialization


class GraphTests(unittest.TestCase):
    def test_rejects_cycle_with_readable_path(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        curriculum["lessons"] = [
            {"id": "a", "title": "A", "milestone_id": "m1", "prerequisites": ["b"], "required_competencies": ["c1"]},
            {"id": "b", "title": "B", "milestone_id": "m1", "prerequisites": ["a"], "required_competencies": ["c1"]},
        ]
        self.assertEqual(validate_prerequisite_graph(curriculum), ["prerequisite cycle: a -> b -> a"])

    def test_topological_order_is_stable(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        self.assertEqual(topological_lessons(curriculum), ["lesson-1", "lesson-2"])

    def test_reports_unknown_prerequisites_before_cycle_errors(self) -> None:
        curriculum = valid_initialization()["curriculum"]
        curriculum["lessons"] = [
            {"id": "a", "title": "A", "milestone_id": "m1", "prerequisites": ["missing", "b"], "required_competencies": ["c1"]},
            {"id": "b", "title": "B", "milestone_id": "m1", "prerequisites": ["a"], "required_competencies": ["c1"]},
        ]
        self.assertEqual(
            validate_prerequisite_graph(curriculum),
            [
                "curriculum.lessons[a] references unknown prerequisite missing",
                "prerequisite cycle: a -> b -> a",
            ],
        )


if __name__ == "__main__":
    unittest.main()
