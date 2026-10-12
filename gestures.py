"""Hand landmark detection and MediaPipe gesture classification."""

from __future__ import annotations

import math
import time
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "gesture_recognizer.task"

LABEL_MAP = {
    "Open_Palm": "open_palm",
    "Closed_Fist": "closed_fist",
    "Pointing_Up": "point_up",
    "Thumb_Up": "thumb_up",
    "Thumb_Down": "thumb_down",
    "Victory": "peace",
    "ILoveYou": "shaka",
    "None": "none",
}


def distance(point_a, point_b):
    """Euclidean distance between normalized landmarks."""
    return math.hypot(point_a.x - point_b.x, point_a.y - point_b.y)


def finger_states(landmarks):
    """Return finger extension states in [index, middle, ring, pinky] order."""
    tip_ids = (8, 12, 16, 20)
    pip_ids = (6, 10, 14, 18)
    return [
        landmarks[tip].y < landmarks[pip].y
        for tip, pip in zip(tip_ids, pip_ids)
    ]


def get_finger_states(landmarks, handedness="Right"):
    """Return [thumb, index, middle, ring, pinky] approximate states."""
    if handedness == "Right":
        thumb_up = landmarks[4].x < landmarks[3].x
    else:
        thumb_up = landmarks[4].x > landmarks[3].x
    return [thumb_up, *finger_states(landmarks)]


def ai_matches(expected_label, actual_label, confidence, threshold=0.80):
    """Compare a known MediaPipe category with a confidence threshold."""
    expected = LABEL_MAP.get(expected_label, expected_label).lower()
    actual = str(actual_label).lower()
    return actual == expected and float(confidence) >= threshold


