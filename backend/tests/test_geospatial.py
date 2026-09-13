import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.geospatial import calibrate_dsm, parse_ground_control_points, write_dsm_geotiff


class GeospatialCalibrationTests(unittest.TestCase):
    def test_ground_pixels_and_ground_elevation_produce_metric_dsm(self) -> None:
        heights = np.zeros((8, 8), dtype=np.float32)
        labels = np.ones((8, 8), dtype=np.uint8)
        labels[2:6, 2:6] = 3
        heights[2:6, 2:6] = 4.0

        dsm, calibration = calibrate_dsm(heights, labels, ground_elevation=120.5)

        self.assertIsNotNone(dsm)
        self.assertEqual(calibration["status"], "calibrated")
        self.assertEqual(calibration["method"], "ground_pixels_plus_ground_elevation")
        self.assertAlmostEqual(calibration["residualError"], 0.0, places=5)
        self.assertEqual(float(dsm[0, 0]), 120.5)
        self.assertEqual(float(dsm[3, 3]), 124.5)

    def test_ground_control_points_fit_a_metric_ground_plane(self) -> None:
        heights = np.zeros((8, 8), dtype=np.float32)
        labels = np.ones((8, 8), dtype=np.uint8)
        points = [(0.0, 0.0, 100.0), (7.0, 0.0, 107.0), (0.0, 7.0, 114.0)]

        dsm, calibration = calibrate_dsm(heights, labels, ground_control_points=points)

        self.assertEqual(calibration["status"], "calibrated")
        self.assertEqual(calibration["method"], "ground_control_points")
        self.assertAlmostEqual(float(dsm[7, 7]), 121.0, places=4)
        self.assertAlmostEqual(calibration["residualError"], 0.0, places=10)

    def test_calibration_is_flagged_without_ground_evidence(self) -> None:
        dsm, calibration = calibrate_dsm(np.ones((8, 8), dtype=np.float32), None, ground_elevation=100.0)

        self.assertIsNone(dsm)
        self.assertEqual(calibration["status"], "insufficient_ground_evidence")

    def test_ground_control_points_must_land_on_ground_pixels(self) -> None:
        labels = np.ones((8, 8), dtype=np.uint8)
        labels[3:5, 3:5] = 3
        points = [(0.0, 0.0, 100.0), (7.0, 0.0, 107.0), (3.0, 3.0, 106.0)]

        dsm, calibration = calibrate_dsm(np.zeros((8, 8), dtype=np.float32), labels, ground_control_points=points)

        self.assertIsNone(dsm)
        self.assertEqual(calibration["status"], "invalid_ground_control_points")

    def test_ground_control_points_need_semantic_ground_evidence(self) -> None:
        points = [(0.0, 0.0, 100.0), (7.0, 0.0, 107.0), (0.0, 7.0, 114.0)]

        dsm, calibration = calibrate_dsm(np.zeros((8, 8), dtype=np.float32), None, ground_control_points=points)

        self.assertIsNone(dsm)
        self.assertEqual(calibration["status"], "insufficient_ground_evidence")

    def test_geotiff_parser_and_export_preserve_spatial_reference(self) -> None:
        points = parse_ground_control_points('[{"pixelX": 0, "pixelY": 1, "elevation": 100}]')
        self.assertEqual(points, [(0.0, 1.0, 100.0)])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dsm.tif"
            transform = from_origin(72.8, 19.1, 0.0001, 0.0001)
            write_dsm_geotiff(path, np.full((4, 5), 123.5, dtype=np.float32), {
                "crs": "EPSG:4326",
                "transform": list(transform),
                "bounds": {"left": 72.8, "bottom": 19.0996, "right": 72.8005, "top": 19.1},
                "resolution": [0.0001, 0.0001],
            })
            with rasterio.open(path) as dataset:
                self.assertEqual(dataset.crs.to_string(), "EPSG:4326")
                self.assertEqual(dataset.transform, transform)
                self.assertEqual(dataset.bounds.left, 72.8)
                self.assertEqual(dataset.bounds.top, 19.1)
                self.assertEqual(dataset.res, (0.0001, 0.0001))
                np.testing.assert_allclose(dataset.read(1), 123.5)


if __name__ == "__main__":
    unittest.main()
