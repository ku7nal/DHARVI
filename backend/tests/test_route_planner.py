import unittest

from app.route_planner import plan_route


class RoutePlannerTests(unittest.TestCase):
    def test_returns_the_shortest_connected_road_path(self) -> None:
        labels = [0] * 25
        for column in range(5):
            labels[2 * 5 + column] = 5
        for row in range(5):
            labels[row * 5 + 4] = 5

        result = plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 4, "column": 4})

        self.assertEqual(result["distanceCells"], 6)
        self.assertEqual(result["path"][0], {"row": 2, "column": 0})
        self.assertEqual(result["path"][-1], {"row": 4, "column": 4})
        self.assertTrue(all(labels[point["row"] * 5 + point["column"]] == 5 for point in result["path"]))

    def test_rejects_points_that_are_not_roads(self) -> None:
        labels = [5] * 9
        labels[0] = 1

        with self.assertRaisesRegex(ValueError, "start must be on a semantic road"):
            plan_route(labels, 3, {"row": 0, "column": 0}, {"row": 2, "column": 2})

    def test_reports_disconnected_roads(self) -> None:
        labels = [0] * 9
        labels[0] = 5
        labels[8] = 5

        with self.assertRaisesRegex(ValueError, "No connected road route"):
            plan_route(labels, 3, {"row": 0, "column": 0}, {"row": 2, "column": 2})


if __name__ == "__main__":
    unittest.main()
