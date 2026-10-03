# CV-BN Screen Translator

CV-BN lets you select text anywhere on your screen, recognize it with Tesseract OCR, and translate it with Argos Translate. Press C, V, B, and N together or use the button, drag over the text, then review or copy the result.

Translation runs on your computer. CV-BN does not use Google Translate, require an API key, or require a payment card. On the first use of a language pair, it downloads the required open Argos model package or packages. After that download, translation works offline and the recognized text stays on your computer.

## Requirements

- Python 3.10 or newer with Tkinter
- Python packages from requirements.txt
- Tesseract OCR installed on the computer
- An internet connection for the initial language model download

Argos language models can take significant disk space; the Argos documentation says model packages average around 100 MB. The exact download depends on the language pair and may involve more than one package when translation uses an intermediate language.

## Install

Install the Python packages with:

    python -m pip install -r requirements.txt

Install Tesseract separately and make its executable available on PATH. If it is not on PATH, provide its full path with --tesseract-cmd. Install the matching Tesseract language data for the selected OCR language.

## Run

    python main.py

The default target is Turkish, and the source language is detected locally. Automatic detection may be unreliable for a short selection; choose a source language code if needed:

    python main.py --source en --target tr --ocr-language eng

For example, recognize German text and translate it into English:

    python main.py --source de --target en --ocr-language deu

Use Argos Translate language codes for --source and --target. The OCR language is a Tesseract language code, which may differ from the translation code.

The first translation for a language pair can take longer while CV-BN downloads and installs its model package or packages. Later translations use the installed models locally. Repeated identical OCR text is cached for the current app session.

## Files

- main.py starts the app and coordinates screen selection, OCR, and translation.
- region_selector.py captures all connected displays and lets the user drag a selection.
- translation.py runs OCR, detects the source language locally, installs missing Argos models, and translates locally.
- translation_window.py displays and copies the result.

Project links: [Argos Translate](https://github.com/argosopentech/argos-translate) and [Argos model documentation](https://github.com/argosopentech/argos-translate/blob/master/docs/source/gui.rst).
