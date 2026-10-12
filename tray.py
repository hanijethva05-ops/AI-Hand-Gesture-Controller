"""Optional Windows system tray controller. Safe to omit if pystray is unavailable."""

import threading


def start_system_tray(shared_state):
    """Start a small tray icon in a daemon thread; returns None when unsupported."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as exc:
        print(f"[Info] System tray disabled (optional dependency): {exc}")
        return None

    image = Image.new("RGB", (64, 64), (28, 31, 42))
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 12, 52, 52), fill=(75, 150, 240))
    draw.ellipse((23, 22, 29, 28), fill=(255, 255, 255))
    draw.ellipse((36, 22, 42, 28), fill=(255, 255, 255))
    draw.arc((22, 24, 42, 43), 10, 170, fill=(255, 255, 255), width=3)

    def toggle_pause(icon, item):
        shared_state["pause_toggle"] = not shared_state.get("pause_toggle", False)

    def quit_app(icon, item):
        shared_state["quit"] = True
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Toggle pause", toggle_pause),
        pystray.MenuItem("Quit controller", quit_app),
    )
    icon = pystray.Icon("AIHandGestureController", image, "AI Hand Gesture Controller", menu)
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
    return icon
