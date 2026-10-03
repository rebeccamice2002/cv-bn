import tkinter as tk
from tkinter import ttk


class TranslationWindow:
    def __init__(self, parent, original_text, translated_text):
        self.parent = parent
        self.translated_text = translated_text
        self.window = tk.Toplevel(parent)
        self.window.title("Selected text translation")
        self.window.geometry("680x520")
        self.window.minsize(420, 320)
        self.window.transient(parent)

        container = ttk.Frame(self.window, padding=16)
        container.pack(fill="both", expand=True)
        container.rowconfigure(1, weight=1)
        container.rowconfigure(3, weight=2)
        container.columnconfigure(0, weight=1)

        ttk.Label(container, text="Recognized text").grid(row=0, column=0, sticky="w", pady=(0, 6))
        original = tk.Text(container, height=5, wrap="word")
        original.grid(row=1, column=0, sticky="nsew", pady=(0, 14))
        original.insert("1.0", original_text)
        original.configure(state="disabled")

        ttk.Label(container, text="Translation").grid(row=2, column=0, sticky="w", pady=(0, 6))
        translated = tk.Text(container, height=9, wrap="word")
        translated.grid(row=3, column=0, sticky="nsew")
        translated.insert("1.0", translated_text)
        translated.configure(state="disabled")

        controls = ttk.Frame(container)
        controls.grid(row=4, column=0, sticky="e", pady=(12, 0))
        ttk.Button(controls, text="Copy translation", command=self.copy_translation).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Close", command=self.window.destroy).pack(side="left")

    def copy_translation(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.translated_text)
        self.parent.update()
