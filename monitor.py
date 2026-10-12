"""Screen geometry helpers."""

import pyautogui


class MonitorManager:
    """Map normalized camera points to the primary desktop screen."""

    def __init__(self):
        self.width, self.height = pyautogui.size()

    def map_to_screen(self, x, y):
        x = max(0.0, min(1.0, float(x)))
        y = max(0.0, min(1.0, float(y)))
        return int(x * (self.width - 1)), int(y * (self.height - 1))

    def get_size(self):
        return self.width, self.height
