"""AI Hand Gesture Desktop Controller entry point."""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

from actions import ActionController
from calibration import CalibrationManager
from feedback import HUD
from gestures import GestureEngine
from macros import MacroManager
from monitor import MonitorManager
from tray import start_system_tray

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_DIR / "config.json"


def load_config(path):
    with Path(path).open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict) or not isinstance(config.get("modes"), dict):
        raise ValueError("config.json must contain a 'modes' object.")
    return config


def run_app(args):
    config_path = Path(args.config).expanduser().resolve()
    config = load_config(config_path)
    modes = list(config["modes"])
    if args.list:
        for name, mapping in config["modes"].items():
            print(f"\n[{name.upper()}]")
            for gesture, action in mapping.items():
                print(f"  {gesture:18} -> {action}")
        return
    if args.mode:
        if args.mode not in modes:
            raise ValueError(f"Unknown mode {args.mode!r}. Available: {modes}")
        start_mode = args.mode
    else:
        start_mode = modes[0]

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    engine = GestureEngine(config)
    monitors = MonitorManager()
    actions = ActionController(config, monitors)
    calibration = CalibrationManager(config_path)
    macros = MacroManager(config)
    hud = HUD(config)
    shared_state = {"quit": False, "pause_toggle": False}
    tray_icon = start_system_tray(shared_state)

    camera = None
    if not args.demo:
        camera_index = args.camera if args.camera is not None else int(config.get("camera_index", 0))
        camera = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(camera_index)
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(camera_index)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(config.get("camera_width", 640)))
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config.get("camera_height", 480)))
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not camera.isOpened():
            engine.close()
            raise RuntimeError("Webcam open nahi hua. Camera permission aur index check karo.")

    mode_index = modes.index(start_mode)
    paused = bool(config.get("start_paused", True))
    last_action_time = 0.0
    current_gesture = None
    gesture_start = 0.0
    neutral_start = time.monotonic()
    action_latched = False
    previous_time = time.monotonic()
    fps = 0.0
    last_message = "Ready"
    last_control_time = 0.0
    previous_palm_y = None
    last_scroll_time = 0.0

    print("=== AI Hand Gesture Desktop Controller ===")
    print("M = mode | P = pause/resume | C = calibrate | R = reset calibration")
    print("H = HUD | G = guide | L = action log | 1/2/3 = macro record/stop/play | Q = quit")
    print("Starts paused for safety. Press P in the webcam window to resume.")

    try:
        while True:
            if shared_state.get("quit"):
                break
            if shared_state.pop("pause_toggle", False):
                paused = not paused
                actions.release_all()
                current_gesture = None
                action_latched = False

            if args.demo:
                frame = np.zeros((480, 640, 3), dtype="uint8")
                cv2.putText(frame, "DEMO MODE - NO CAMERA", (90, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                data = None
            else:
                success, frame = camera.read()
                if not success:
                    time.sleep(0.02)
                    continue
                frame = cv2.flip(frame, 1)
                data = None if paused else engine.process(frame)

            now = time.monotonic()
            delta = now - previous_time
            previous_time = now
            if delta > 0:
                fps = fps * 0.85 + (1.0 / delta) * 0.15 if fps else 1.0 / delta

            mode = modes[mode_index]
            gesture = data.get("gesture", "none") if data else "none"
            confidence = float(data.get("confidence", 0.0)) if data else 0.0
            cursor = data.get("cursor") if data else None
            landmarks = data.get("landmarks") if data else None
            if landmarks:
                engine.draw_landmarks(frame, landmarks)

            threshold = float(config.get("confidence_threshold", 0.60))
            is_valid = bool(data and confidence >= threshold and gesture not in set(config.get("disabled_gestures", [])))
            action_name = config["modes"].get(mode, {}).get(gesture) if is_valid and not paused else None

            if action_name == "move_mouse" and cursor:
                x_norm, y_norm = calibration.map_point(*cursor)
                x, y = monitors.map_to_screen(x_norm, y_norm)
                actions.move_mouse(x, y)
                last_message = "Moving mouse"
                previous_palm_y = cursor[1]
            elif action_name == "scroll_mode" and cursor:
                if previous_palm_y is not None and now - last_scroll_time >= 0.12:
                    change = cursor[1] - previous_palm_y
                    if abs(change) >= 0.025:
                        pyautogui.scroll(1 if change < 0 else -1)
                        last_scroll_time = now
                previous_palm_y = cursor[1]
            elif action_name == "brightness_mode" and cursor and now - last_control_time > 0.30:
                last_message = actions.set_brightness(int(max(0, min(100, (1 - cursor[1]) * 100))))
                last_control_time = now
            elif action_name == "volume_up" and is_valid and not paused:
                pass  # handled by the stable action trigger below
            else:
                previous_palm_y = None

            # Continuous controls do not run through the discrete trigger engine.
            if action_name in {"move_mouse", "scroll_mode", "brightness_mode"}:
                current_gesture = None
                action_latched = False
                neutral_start = now
            elif action_name and not paused and is_valid:
                neutral_start = now
                if gesture != current_gesture:
                    current_gesture = gesture
                    gesture_start = now
                    action_latched = False
                hold_needed = 0.35
                if action_name in {"copy", "paste", "undo", "redo", "close_tab", "screenshot", "show_desktop", "task_view"}:
                    hold_needed = 0.75
                if (not action_latched and now - gesture_start >= hold_needed
                        and now - last_action_time >= float(config.get("action_cooldown_seconds", 0.8))):
                    last_message = actions.execute(action_name, data)
                    macros.record_action(action_name)
                    last_action_time = now
                    action_latched = True
            else:
                if neutral_start == 0.0:
                    neutral_start = now
                elif now - neutral_start >= float(config.get("neutral_release_seconds", 0.5)):
                    current_gesture = None
                    action_latched = False
                if paused:
                    actions.release_all()

            state = {
                "mode": mode,
                "paused": paused,
                "fps": fps,
                "gesture": gesture,
                "confidence": confidence,
                "action": "PAUSED" if paused else (action_name or last_message),
                "action_log": actions.action_log,
                "guide": list(config["modes"].get(mode, {}).items()),
                "calibrating": calibration.is_calibrating,
            }
            display_frame = hud.draw(frame, state)
            cv2.imshow("AI Hand Gesture Desktop Controller", display_frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("p"), ord("P")):
                paused = not paused
                actions.release_all()
                current_gesture = None
                action_latched = False
                neutral_start = now
                last_message = "Paused" if paused else "Resumed"
            elif key in (ord("m"), ord("M")):
                actions.release_all()
                mode_index = (mode_index + 1) % len(modes)
                current_gesture = None
                action_latched = False
                last_message = f"Mode: {modes[mode_index]}"
            elif key in (ord("h"), ord("H")):
                hud.toggle_hud()
            elif key in (ord("g"), ord("G")):
                hud.toggle_guide()
            elif key in (ord("l"), ord("L")):
                hud.toggle_log()
            elif key in (ord("c"), ord("C")):
                calibration.start()
                last_message = "Calibration started; move hand around frame"
            elif key in (ord("r"), ord("R")):
                calibration.reset()
                last_message = "Calibration reset"
            elif key == ord("1"):
                macros.start_recording()
                last_message = "Macro recording started"
            elif key == ord("2"):
                last_message = macros.stop_recording()
            elif key == ord("3"):
                last_message = macros.play(actions)
            elif key in (ord("s"), ord("S")):
                calibration.save()
                last_message = "Calibration saved"

            if calibration.is_calibrating and data:
                calibration.update(data)
                last_message = calibration.status_message
    finally:
        actions.release_all()
        if camera is not None:
            camera.release()
        engine.close()
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass
        cv2.destroyAllWindows()
        print("Controller closed safely.")


def parse_args():
    parser = argparse.ArgumentParser(description="AI Hand Gesture Desktop Controller")
    parser.add_argument("--camera", type=int, default=None, help="Camera index, e.g. 0 or 1")
    parser.add_argument("--mode", choices=["normal", "presentation", "gaming", "browser", "windows"])
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--list", action="store_true", help="List gesture mappings")
    parser.add_argument("--demo", action="store_true", help="Open the UI without using a camera")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run_app(parse_args())
    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as exc:
        print(f"[Startup Error] {exc}")
        raise
