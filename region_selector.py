import ctypes
import sys
import tkinter as tk

from mss import mss
from PIL import Image


def _enable_windows_dpi_awareness():
    if sys.platform != "win32":
        return

    try:
        set_awareness = ctypes.windll.user32.SetProcessDpiAwarenessContext
        if set_awareness(ctypes.c_void_p(-4)):
            return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


_enable_windows_dpi_awareness()


def capture_all_screens():
    with mss() as capture:
        monitors = [monitor.copy() for monitor in capture.monitors[1:]]
        screens = []
        for monitor in monitors:
            shot = capture.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            screens.append((monitor, image))

    if not screens:
        raise RuntimeError("No screen monitor is available for capture.")
    return screens


class RegionSelector:
    def __init__(self, parent, screens, on_complete):
        self.parent = parent
        self.screens = screens
        self.on_complete = on_complete
        self.start_point = None
        self.rectangle = None
        self.active_canvas = None
        self.active_image = None
        self.windows = []
        self.completed = False

        for monitor, screen_image in screens:
            self._create_overlay(monitor, screen_image)

    def _position_window(self, window, monitor):
        left = int(monitor["left"])
        top = int(monitor["top"])
        width = int(monitor["width"])
        height = int(monitor["height"])

        if sys.platform == "win32":
            window.geometry(f"{width}x{height}+0+0")
            window.update_idletasks()

            from ctypes import wintypes

            set_window_pos = ctypes.windll.user32.SetWindowPos
            set_window_pos.argtypes = (
                wintypes.HWND,
                wintypes.HWND,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.UINT,
            )
            set_window_pos.restype = wintypes.BOOL
            positioned = set_window_pos(
                wintypes.HWND(window.winfo_id()),
                wintypes.HWND(-1),
                left,
                top,
                width,
                height,
                0x0040,
            )
            if not positioned:
                raise ctypes.WinError()
        else:
            window.geometry(f"{width}x{height}{left:+d}{top:+d}")
            window.update_idletasks()

    def _create_overlay(self, monitor, screen_image):
        window = tk.Toplevel(self.parent)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        try:
            window.attributes("-alpha", 0.28)
        except tk.TclError:
            pass

        canvas = tk.Canvas(window, bg="#101722", highlightthickness=0, cursor="crosshair")
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            24,
            24,
            anchor="nw",
            text="Drag to select text | Escape to cancel",
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )
        canvas.bind(
            "<ButtonPress-1>",
            lambda event, target=canvas, image=screen_image: self.start_selection(
                event, target, image
            ),
        )
        canvas.bind("<B1-Motion>", self.update_selection)
        canvas.bind(
            "<ButtonRelease-1>",
            lambda event, target=canvas, image=screen_image: self.finish_selection(
                event, target, image
            ),
        )
        window.bind("<Escape>", self.cancel)
        self.windows.append(window)
        self._position_window(window, monitor)
        window.lift()
        window.focus_force()
        canvas.focus_set()

    def start_selection(self, event, canvas, screen_image):
        if self.completed:
            return

        self.active_canvas = canvas
        self.active_image = screen_image
        self.start_point = (event.x, event.y)
        self.rectangle = canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#27d7a1",
            width=3,
        )

    def update_selection(self, event):
        if (
            self.rectangle is not None
            and self.start_point is not None
            and self.active_canvas is not None
        ):
            self.active_canvas.coords(
                self.rectangle,
                self.start_point[0],
                self.start_point[1],
                event.x,
                event.y,
            )

    def finish_selection(self, event, canvas, screen_image):
        if self.start_point is None or canvas is not self.active_canvas:
            return

        x1, y1 = self.start_point
        x2, y2 = event.x, event.y
        scale_x = screen_image.width / max(canvas.winfo_width(), 1)
        scale_y = screen_image.height / max(canvas.winfo_height(), 1)
        left = max(0, round(min(x1, x2) * scale_x))
        top = max(0, round(min(y1, y2) * scale_y))
        right = min(screen_image.width, round(max(x1, x2) * scale_x))
        bottom = min(screen_image.height, round(max(y1, y2) * scale_y))

        if right <= left or bottom <= top:
            self._complete(None)
            return
        self._complete(screen_image.crop((left, top, right, bottom)))

    def _complete(self, selection):
        if self.completed:
            return
        self.completed = True
        for window in self.windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.windows.clear()
        self.on_complete(selection)

    def cancel(self, event=None):
        self._complete(None)
        return "break"
