# Setup notes

1. Open this folder in VS Code.
2. Run `py -3.12 -m venv .venv` if a virtual environment does not already exist.
3. Run `\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
4. Run `\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
5. Run `\.venv\Scripts\python.exe gesture_controller.py`.

The controller starts paused. Focus the webcam window and press `P` to resume.
Press `Q` to quit. Keep important documents unsaved while testing actions.
