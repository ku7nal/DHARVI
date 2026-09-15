import unittest

from app.route_planner import plan_ranked_routes, plan_route


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

    def test_ranked_routes_expose_three_profiles_and_stable_order(self) -> None:
        labels = [0] * 49
        for row in range(7):
            for column in range(7):
                if row in (1, 3, 5) or column in (0, 6):
                    labels[row * 7 + column] = 5
        heights = [0.0] * 49
        for column in range(1, 6):
            heights[3 * 7 + column] = 20.0

        fastest = plan_ranked_routes(labels, 7, {"row": 3, "column": 0}, {"row": 3, "column": 6}, height_data=heights, profile="fastest")
        safest = plan_ranked_routes(labels, 7, {"row": 3, "column": 0}, {"row": 3, "column": 6}, height_data=heights, profile="safest")

        self.assertEqual(fastest["profile"], "fastest")
        self.assertEqual(len(fastest["alternatives"]), 3)
        self.assertEqual([item["profileScore"] for item in fastest["alternatives"]], sorted(item["profileScore"] for item in fastest["alternatives"]))
        self.assertEqual(fastest["path"], plan_ranked_routes(labels, 7, {"row": 3, "column": 0}, {"row": 3, "column": 6}, height_data=heights, profile="fastest")["path"])
        self.assertLess(fastest["distanceCells"], safest["distanceCells"])
        self.assertGreater(safest["riskScore"], 0)
        self.assertLess(safest["riskScore"], fastest["riskScore"])

    def test_accessible_profile_prefers_lower_slope_route(self) -> None:
        labels = [0] * 49
        for column in range(7):
            labels[3 * 7 + column] = 5
        for row in range(7):
            labels[row * 7] = 5
            labels[row * 7 + 6] = 5
        for column in range(7):
            labels[1 * 7 + column] = 5
            labels[5 * 7 + column] = 5
        heights = [0.0] * 49
        for column, value in enumerate((0.0, 10.0, 20.0, 30.0, 20.0, 10.0, 0.0)):
            heights[3 * 7 + column] = value

        result = plan_ranked_routes(labels, 7, {"row": 3, "column": 0}, {"row": 3, "column": 6}, height_data=heights, profile="accessible")

        self.assertEqual(result["profile"], "accessible")
        self.assertGreater(result["distanceCells"], 6)
        self.assertLess(result["accessibilityScore"], 10)

    def test_uncertainty_and_building_proximity_raise_risk(self) -> None:
        labels = [5] * 25
        labels[5] = 3
        uncertainty = [0.0] * 25
        uncertainty[12] = 1.0

        result = plan_ranked_routes(labels, 5, {"row": 2, "column": 0}, {"row": 2, "column": 4}, uncertainty_data=uncertainty, profile="safest")

        self.assertGreater(result["riskScore"], 0)
        self.assertIn("prediction uncertainty", result["avoidedHazards"])

    def test_rejects_malformed_or_non_finite_route_features(self) -> None:
        labels = [5] * 9
        with self.assertRaisesRegex(ValueError, "exactly 9 cells"):
            plan_ranked_routes(labels, 3, {"row": 0, "column": 0}, {"row": 2, "column": 2}, height_data=[])
        with self.assertRaisesRegex(ValueError, "finite numeric"):
            plan_ranked_routes(labels, 3, {"row": 0, "column": 0}, {"row": 2, "column": 2}, height_data=[float("nan")] * 9)


if __name__ == "__main__":
    unittest.main()
