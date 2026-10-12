# AI Hand Gesture Desktop Controller

A modular Windows desktop controller using Python, OpenCV, MediaPipe and PyAutoGUI.

## Features

- Webcam hand tracking with the official MediaPipe Gesture Recognizer model
- Mouse movement, pinch clicks, scroll mode, drag, volume and brightness controls
- Keyboard shortcuts, browser controls, media controls and Windows actions
- Normal, Presentation, Gaming, Browser and Windows modes
- Calibration, on-screen guide, action log and simple macro recording
- Optional system tray menu

## Folder structure

```text
AI Hand Gesture Control System/
├── gesture_controller.py
├── gestures.py
├── actions.py
├── calibration.py
├── feedback.py
├── macros.py
├── monitor.py
├── tray.py
├── config.json
├── requirements.txt
├── requirements-dev.txt
├── gesture.txt
├── GESTURE_GUIDE.txt
├── tests/
│   └── test_helpers.py
├── docs/
└── models/  (the model is downloaded here on first launch)
```

## Requirements

- Windows recommended
- Python 3.12 recommended
- Webcam
- Internet connection on first run to download `gesture_recognizer.task`

## Install

Run these commands from this folder in VS Code Terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you already have a `.venv`, skip the first command.

## Run

```powershell
.\.venv\Scripts\python.exe gesture_controller.py
```

Start in another mode:

```powershell
.\.venv\Scripts\python.exe gesture_controller.py --mode presentation
```

List the configured mappings:

```powershell
.\.venv\Scripts\python.exe gesture_controller.py --list
```

Test the HUD without a webcam:

```powershell
.\.venv\Scripts\python.exe gesture_controller.py --demo
```

## Keyboard controls

- `M`: change mode
- `P`: pause/resume
- `C`: calibrate cursor mapping by moving the hand around the camera area
- `R`: reset calibration
- `H`: toggle HUD
- `G`: toggle gesture guide
- `L`: toggle action log
- `1`: start macro recording
- `2`: stop and save macro recording
- `3`: replay recorded macro
- `S`: save calibration
- `Q`: quit safely

## Notes

- The app starts paused to reduce accidental system actions.
- Media and browser actions are sent to the currently active application. A shortcut can behave differently depending on the app.
- Brightness control depends on monitor hardware/driver support; external monitors may not support it.
- System tray support is optional. If the dependency is unavailable, the main window can still be used.
- Hand gesture recognition is probabilistic; keep your hand well lit and fully visible.
- Do not test actions like closing tabs or deleting content in important windows until you understand the assigned gesture.
