# CV-BN lets you select text on screen and view an OCR-based translation.
import argparse
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from pynput import keyboard

from region_selector import RegionSelector, capture_all_screens
from translation import translate_region
from translation_window import TranslationWindow


class ScreenTranslatorApp:
    def __init__(
        self,
        root,
        source_language,
        target_language,
        ocr_language,
        tesseract_cmd,
    ):
        self.root = root
        self.source_language = source_language
        self.target_language = target_language
        self.ocr_language = ocr_language
        self.tesseract_cmd = tesseract_cmd
        self.messages = queue.Queue()
        self.selector = None
        self.listener = None
        self.pressed_keys = set()
        self.chord_active = False

        root.title("CV-BN Screen Translator")
        root.geometry("470x260")
        root.minsize(400, 230)
        root.configure(bg="#f3f5f8")
        root.protocol("WM_DELETE_WINDOW", self.close)

        heading = ttk.Label(root, text="CV-BN Screen Translator", font=("Segoe UI", 18, "bold"))
        heading.pack(anchor="w", padx=24, pady=(22, 4))

        description = ttk.Label(
            root,
            text="Select a region of your screen to read and translate its text.",
            wraplength=410,
        )
        description.pack(anchor="w", padx=24, pady=(0, 16))

        hotkey = ttk.Label(root, text="Shortcut: press C, V, B and N together")
        hotkey.pack(anchor="w", padx=24)

        controls = ttk.Frame(root)
        controls.pack(anchor="w", padx=24, pady=16)
        ttk.Button(controls, text="Select a screen region", command=self.start_capture).pack(side="left")

        self.status = tk.StringVar(value=f"Listening: {source_language} to {target_language}")
        ttk.Label(root, textvariable=self.status, wraplength=410).pack(anchor="w", padx=24, pady=(0, 16))

        self.root.after(100, self.process_messages)
        self.start_listener()

    def start_listener(self):
        try:
            self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.listener.start()
        except Exception as error:
            self.status.set(f"Keyboard shortcut unavailable: {error}")

    def on_key_press(self, key):
        try:
            character = key.char.casefold()
        except (AttributeError, TypeError):
            return

        if character in {"c", "v", "b", "n"}:
            self.pressed_keys.add(character)
            if len(self.pressed_keys) == 4 and not self.chord_active:
                self.chord_active = True
                self.messages.put(("capture", None))

    def on_key_release(self, key):
        try:
            character = key.char.casefold()
        except (AttributeError, TypeError):
            return

        if character in {"c", "v", "b", "n"}:
            self.pressed_keys.discard(character)
            if len(self.pressed_keys) < 4:
                self.chord_active = False

    def start_capture(self):
        if self.selector is not None:
            return

        try:
            screens = capture_all_screens()
        except Exception as error:
            messagebox.showerror("Screen capture failed", str(error), parent=self.root)
            return

        self.status.set("Drag on any display to select text. Press Escape to cancel.")
        self.selector = RegionSelector(self.root, screens, self.region_selected)

    def region_selected(self, image):
        self.selector = None
        if image is None:
            self.status.set("Selection cancelled.")
            return

        self.status.set("Reading text and preparing the offline translation...")
        worker = threading.Thread(target=self.translate_in_background, args=(image,), daemon=True)
        worker.start()

    def translate_in_background(self, image):
        try:
            original, translated = translate_region(
                image,
                self.source_language,
                self.target_language,
                self.ocr_language,
                self.tesseract_cmd,
            )
            self.messages.put(("result", (original, translated)))
        except Exception as error:
            self.messages.put(("error", str(error)))

    def process_messages(self):
        while True:
            try:
                message_type, payload = self.messages.get_nowait()
            except queue.Empty:
                break

            if message_type == "capture":
                self.start_capture()
            elif message_type == "result":
                self.status.set("Translation ready.")
                original, translated = payload
                TranslationWindow(self.root, original, translated)
            elif message_type == "error":
                self.status.set("Translation failed.")
                messagebox.showerror("Translation failed", payload, parent=self.root)

        self.root.after(100, self.process_messages)

    def close(self):
        if self.listener is not None:
            self.listener.stop()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Translate text selected from the screen.")
    parser.add_argument("--source", default="auto", help="source language code, or auto")
    parser.add_argument("--target", default="tr", help="target language code")
    parser.add_argument("--ocr-language", default="eng", help="Tesseract language code")
    parser.add_argument("--tesseract-cmd", help="path to the Tesseract executable")
    args = parser.parse_args()

    root = tk.Tk()
    ScreenTranslatorApp(
        root,
        args.source,
        args.target,
        args.ocr_language,
        args.tesseract_cmd,
    )
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
