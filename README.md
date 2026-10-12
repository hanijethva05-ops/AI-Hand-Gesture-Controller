
# 🖐️ AI Hand Gesture Control System

A Python-based desktop controller that uses hand gestures to interact with your computer through a webcam.

The project uses MediaPipe, OpenCV, and PyAutoGUI to recognize gestures and connect them to desktop actions.

## ✨ Features

- Real-time hand landmark tracking
- Mouse cursor control and pinch-based clicking
- Gesture-based keyboard shortcuts
- Browser and media controls
- Windows desktop shortcuts
- Multiple control modes
- On-screen gesture guide and status display
- Cursor calibration
- Optional macro recording
- Screenshot capture

## 🛠️ Technologies

- Python
- MediaPipe
- OpenCV
- PyAutoGUI
- NumPy
- PyCAW
- Screen Brightness Control

## 📁 Project Structure

```text
AI_Hand_Gesture_Controller/
├── gesture_controller.py
├── gestures.py
├── gesture_helpers.py
├── actions.py
├── calibration.py
├── feedback.py
├── macros.py
├── monitor.py
├── tray.py
├── config.json
├── requirements.txt
├── requirements-dev.txt
├── tests/
├── docs/
└── README.md
```

## 💻 Requirements

- Windows recommended
- Python 3.12 recommended
- A working webcam
- Internet access for the initial gesture model download

## 🚀 Installation

Clone this repository:

```bash
git clone https://github.com/hanijethva05-ops/AI-Hand-Gesture-Controller.git
cd AI-Hand-Gesture-Controller
```

Create a virtual environment:

```bash
py -3.12 -m venv .venv
```

Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## ▶️ Run the Controller

```powershell
.\.venv\Scripts\python.exe gesture_controller.py
```

The controller starts paused for safety. Focus the webcam window and press `P` to resume gesture actions.

## ⌨️ Keyboard Controls

| Key | Action |
|---|---|
| `M` | Switch control mode |
| `P` | Pause or resume |
| `C` | Start calibration |
| `R` | Reset calibration |
| `H` | Toggle HUD |
| `G` | Toggle gesture guide |
| `L` | Toggle action log |
| `1` | Start macro recording |
| `2` | Stop and save macro |
| `3` | Play recorded macro |
| `S` | Save calibration |
| `Q` | Quit the controller |

## 🔒 Safety Notes

- Test new gestures in a safe environment.
- Desktop shortcuts can affect the currently active application.
- Keep a backup of important files before testing keyboard or mouse automation.
- Do not commit passwords, API keys, or private configuration data.

## 👩‍💻 Author

Created as a Python desktop automation and computer-vision project.
