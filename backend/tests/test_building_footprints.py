import unittest

import numpy as np

from app.building_footprints import extract_building_footprints


class BuildingFootprintTests(unittest.TestCase):
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
