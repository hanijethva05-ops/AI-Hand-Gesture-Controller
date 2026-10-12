"""Simple hand-position calibration manager."""

import json
from pathlib import Path


class CalibrationManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve().with_name("calibration.json")
        self.data = {"x_min": 0.08, "x_max": 0.92, "y_min": 0.08, "y_max": 0.92}
        self.samples = []
        self.is_calibrating = False
        self.status_message = "Calibration ready"
        self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                values = json.loads(self.config_path.read_text(encoding="utf-8"))
                for key in self.data:
                    if key in values:
                        self.data[key] = float(values[key])
            except (OSError, ValueError, TypeError) as exc:
                self.status_message = f"Using default calibration: {exc}"

    def start(self):
        self.samples.clear()
        self.is_calibrating = True
        self.status_message = "Calibration: move index finger around the camera frame"

    def update(self, gesture_data):
        if not self.is_calibrating or not gesture_data:
            return
        cursor = gesture_data.get("cursor")
        if cursor is None:
            return
        self.samples.append((float(cursor[0]), float(cursor[1])))
        self.status_message = f"Calibration samples: {len(self.samples)}/60"
        if len(self.samples) >= 60:
            xs = [point[0] for point in self.samples]
            ys = [point[1] for point in self.samples]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            if x_max - x_min >= 0.25 and y_max - y_min >= 0.25:
                padding = 0.03
                self.data = {
                    "x_min": max(0.0, x_min - padding),
                    "x_max": min(1.0, x_max + padding),
                    "y_min": max(0.0, y_min - padding),
                    "y_max": min(1.0, y_max + padding),
                }
                self.status_message = "Calibration complete"
            else:
                self.status_message = "Not enough hand movement; using current calibration"
            self.is_calibrating = False

    def map_point(self, x, y):
        x_min, x_max = self.data["x_min"], self.data["x_max"]
        y_min, y_max = self.data["y_min"], self.data["y_max"]
        mapped_x = (float(x) - x_min) / max(0.01, x_max - x_min)
        mapped_y = (float(y) - y_min) / max(0.01, y_max - y_min)
        return max(0.0, min(1.0, mapped_x)), max(0.0, min(1.0, mapped_y))

    def reset(self):
        self.data = {"x_min": 0.08, "x_max": 0.92, "y_min": 0.08, "y_max": 0.92}
        self.samples.clear()
        self.is_calibrating = False
        self.status_message = "Calibration reset"
        self.save()

    def save(self):
        self.config_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        self.status_message = "Calibration saved"
