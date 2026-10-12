"""Small action macro recorder and player."""

import json
import time
from pathlib import Path


class MacroManager:
    def __init__(self, config):
        self.config = config
        self.path = Path(__file__).resolve().parent / "macros.json"
        self.recording = False
        self.events = []
        self.started_at = 0.0
        self.last_message = "No macro recorded"
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.events = data
            except (OSError, json.JSONDecodeError):
                self.events = []

    def start_recording(self):
        self.events = []
        self.recording = True
        self.started_at = time.monotonic()
        self.last_message = "Macro recording started"

    def stop_recording(self):
        self.recording = False
        try:
            self.path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
            self.last_message = f"Saved {len(self.events)} macro events"
        except OSError as exc:
            self.last_message = f"Could not save macro: {exc}"
        return self.last_message

    def record_action(self, action_name):
        if self.recording:
            elapsed = time.monotonic() - self.started_at
            self.events.append({"at": round(elapsed, 3), "action": str(action_name)})

    def play(self, actions):
        if self.recording:
            return "Stop recording before playing a macro"
        if not self.events:
            return "No recorded macro. Press 1 to record first."
        previous = 0.0
        for event in self.events:
            target = float(event.get("at", previous))
            time.sleep(max(0.0, min(2.0, target - previous)))
            message = actions.execute(str(event.get("action", "")))
            previous = target
        return f"Macro played ({len(self.events)} events)"
