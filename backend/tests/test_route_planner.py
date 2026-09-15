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

    def test_debris_cells_force_a_detour_and_are_reported(self) -> None:
        labels = [0] * 25
        for column in range(5):
            labels[2 * 5 + column] = 5
        for row in range(5):
            labels[row * 5 + 4] = 5
            labels[row * 5] = 5
        for column in range(5):
            labels[4 * 5 + column] = 5

        result = plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 4, "column": 4}, [{"row": 2, "column": 2}])

        self.assertEqual(result["distanceCells"], 6)
        self.assertEqual(result["path"][1], {"row": 3, "column": 0})
        self.assertEqual(result["hazards"], {"waterCells": 0, "debrisCells": 1, "blockedRoadCells": 1, "waterBlockedRoadCells": 0, "waterAvoidance": True})
        self.assertNotIn({"row": 2, "column": 2}, result["path"])

    def test_clearing_debris_restores_the_unblocked_route(self) -> None:
        labels = [5] * 25
        baseline = plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4})
        detour = plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4}, [{"row": 2, "column": 2}])

        self.assertIn({"row": 2, "column": 2}, baseline["path"])
        self.assertNotIn({"row": 2, "column": 2}, detour["path"])
        self.assertEqual(plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4})["path"], baseline["path"])

    def test_debris_can_make_a_road_network_unrouteable(self) -> None:
        labels = [0] * 9
        labels[3:6] = [5, 5, 5]

        with self.assertRaisesRegex(ValueError, "after applying the active hazards"):
            plan_route(labels, 3, {"row": 1, "column": 0}, {"row": 1, "column": 2}, [{"row": 1, "column": 1}])

    def test_water_cells_are_reported_when_water_avoidance_is_active(self) -> None:
        labels = [5] * 25
        labels[12] = 4

        baseline = plan_route([5] * 25, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4})
        result = plan_route(labels, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4})

        self.assertIn({"row": 2, "column": 2}, baseline["path"])
        self.assertNotIn({"row": 2, "column": 2}, result["path"])
        self.assertEqual(result["hazards"]["waterCells"], 1)
        self.assertGreater(result["hazards"]["waterBlockedRoadCells"], 0)
        self.assertTrue(result["hazards"]["waterAvoidance"])

    def test_rejects_endpoint_inside_water_buffer(self) -> None:
        labels = [5] * 25
        labels[12] = 4

        with self.assertRaisesRegex(ValueError, "start must not be adjacent"):
            plan_route(labels, 5, {"row": 1, "column": 1}, {"row": 2, "column": 4})


if __name__ == "__main__":
    unittest.main()