class GestureEngine:
    """MediaPipe Gesture Recognizer with optional legacy fallback."""

    def __init__(self, config):
        self.config = config
        self.recognizer = None
        self.legacy_hands = None
        self.last_timestamp_ms = 0
        self.last_error = None
        self.position_history = []
        self.active_swipe = None
        self.active_swipe_until = 0.0
        self.confidence_threshold = float(config.get("confidence_threshold", 0.60))
        self._initialize()

    @property
    def ml_enabled(self):
        return self.recognizer is not None

    def _ensure_model(self):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
            return

        temp_path = MODEL_PATH.with_suffix(".download")
        request = urllib.request.Request(
            MODEL_URL,
            headers={"User-Agent": "AI-Hand-Gesture-Controller/1.0"},
        )
        print("[Setup] Downloading MediaPipe gesture model (first run only)...")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with temp_path.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
            if temp_path.stat().st_size < 1_000_000:
                raise RuntimeError("Downloaded model file is unexpectedly small.")
            temp_path.replace(MODEL_PATH)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _initialize(self):
        try:
            self._ensure_model()
            options = mp.tasks.vision.GestureRecognizerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.60,
                min_hand_presence_confidence=0.60,
                min_tracking_confidence=0.60,
            )
            self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(options)
            print("[Info] MediaPipe ML Gesture Recognizer enabled.")
        except Exception as exc:
            self.last_error = str(exc)
            print(f"[Warning] ML gesture model unavailable: {exc}")
            print("[Info] Falling back to MediaPipe hand landmarks.")
            self.legacy_hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.60,
                min_tracking_confidence=0.60,
            )

    @staticmethod
    def _normalize_landmarks(landmarks):
        # Both task and legacy APIs provide objects with x/y/z attributes.
        return list(landmarks)

    def _classify_landmarks(self, landmarks, handedness, ml_label="none", ml_score=0.0):
        f = get_finger_states(landmarks, handedness)
        index, middle, ring, pinky = f[1], f[2], f[3], f[4]
        d_index = distance(landmarks[4], landmarks[8])
        d_middle = distance(landmarks[4], landmarks[12])
        d_ring = distance(landmarks[4], landmarks[16])
        pinch_limit = 0.035

        # Give precise pinch geometry priority over broad model labels.
        if d_index < pinch_limit and d_middle >= pinch_limit:
            label, score = "pinch_index", 0.90
        elif d_middle < pinch_limit and d_index >= pinch_limit:
            label, score = "pinch_middle", 0.90
        elif d_ring < pinch_limit and d_index >= pinch_limit and d_middle >= pinch_limit:
            label, score = "pinch_ring", 0.90
        elif not index and middle and ring and not pinky:
            label, score = "copy_pose", 0.88
        elif index and not middle and not ring and pinky:
            label, score = "paste_pose", 0.88
        elif not index and middle and not ring and pinky:
            label, score = "undo_pose", 0.88
        elif index and not middle and ring and not pinky:
            label, score = "redo_pose", 0.88
        elif index and middle and ring and pinky and not f[0]:
            label, score = "four_fingers", 0.88
        elif index and pinky and not middle and not ring:
            label, score = "rock", 0.88
        elif ml_label in {"thumb_up", "thumb_down", "shaka"} and ml_score >= self.confidence_threshold:
            label, score = ml_label, ml_score
        elif ml_label == "open_palm" and ml_score >= self.confidence_threshold:
            label, score = "open_palm", ml_score
        elif ml_label == "closed_fist" and ml_score >= self.confidence_threshold:
            label, score = "closed_fist", ml_score
        elif index and middle and not ring and not pinky:
            label, score = "peace", 0.85
        elif index and not middle and not ring and not pinky:
            label, score = "point_up", 0.84
        elif all(f[1:]):
            label, score = "open_palm", max(0.75, ml_score)
        elif not any(f[1:]):
            label, score = "closed_fist", max(0.75, ml_score)
        elif ml_score >= self.confidence_threshold:
            label, score = ml_label, ml_score
        else:
            label, score = "none", 0.0

        now = time.monotonic()
        wrist_x = float(landmarks[0].x)
        self.position_history.append((now, wrist_x))
        self.position_history = [p for p in self.position_history if now - p[0] <= 0.35]
        if len(self.position_history) >= 3 and now >= self.active_swipe_until:
            delta_x = wrist_x - self.position_history[0][1]
            elapsed = now - self.position_history[0][0]
            if elapsed >= 0.10 and abs(delta_x) >= 0.28:
                self.active_swipe = "swipe_right" if delta_x > 0 else "swipe_left"
                self.active_swipe_until = now + 0.45
                self.position_history.clear()
        if now < self.active_swipe_until and self.active_swipe:
            label, score = self.active_swipe, 0.90

        return {
            "gesture": label,
            "confidence": float(score),
            "landmarks": landmarks,
            "handedness": handedness,
            "cursor": (float(landmarks[8].x), float(landmarks[8].y)),
            "fingers": f,
        }

    def process(self, frame):
        target_w = min(640, frame.shape[1])
        target_h = min(480, frame.shape[0])
        small = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False

        if self.recognizer is not None:
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = max(time.monotonic_ns() // 1_000_000, self.last_timestamp_ms + 1)
            self.last_timestamp_ms = timestamp_ms
            result = self.recognizer.recognize_for_video(image, timestamp_ms)
            if not result.hand_landmarks:
                self.position_history.clear()
                return None
            landmarks = result.hand_landmarks[0]
            handedness = "Right"
            if result.handedness and result.handedness[0]:
                handedness = result.handedness[0][0].category_name
            ml_label, ml_score = "none", 0.0
            if result.gestures and result.gestures[0]:
                category = result.gestures[0][0]
                ml_label = LABEL_MAP.get(category.category_name, category.category_name.lower())
                ml_score = float(category.score)
        else:
            result = self.legacy_hands.process(rgb)
            if not result.multi_hand_landmarks:
                self.position_history.clear()
                return None
            landmarks = result.multi_hand_landmarks[0].landmark
            handedness = "Right"
            if result.multi_handedness:
                try:
                    handedness = result.multi_handedness[0].classification[0].label
                except (IndexError, AttributeError):
                    pass
            ml_label, ml_score = "none", 0.0

        return self._classify_landmarks(landmarks, handedness, ml_label, ml_score)

    def draw_landmarks(self, frame, landmarks):
        height, width = frame.shape[:2]
        points = [(int(p.x * width), int(p.y * height)) for p in landmarks]
        for start, end in mp.solutions.hands.HAND_CONNECTIONS:
            cv2.line(frame, points[start], points[end], (70, 220, 120), 2, cv2.LINE_AA)
        for point in points:
            cv2.circle(frame, point, 4, (0, 220, 255), -1, cv2.LINE_AA)

    def close(self):
        if self.recognizer is not None:
            self.recognizer.close()
            self.recognizer = None
        if self.legacy_hands is not None:
            self.legacy_hands.close()
            self.legacy_hands = None
