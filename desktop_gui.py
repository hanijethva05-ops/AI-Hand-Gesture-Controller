"""Desktop GUI for AI Hand Gesture Controller. Run: python desktop_gui.py"""

import ctypes
import json
import platform
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
import pyautogui
from PIL import Image, ImageTk

from actions import ActionController
from calibration import CalibrationManager
from gestures import GestureEngine
from monitor import MonitorManager

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.json"
BG, PANEL, TEXT, MUTED = "#0D1117", "#161B22", "#E6EDF3", "#9AA8B8"
BLUE, GREEN, RED = "#4285F4", "#3FB950", "#F85149"


def read_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config.get("modes"), dict):
        raise ValueError("config.json needs a 'modes' object.")
    return config


def save_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


class DesktopGUI:
    def __init__(self, root):
        self.root = root
        root.title("AI Hand Gesture Controller")
        root.geometry("1200x780")
        root.minsize(950, 630)
        root.configure(bg=BG)
        self.config = read_config()
        self.modes = list(self.config["modes"])

        self.mode = tk.StringVar(value=self.modes[0])
        self.status = tk.StringVar(value="Ready — press Start Controller")
        self.gesture_text = tk.StringVar(value="Gesture: —")
        self.confidence_text = tk.StringVar(value="Confidence: —")
        self.fps_text = tk.StringVar(value="FPS: —")
        self.action_text = tk.StringVar(value="Last action: —")
        self.threshold = tk.DoubleVar(value=float(self.config.get("confidence_threshold", 0.60)))
        self.hold = tk.DoubleVar(value=float(self.config.get("gesture_hold_seconds", 0.35)))
        self.cooldown = tk.DoubleVar(value=float(self.config.get("action_cooldown_seconds", 0.80)))

        self.camera = self.engine = self.actions = self.monitor = self.calibration = None
        self.running = False
        self.paused = True
        self.photo = None
        self.fps = 0.0
        self.last_frame = time.monotonic()
        self.pending_gesture = None
        self.pending_since = 0.0
        self.last_action_time = 0.0
        self.action_latched = False
        self.neutral_since = time.monotonic()
        self.previous_y = None
        self.last_scroll = 0.0
        self.last_brightness = 0.0
        self.last_external_hwnd = None

        self._style()
        self._layout()
        self.refresh_guide()
        root.bind("<KeyPress>", self._on_key)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_foreground()

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 20))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=7)
        style.configure("Primary.TButton", background=BLUE, foreground="white")
        style.configure("Treeview", background="#202938", fieldbackground="#202938", foreground=TEXT, rowheight=25)
        style.configure("Treeview.Heading", background=PANEL, foreground=TEXT)
        style.configure("TCombobox", fieldbackground="#202938", background="#202938", foreground=TEXT)

    def _layout(self):
        header = ttk.Frame(self.root, padding=(20, 15, 20, 12))
        header.pack(fill="x")
        ttk.Label(header, text="AI Hand Gesture Controller", style="Title.TLabel").pack(side="left")
        self.badge = tk.Label(header, text="● STOPPED", bg=BG, fg=RED, font=("Segoe UI Semibold", 10))
        self.badge.pack(side="right")

        bar = ttk.Frame(self.root, padding=(20, 0, 20, 12))
        bar.pack(fill="x")
        ttk.Label(bar, text="Mode:").pack(side="left", padx=(0, 7))
        combo = ttk.Combobox(bar, textvariable=self.mode, values=self.modes, state="readonly", width=15)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.change_mode)
        self.start_btn = ttk.Button(bar, text="▶ Start", style="Primary.TButton", command=self.start)
        self.start_btn.pack(side="left", padx=(12, 5))
        self.pause_btn = ttk.Button(bar, text="▶ Resume", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(bar, text="■ Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        self.cal_btn = ttk.Button(bar, text="◎ Calibrate", command=self.calibrate, state="disabled")
        self.cal_btn.pack(side="left", padx=5)

        body = ttk.Frame(self.root, padding=(20, 0, 20, 12))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame", padding=12)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = ttk.Frame(body, style="Panel.TFrame", padding=12, width=360)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        ttk.Label(left, text="LIVE CAMERA PREVIEW", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(0, 8))
        self.preview = tk.Label(left, text="Camera preview appears here\n\nPress Start", bg="#080B10", fg=MUTED, font=("Segoe UI", 12))
        self.preview.pack(fill="both", expand=True)
        row = ttk.Frame(left, style="Panel.TFrame")
        row.pack(fill="x", pady=(10, 0))
        ttk.Label(row, textvariable=self.gesture_text, style="Muted.TLabel").pack(side="left", padx=(0, 12))
        ttk.Label(row, textvariable=self.confidence_text, style="Muted.TLabel").pack(side="left")
        ttk.Label(row, textvariable=self.fps_text, style="Muted.TLabel").pack(side="right")
        ttk.Label(left, textvariable=self.action_text, style="Muted.TLabel").pack(anchor="w", pady=(7, 0))

        ttk.Label(right, text="GESTURE GUIDE", style="Panel.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        ttk.Label(right, text="Mappings for the selected mode", style="Muted.TLabel").pack(anchor="w", pady=(4, 8))
        table = ttk.Frame(right, style="Panel.TFrame")
        table.pack(fill="both", expand=True)
        self.guide = ttk.Treeview(table, columns=("gesture", "action"), show="headings", height=9)
        self.guide.heading("gesture", text="Gesture")
        self.guide.heading("action", text="Action")
        self.guide.column("gesture", width=135)
        self.guide.column("action", width=155)
        bar = ttk.Scrollbar(table, orient="vertical", command=self.guide.yview)
        self.guide.configure(yscrollcommand=bar.set)
        self.guide.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        settings = ttk.LabelFrame(right, text="Settings", padding=8)
        settings.pack(fill="x", pady=(12, 0))
        self._add_slider(settings, "Confidence threshold", self.threshold, 0.50, 0.95)
        self._add_slider(settings, "Gesture hold (seconds)", self.hold, 0.20, 1.50)
        self._add_slider(settings, "Action cooldown (seconds)", self.cooldown, 0.40, 2.00)
        ttk.Button(settings, text="Save settings", command=self.save_settings).pack(anchor="e", pady=(6, 0))

        footer = ttk.Frame(self.root, padding=(20, 0, 20, 12))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel").pack(side="left", fill="x", expand=True)
        ttk.Label(footer, text="M: mode  •  P: pause  •  Q: stop", style="Muted.TLabel").pack(side="right")

    def _add_slider(self, parent, title, variable, minimum, maximum):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        label = ttk.Label(row, text=f"{title}: {variable.get():.2f}")
        label.pack(anchor="w")
        ttk.Scale(row, from_=minimum, to=maximum, variable=variable, orient="horizontal",
                  command=lambda _v, v=variable, out=label, name=title: out.configure(text=f"{name}: {v.get():.2f}")).pack(fill="x")

    def refresh_guide(self):
        for item in self.guide.get_children():
            self.guide.delete(item)
        for gesture, action in self.config["modes"].get(self.mode.get(), {}).items():
            self.guide.insert("", "end", values=(gesture.replace("_", " ").title(), action.replace("_", " ").title()))

    def start(self):
        if self.running:
            return
        try:
            self.status.set("Starting gesture model and camera…")
            self.root.update_idletasks()
            self.engine = GestureEngine(self.config)
            self.monitor = MonitorManager()
            self.actions = ActionController(self.config, self.monitor)
            self.calibration = CalibrationManager(CONFIG_PATH)
            camera_id = int(self.config.get("camera_index", 0))
            self.camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW) if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(camera_id)
            if not self.camera.isOpened():
                self.camera.release()
                self.camera = cv2.VideoCapture(camera_id)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.config.get("camera_width", 640)))
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.config.get("camera_height", 480)))
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.camera.isOpened():
                raise RuntimeError("Webcam did not open. Check permissions or camera index.")
        except Exception as exc:
            self._release_resources()
            messagebox.showerror("Could not start", str(exc))
            self.status.set("Start failed — see error message")
            return

        self.running = True
        self.paused = True
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="▶ Resume")
        self.stop_btn.configure(state="normal")
        self.cal_btn.configure(state="normal")
        self.badge.configure(text="● PAUSED", fg="#F0B429")
        self.status.set("Controller is paused. Press Resume to enable gestures.")
        self.pending_gesture = None
        self.action_latched = False
        self._tick()

    def _tick(self):
        if not self.running:
            return
        try:
            ok, frame = self.camera.read()
            if not ok:
                self.status.set("Waiting for webcam frame…")
                self.root.after(40, self._tick)
                return
            frame = cv2.flip(frame, 1)
            now = time.monotonic()
            dt = now - self.last_frame
            self.last_frame = now
            if dt > 0:
                measured = 1.0 / dt
                self.fps = measured if not self.fps else 0.85 * self.fps + 0.15 * measured

            data = None if self.paused else self.engine.process(frame)
            gesture = data.get("gesture", "none") if data else "none"
            confidence = float(data.get("confidence", 0.0)) if data else 0.0
            landmarks = data.get("landmarks") if data else None
            cursor = data.get("cursor") if data else None
            calibrating = bool(self.calibration and self.calibration.is_calibrating)
            if landmarks:
                self.engine.draw_landmarks(frame, landmarks)
                if calibrating:
                    self.calibration.update(data)
                    self.status.set(self.calibration.status_message)

            mapping = self.config["modes"].get(self.mode.get(), {})
            valid = bool(data and confidence >= float(self.threshold.get()) and gesture not in set(self.config.get("disabled_gestures", [])))
            action = mapping.get(gesture) if valid and not self.paused and not calibrating else None
            self._process_action(action, gesture, data, now)

            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], 98), (16, 22, 31), -1)
            cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
            messages = [
                ("PAUSED" if self.paused else f"MODE: {self.mode.get().upper()}", (100, 240, 140)),
                (f"Gesture: {gesture}", (0, 225, 255)),
                (f"Action: {self.action_text.get().replace('Last action: ', '')[:34]}", (255, 210, 90)),
                (f"FPS: {self.fps:.0f}  Confidence: {confidence:.0%}", (230, 230, 230)),
            ]
            for line, (text, color) in enumerate(messages):
                cv2.putText(frame, text, (12, 22 + 23 * line), cv2.FONT_HERSHEY_SIMPLEX, 0.44, color, 1, cv2.LINE_AA)

            self.gesture_text.set(f"Gesture: {gesture}")
            self.confidence_text.set(f"Confidence: {confidence:.0%}")
            self.fps_text.set(f"FPS: {self.fps:.0f}")
            self.badge.configure(text="● PAUSED" if self.paused else "● RUNNING", fg="#F0B429" if self.paused else GREEN)
            self._display_frame(frame)
            self.root.after(12, self._tick)
        except pyautogui.FailSafeException:
            self.status.set("Safety stop: cursor reached top-left corner")
            self.stop()
        except Exception as exc:
            self.stop()
            messagebox.showerror("Controller error", str(exc))
            self.status.set(f"Stopped: {exc}")

    def _process_action(self, action, gesture, data, now):
        if self.paused or not action:
            self.pending_gesture = None
            self.pending_since = now
            if self.neutral_since is None:
                self.neutral_since = now
            elif now - self.neutral_since >= float(self.config.get("neutral_release_seconds", 0.5)):
                self.action_latched = False
            self.previous_y = None
            return

        self.neutral_since = None
        cursor = data.get("cursor") if data else None
        if action == "move_mouse" and cursor:
            x_norm, y_norm = self.calibration.map_point(*cursor)
            x, y = self.monitor.map_to_screen(x_norm, y_norm)
            self.actions.move_mouse(x, y)
            self.action_text.set("Last action: Moving mouse")
            self.action_latched = False
            return
        if action == "scroll_mode" and cursor:
            if self.previous_y is not None and now - self.last_scroll >= 0.12:
                change = cursor[1] - self.previous_y
                if abs(change) >= 0.025:
                    pyautogui.scroll(1 if change < 0 else -1)
                    self.last_scroll = now
            self.previous_y = cursor[1]
            self.action_text.set("Last action: Scroll control")
            self.action_latched = False
            return
        if action == "brightness_mode" and cursor:
            if now - self.last_brightness >= 0.35:
                value = int(max(0, min(100, (1.0 - cursor[1]) * 100)))
                result = self.actions.set_brightness(value)
                self.action_text.set(f"Last action: {result}")
                self.last_brightness = now
            self.action_latched = False
            return

        if gesture != self.pending_gesture:
            self.pending_gesture = gesture
            self.pending_since = now
            self.action_latched = False
        hold = float(self.hold.get())
        if action in {"copy", "paste", "undo", "redo", "close_tab", "screenshot", "show_desktop", "task_view"}:
            hold = max(hold, 0.75)
        if not self.action_latched and now - self.pending_since >= hold and now - self.last_action_time >= float(self.cooldown.get()):
            result = self.actions.execute(action, data)
            self.action_text.set(f"Last action: {result}")
            self.status.set(result)
            self.last_action_time = now
            self.action_latched = True

    def _display_frame(self, frame):
        box_w, box_h = max(320, self.preview.winfo_width()), max(240, self.preview.winfo_height())
        height, width = frame.shape[:2]
        scale = min(box_w / width, box_h / height, 1.0)
        frame = cv2.resize(frame, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.preview.configure(image=self.photo, text="")

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        self.actions.release_all()
        self.pending_gesture = None
        self.action_latched = False
        self.neutral_since = time.monotonic()
        self.pause_btn.configure(text="▶ Resume" if self.paused else "Ⅱ Pause")
        self.status.set("Paused" if self.paused else "Gesture control active")
        if not self.paused:
            self.root.after(180, self._restore_focus)

    def change_mode(self, _event=None):
        self.refresh_guide()
        self.pending_gesture = None
        self.action_latched = False
        if self.actions:
            self.actions.release_all()
        self.status.set(f"Selected mode: {self.mode.get().title()}")
        if self.running and not self.paused:
            self.root.after(180, self._restore_focus)

    def calibrate(self):
        if self.running and self.calibration:
            self.calibration.start()
            self.status.set("Calibration started — move your hand around the camera frame")
            if not self.paused:
                self.root.after(180, self._restore_focus)

    def reset_calibration(self):
        if self.calibration:
            self.calibration.reset()
        else:
            path = ROOT_DIR / "calibration.json"
            if path.exists():
                path.unlink()
        self.status.set("Calibration reset")

    def save_settings(self):
        self.config["confidence_threshold"] = float(self.threshold.get())
        self.config["gesture_hold_seconds"] = float(self.hold.get())
        self.config["action_cooldown_seconds"] = float(self.cooldown.get())
        try:
            save_config(self.config)
            self.status.set("Settings saved to config.json")
        except OSError as exc:
            messagebox.showerror("Settings error", str(exc))

    def _on_key(self, event):
        key = event.keysym.lower()
        if key == "m":
            index = self.modes.index(self.mode.get())
            self.mode.set(self.modes[(index + 1) % len(self.modes)])
            self.change_mode()
        elif key == "p":
            self.toggle_pause()
        elif key == "q":
            self.stop()

    def _poll_foreground(self):
        if platform.system() == "Windows":
            try:
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                root_hwnd = user32.GetAncestor(self.root.winfo_id(), 2)
                if hwnd and user32.GetAncestor(hwnd, 2) != root_hwnd:
                    self.last_external_hwnd = hwnd
            except Exception:
                pass
        self.root.after(250, self._poll_foreground)

    def _restore_focus(self):
        if platform.system() == "Windows" and self.last_external_hwnd:
            try:
                ctypes.windll.user32.SetForegroundWindow(self.last_external_hwnd)
            except Exception:
                pass

    def stop(self):
        self.running = False
        self._release_resources()
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled", text="▶ Resume")
        self.stop_btn.configure(state="disabled")
        self.cal_btn.configure(state="disabled")
        self.badge.configure(text="● STOPPED", fg=RED)
        self.preview.configure(image="", text="Camera stopped\n\nPress Start")
        self.photo = None
        self.status.set("Controller stopped safely")

    def _release_resources(self):
        if self.actions:
            try:
                self.actions.release_all()
            except Exception:
                pass
        if self.camera:
            self.camera.release()
            self.camera = None
        if self.engine:
            self.engine.close()
            self.engine = None
        self.actions = self.monitor = self.calibration = None

    def close(self):
        if self.running:
            self.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        DesktopGUI(root)
    except Exception as exc:
        messagebox.showerror("Startup error", str(exc))
        root.destroy()
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
