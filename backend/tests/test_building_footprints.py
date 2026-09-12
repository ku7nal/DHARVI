import unittest

import numpy as np

from app.building_footprints import extract_building_footprints, infer_roof_type


class BuildingFootprintTests(unittest.TestCase):
    def test_roof_type_inference_uses_height_profiles(self) -> None:
        labels = np.zeros((11, 11), dtype=np.uint8)
        labels[2:9, 2:9] = 2
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

        self.assertEqual(infer_roof_type(labels == 2, flat), "flat")
        self.assertEqual(infer_roof_type(labels == 2, gabled), "gabled")
        self.assertEqual(infer_roof_type(labels == 2, hipped), "hipped")
        self.assertEqual(infer_roof_type(labels == 2, dome), "dome")

    def test_adjacent_buildings_remain_separate_and_small_building_is_kept(self) -> None:
        labels = np.zeros((12, 16), dtype=np.uint8)
        labels[2:6, 2:5] = 2
        labels[2:6, 6:9] = 2
        labels[8:10, 11:13] = 2
        heights = labels.astype(np.float32) * 10

        regions = extract_building_footprints(labels, heights)

        self.assertEqual(len(regions), 3)
        self.assertEqual(sorted(region["area"] for region in regions), [4, 12, 12])
        self.assertTrue(all(len(region["footprint"]) >= 4 for region in regions))

    def test_hole_is_retained_as_a_separate_inner_ring(self) -> None:
        labels = np.zeros((12, 12), dtype=np.uint8)
        labels[2:10, 2:10] = 2
        labels[5:7, 5:7] = 0
        heights = labels.astype(np.float32) * 12

        region = extract_building_footprints(labels, heights)[0]

        self.assertEqual(len(region["holes"]), 1)
        self.assertGreater(len(region["holes"][0]), 3)

    def test_isolated_noise_is_removed_but_building_uses_surrounding_ground(self) -> None:
        labels = np.zeros((14, 14), dtype=np.uint8)
        labels[4:9, 4:9] = 2
        labels[6, 6] = 0
        labels[1, 1] = 2
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
        labels[2, 2] = 2
        heights = np.zeros((5, 5), dtype=np.float32)
        heights[2, 2] = 8

        regions = extract_building_footprints(labels, heights)

        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["area"], 1)

    def test_jagged_outline_is_simplified_without_changing_extent(self) -> None:
        labels = np.zeros((14, 14), dtype=np.uint8)
        labels[3:11, 3:11] = 2
        labels[3, 5] = 0
        labels[3, 6] = 0
        labels[4, 5] = 2
        heights = labels.astype(np.float32) * 8

        region = extract_building_footprints(labels, heights)
        footprint = region[0]["footprint"]

        self.assertLessEqual(len(footprint), 10)
        self.assertEqual(region[0]["minRow"], 3)
        self.assertEqual(region[0]["maxColumn"], 10)


if __name__ == "__main__":
    unittest.main()
