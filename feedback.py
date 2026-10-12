"""OpenCV heads-up display for controller status and gesture guide."""

import cv2
import numpy as np


class HUD:
    def __init__(self, config):
        self.config = config
        self.show_hud = True
        self.show_guide = True
        self.show_log = True

    def toggle_hud(self):
        self.show_hud = not self.show_hud

    def toggle_guide(self):
        self.show_guide = not self.show_guide

    def toggle_log(self):
        self.show_log = not self.show_log

    @staticmethod
    def _text(image, text, x, y, scale=0.45, color=(240, 240, 240), thickness=1):
        cv2.putText(image, str(text)[:70], (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def draw(self, frame, state):
        image = frame.copy()
        h, w = image.shape[:2]
        if self.show_hud:
            overlay = image.copy()
            cv2.rectangle(overlay, (0, 0), (w, 118), (25, 28, 38), -1)
            cv2.addWeighted(overlay, 0.82, image, 0.18, 0, image)
            mode = state.get("mode", "normal").upper()
            status = "PAUSED - press P" if state.get("paused") else f"MODE: {mode}"
            self._text(image, status, 12, 24, 0.55, (100, 245, 140), 2)
            self._text(image, f"FPS: {state.get('fps', 0):.0f}", w - 90, 24, 0.48)
            self._text(image, f"Gesture: {state.get('gesture', 'none')}", 12, 48, 0.44, (40, 230, 255))
            self._text(image, f"Confidence: {state.get('confidence', 0):.0%}", 12, 70, 0.40)
            self._text(image, f"Action: {state.get('action', 'Ready')}", 12, 92, 0.42, (255, 210, 80))
            self._text(image, "M mode | P pause | C calibrate | H HUD | G guide | Q quit", 12, 111, 0.32)

        if self.show_log and state.get("action_log"):
            logs = state["action_log"][-3:]
            top = 142 if self.show_hud else 24
            for line in logs:
                self._text(image, line, 12, top, 0.34, (180, 230, 255))
                top += 18

        if not self.show_guide:
            return image

        guide = state.get("guide", [])
        panel_w = 360
        panel_h = max(h, 100 + len(guide) * 22 + 40)
        panel = np.full((panel_h, panel_w, 3), (28, 31, 42), dtype=np.uint8)
        self._text(panel, "GESTURE GUIDE", 14, 28, 0.60, (120, 220, 255), 2)
        self._text(panel, f"Mode: {state.get('mode', 'normal').upper()}", 14, 53, 0.43, (100, 240, 140))
        self._text(panel, "Hold the pose steady; return to neutral between actions.", 14, 76, 0.32)
        y = 105
        for gesture, action in guide:
            self._text(panel, f"{gesture} -> {action}", 14, y, 0.34)
            y += 22
        self._text(panel, "M mode | P pause | C calibration | Q quit", 14, panel_h - 16, 0.32, (120, 220, 255))

        canvas = np.zeros((panel_h, w, 3), dtype=np.uint8)
        canvas[:h, :w] = image
        return np.hstack((canvas, panel))
