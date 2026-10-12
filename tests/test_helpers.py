import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calibration import CalibrationManager
from gesture_helpers import clamp, map_range


class HelperTests(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp(10, 0, 5), 5)
        self.assertEqual(clamp(-1, 0, 5), 0)
        self.assertEqual(clamp(3, 0, 5), 3)

    def test_map_range(self):
        self.assertEqual(map_range(5, 0, 10, 0, 100), 50)
        self.assertEqual(map_range(1, 1, 1, 9, 99), 9)

    def test_config_modes(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.assertIn("normal", config["modes"])
        self.assertIn("presentation", config["modes"])

    def test_calibration_map(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = CalibrationManager(Path(folder) / "config.json")
            x, y = manager.map_point(0.5, 0.5)
            self.assertAlmostEqual(x, 0.5, places=5)
            self.assertAlmostEqual(y, 0.5, places=5)


if __name__ == "__main__":
    unittest.main()
