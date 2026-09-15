import unittest

import numpy as np

from app.building_footprints import clean_semantic_labels, extract_building_footprints, infer_roof_type
from app.semantic_contract import BUILDING_CLASS


class BuildingFootprintTests(unittest.TestCase):
    def test_semantic_cleanup_removes_tiny_buildings_and_fills_small_holes(self) -> None:
        labels = np.ones((12, 12), dtype=np.uint8)
        labels[2:9, 2:9] = BUILDING_CLASS
        labels[5, 5] = 0
        labels[1, 1] = BUILDING_CLASS
        labels[9, 9] = BUILDING_CLASS

        cleaned = clean_semantic_labels(labels, minimum_building_area=4, maximum_building_hole_area=2)

        self.assertEqual(int(cleaned[5, 5]), BUILDING_CLASS)
        self.assertEqual(int(cleaned[1, 1]), 1)
        self.assertEqual(int(cleaned[9, 9]), 1)
        self.assertEqual(int(cleaned[4, 4]), BUILDING_CLASS)

    def test_roof_type_inference_uses_height_profiles(self) -> None:
        labels = np.zeros((11, 11), dtype=np.uint8)
        labels[2:9, 2:9] = BUILDING_CLASS
        flat = np.full((11, 11), 10, dtype=np.float32)
        gabled = flat.copy()
        for column in range(2, 9):
            gabled[2:9, column] = 10 + (3 - abs(column - 5)) * 2
        hipped = flat.copy()
        for row in range(2, 9):
            for column in range(2, 9):
                hipped[row, column] = 10 + (3 - max(abs(column - 5), abs(row - 5))) * 2
        dome = flat.copy()
        for row in range(2, 9):
            for column in range(2, 9):
                radius = np.hypot(column - 5, row - 5) / 3
                dome[row, column] = 10 + max(0, 1 - radius**2) * 6

        self.assertEqual(infer_roof_type(labels == BUILDING_CLASS, flat), "flat")
        self.assertEqual(infer_roof_type(labels == BUILDING_CLASS, gabled), "gabled")
        self.assertEqual(infer_roof_type(labels == BUILDING_CLASS, hipped), "hipped")
        self.assertEqual(infer_roof_type(labels == BUILDING_CLASS, dome), "dome")

    def test_adjacent_buildings_remain_separate_and_small_building_is_kept(self) -> None:
        labels = np.zeros((12, 16), dtype=np.uint8)
        labels[2:6, 2:5] = BUILDING_CLASS
        labels[2:6, 6:9] = BUILDING_CLASS
        labels[8:10, 11:13] = BUILDING_CLASS
        heights = labels.astype(np.float32) * 10

        regions = extract_building_footprints(labels, heights)

        self.assertEqual(len(regions), 3)
        self.assertEqual(sorted(region["area"] for region in regions), [4, 12, 12])
        self.assertTrue(all(len(region["footprint"]) >= 4 for region in regions))

    def test_hole_is_retained_as_a_separate_inner_ring(self) -> None:
        labels = np.zeros((12, 12), dtype=np.uint8)
        labels[2:10, 2:10] = BUILDING_CLASS
        labels[5:7, 5:7] = 0
        heights = labels.astype(np.float32) * 12

        region = extract_building_footprints(labels, heights)[0]

        self.assertEqual(len(region["holes"]), 1)
        self.assertGreater(len(region["holes"][0]), 3)

    def test_isolated_noise_is_removed_but_building_uses_surrounding_ground(self) -> None:
        labels = np.zeros((14, 14), dtype=np.uint8)
        labels[4:9, 4:9] = BUILDING_CLASS
        labels[6, 6] = 0
        labels[1, 1] = BUILDING_CLASS
        heights = np.full((14, 14), 3, dtype=np.float32)
        heights[4:9, 4:9] = 18
        heights[6, 6] = 3

        region = extract_building_footprints(labels, heights)[0]

        self.assertEqual(region["area"], 24)
        self.assertAlmostEqual(region["groundHeight"], 3.0)
        self.assertAlmostEqual(region["height"], 15.0)
        self.assertEqual(region["roofType"], "flat")
        self.assertAlmostEqual(region["wallHeight"], 15.0)
        self.assertAlmostEqual(region["roofRise"], 0.0)

    def test_one_cell_building_is_kept_when_it_is_above_ground(self) -> None:
        labels = np.zeros((5, 5), dtype=np.uint8)
        labels[2, 2] = BUILDING_CLASS
        heights = np.zeros((5, 5), dtype=np.float32)
        heights[2, 2] = 8

        regions = extract_building_footprints(labels, heights)

        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["area"], 1)

    def test_jagged_outline_is_simplified_without_changing_extent(self) -> None:
        labels = np.zeros((14, 14), dtype=np.uint8)
        labels[3:11, 3:11] = BUILDING_CLASS
        labels[3, 5] = 0
        labels[3, 6] = 0
        labels[4, 5] = BUILDING_CLASS
        heights = labels.astype(np.float32) * 8

        region = extract_building_footprints(labels, heights)
        footprint = region[0]["footprint"]

        self.assertLessEqual(len(footprint), 10)
        self.assertEqual(region[0]["minRow"], 3)
        self.assertEqual(region[0]["maxColumn"], 10)

    def test_noisy_rectangular_outline_is_orthogonalized(self) -> None:
        labels = np.zeros((20, 20), dtype=np.uint8)
        labels[4:16, 4:16] = BUILDING_CLASS
        labels[4, 7:10] = 0
        labels[5, 7:10] = BUILDING_CLASS
        labels[15, 11:14] = 0
        labels[14, 11:14] = BUILDING_CLASS
        heights = labels.astype(np.float32) * 12

        region = extract_building_footprints(labels, heights)[0]
        footprint = region["footprint"]
        self.assertLessEqual(len(footprint), 4)
        self.assertEqual(len({round(point[1], 6) for point in footprint}), 2)
        self.assertEqual(len({round(point[0], 6) for point in footprint}), 2)
        self.assertAlmostEqual(min(point[0] for point in footprint), -0.3)
        self.assertAlmostEqual(max(point[0] for point in footprint), 0.3)

    def test_diagonal_outline_keeps_simplified_fallback(self) -> None:
        labels = np.zeros((16, 16), dtype=np.uint8)
        for row in range(3, 12):
            for column in range(3, 12):
                if column >= row - 1:
                    labels[row, column] = BUILDING_CLASS
        heights = labels.astype(np.float32) * 10

        region = extract_building_footprints(labels, heights)[0]
        footprint = region["footprint"]
        self.assertGreaterEqual(len(footprint), 4)
        self.assertTrue(any(abs(footprint[index][0] - footprint[(index + 1) % len(footprint)][0]) > 1e-6 and abs(footprint[index][1] - footprint[(index + 1) % len(footprint)][1]) > 1e-6 for index in range(len(footprint))))

    def test_high_confidence_internal_boundary_splits_connected_buildings(self) -> None:
        labels = np.zeros((50, 60), dtype=np.uint8)
        labels[2:48, 5:55] = BUILDING_CLASS
        heights = labels.astype(np.float32) * 12
        boundary = np.zeros_like(heights)
        boundary[2:48, 30] = 1.0

        regions = extract_building_footprints(labels, heights, boundary_confidence=boundary)

        self.assertEqual(len(regions), 2)
        self.assertTrue(all(region["source"] == "semantic_head" for region in regions))


if __name__ == "__main__":
    unittest.main()
