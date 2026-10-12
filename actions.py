"""Desktop actions with safer execution and optional Windows controls."""

from __future__ import annotations

import platform
import time
from pathlib import Path

import pyautogui


class ActionController:
    def __init__(self, config, monitors):
        self.config = config
        self.monitors = monitors
        self.dragging = False
        self.action_log = []
        self.volume_control = None
        self.brightness_module = None
        self._initialize_system_controls()
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

    def _initialize_system_controls(self):
        if platform.system() != "Windows":
            return
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            if hasattr(speakers, "EndpointVolume"):
                self.volume_control = speakers.EndpointVolume
            else:
                from pycaw.pycaw import IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self.volume_control = interface.QueryInterface(IAudioEndpointVolume)
        except Exception as exc:
            print(f"[Warning] Volume control unavailable: {exc}")
        try:
            import screen_brightness_control as sbc
            self.brightness_module = sbc
        except Exception as exc:
            print(f"[Warning] Brightness control unavailable: {exc}")

    def move_mouse(self, x, y):
        screen_w, screen_h = self.monitors.get_size()
        pyautogui.moveTo(
            max(1, min(screen_w - 2, int(x))),
            max(1, min(screen_h - 2, int(y))),
            duration=0,
        )

    def _change_volume(self, amount):
        if self.volume_control is None:
            return "Volume control unavailable"
        try:
            current = self.volume_control.GetMasterVolumeLevelScalar()
            target = max(0.0, min(1.0, current + amount))
            self.volume_control.SetMasterVolumeLevelScalar(target, None)
            return f"Volume {round(target * 100)}%"
        except Exception as exc:
            return f"Volume error: {exc}"

    def set_volume(self, scalar):
        if self.volume_control is None:
            return "Volume control unavailable"
        try:
            scalar = max(0.0, min(1.0, float(scalar)))
            self.volume_control.SetMasterVolumeLevelScalar(scalar, None)
            return f"Volume {round(scalar * 100)}%"
        except Exception as exc:
            return f"Volume error: {exc}"

    def set_brightness(self, percent):
        if self.brightness_module is None:
            return "Brightness control unavailable on this display"
        try:
            value = max(0, min(100, int(percent)))
            self.brightness_module.set_brightness(value)
            return f"Brightness {value}%"
        except Exception as exc:
            return f"Brightness error: {exc}"

    def execute(self, action_name, gesture_data=None):
        """Execute a named action and return a status message."""
        try:
            if action_name in {"move_mouse", "scroll_mode", "brightness_mode"}:
                return f"Continuous control: {action_name}"

            if action_name == "left_click":
                pyautogui.click(button="left")
            elif action_name == "right_click":
                pyautogui.click(button="right")
            elif action_name == "double_click":
                pyautogui.doubleClick()
            elif action_name == "toggle_drag":
                self.dragging = not self.dragging
                if self.dragging:
                    pyautogui.mouseDown(button="left")
                else:
                    pyautogui.mouseUp(button="left")
            elif action_name in {"copy", "paste", "undo", "redo", "select_all"}:
                shortcut = {
                    "copy": ("ctrl", "c"),
                    "paste": ("ctrl", "v"),
                    "undo": ("ctrl", "z"),
                    "redo": ("ctrl", "y"),
                    "select_all": ("ctrl", "a"),
                }[action_name]
                pyautogui.hotkey(*shortcut)
            elif action_name == "new_tab":
                pyautogui.hotkey("ctrl", "t")
            elif action_name == "close_tab":
                pyautogui.hotkey("ctrl", "w")
            elif action_name == "reopen_tab":
                pyautogui.hotkey("ctrl", "shift", "t")
            elif action_name == "next_tab":
                pyautogui.hotkey("ctrl", "tab")
            elif action_name == "previous_tab":
                pyautogui.hotkey("ctrl", "shift", "tab")
            elif action_name == "refresh":
                pyautogui.press("f5")
            elif action_name == "zoom_in":
                pyautogui.hotkey("ctrl", "+")
            elif action_name == "zoom_out":
                pyautogui.hotkey("ctrl", "-")
            elif action_name == "play_pause":
                pyautogui.press("playpause")
            elif action_name == "next_track":
                pyautogui.press("nexttrack")
            elif action_name == "previous_track":
                pyautogui.press("prevtrack")
            elif action_name == "mute":
                pyautogui.press("volumemute")
            elif action_name == "fullscreen":
                pyautogui.press("f")
            elif action_name == "next_slide":
                pyautogui.press("right")
            elif action_name == "previous_slide":
                pyautogui.press("left")
            elif action_name == "start_presentation":
                pyautogui.press("f5")
            elif action_name == "black_screen":
                pyautogui.press("b")
            elif action_name in {"press_w", "jump", "crouch", "interact", "reload", "move_left", "move_right"}:
                key_map = {
                    "press_w": "w", "jump": "space", "crouch": "c",
                    "interact": "e", "reload": "r", "move_left": "left",
                    "move_right": "right",
                }
                pyautogui.press(key_map[action_name])
            elif action_name == "screenshot":
                folder = Path.home() / "Pictures" / "GestureScreenshots"
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / time.strftime("screenshot_%Y%m%d_%H%M%S.png")
                pyautogui.screenshot().save(path)
                return self._log(f"Screenshot saved: {path}")
            elif action_name == "alt_tab":
                pyautogui.hotkey("alt", "tab")
            elif action_name == "show_desktop":
                pyautogui.hotkey("win", "d")
            elif action_name == "task_view":
                pyautogui.hotkey("win", "tab")
            elif action_name == "minimize":
                pyautogui.hotkey("win", "down")
            elif action_name == "maximize":
                pyautogui.hotkey("win", "up")
            elif action_name == "next_desktop":
                pyautogui.hotkey("win", "ctrl", "right")
            elif action_name == "previous_desktop":
                pyautogui.hotkey("win", "ctrl", "left")
            elif action_name == "volume_up":
                return self._log(self._change_volume(0.05))
            elif action_name == "volume_down":
                return self._log(self._change_volume(-0.05))
            elif action_name == "lock_computer":
                if platform.system() == "Windows":
                    pyautogui.hotkey("win", "l")
                else:
                    return self._log("Lock Computer is supported only on Windows")
            else:
                return self._log(f"Unknown action: {action_name}")

            return self._log(f"Executed: {action_name}")
        except pyautogui.FailSafeException:
            self.release_all()
            return self._log("Emergency stop: cursor reached top-left corner")
        except Exception as exc:
            return self._log(f"Action failed ({action_name}): {exc}")

    def _log(self, message):
        self.action_log.append(message)
        self.action_log = self.action_log[-8:]
        print(message)
        return message

    def release_all(self):
        if self.dragging:
            try:
                pyautogui.mouseUp(button="left")
            except Exception:
                pass
            self.dragging = False
        for key in ("ctrl", "alt", "shift", "win", "w", "a", "s", "d", "e", "r", "c"):
            try:
                pyautogui.keyUp(key)
            except Exception:
                pass
