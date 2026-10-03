from collections import OrderedDict, deque
import threading

import argostranslate.package as argos_package
import argostranslate.translate as argos_translate
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from PIL import ImageOps
import pytesseract


MAX_CACHED_TRANSLATIONS = 128
_translation_cache = OrderedDict()
_cache_lock = threading.Lock()
_model_lock = threading.Lock()


def _normalize_language_code(language_code):
    code = language_code.strip().casefold().replace("_", "-")
    if code in {"", "auto"}:
        return code

    aliases = {
        "zh-cn": "zh",
        "zh-tw": "zh",
        "iw": "he",
        "in": "id",
        "ji": "yi",
    }
    return aliases.get(code, code.split("-", 1)[0])


def _resolve_source_language(text, source_language):
    source = _normalize_language_code(source_language)
    if source and source != "auto":
        return source

    try:
        return _normalize_language_code(detect(text))
    except LangDetectException as error:
        raise ValueError(
            "Could not detect the source language from this selection. "
            "Try again with a larger text selection or start CV-BN with --source and a language code."
        ) from error


def _find_path(edges, source, target):
    if source == target:
        return []

    graph = {}
    for from_code, to_code, package in edges:
        graph.setdefault(from_code, []).append((to_code, package))

    queue = deque([source])
    previous = {source: None}
    previous_edge = {}

    while queue:
        current = queue.popleft()
        for next_code, package in graph.get(current, ()):
            if next_code in previous:
                continue
            previous[next_code] = current
            previous_edge[next_code] = (current, next_code, package)
            if next_code == target:
                queue.clear()
                break
            queue.append(next_code)

    if target not in previous:
        return None

    path = []
    current = target
    while current != source:
        path.append(previous_edge[current])
        current = previous[current]
    path.reverse()
    return path


def _installed_edges():
    edges = []
    for language in argos_translate.get_installed_languages():
        translations = getattr(language, "translations_from", None)
        if translations is None:
            translations = getattr(language, "translations", ())

        for translation in translations:
            target_language = getattr(translation, "to_lang", None)
            if target_language is not None:
                edges.append((language.code, target_language.code, translation))
    return edges


def _available_edges(packages):
    edges = []
    for model in packages:
        model_type = getattr(model, "type", "translate")
        if model_type not in (None, "translate"):
            continue
        from_code = getattr(model, "from_code", None)
        to_code = getattr(model, "to_code", None)
        if from_code and to_code:
            edges.append((from_code, to_code, model))
    return edges


def _ensure_translation_models(source_language, target_language):
    with _model_lock:
        installed_path = _find_path(
            _installed_edges(),
            source_language,
            target_language,
        )
        if installed_path is not None:
            return

        try:
            argos_package.update_package_index()
            available_packages = argos_package.get_available_packages()
        except Exception as error:
            raise RuntimeError(
                "CV-BN needs to download an Argos language model for this language pair, "
                "but could not reach the Argos package index. Check your internet connection "
                f"and try again. Details: {error}"
            ) from error

        model_path = _find_path(
            _available_edges(available_packages),
            source_language,
            target_language,
        )
        if model_path is None:
            raise RuntimeError(
                f"No Argos Translate model route is available from '{source_language}' "
                f"to '{target_language}'. Try another source or target language code."
            )

        for from_code, to_code, model in model_path:
            try:
                downloaded_model = model.download()
                argos_package.install_from_path(downloaded_model)
            except Exception as error:
                raise RuntimeError(
                    f"Could not download or install the Argos model for "
                    f"{from_code} to {to_code}. Check your internet connection and free disk space. "
                    f"Details: {error}"
                ) from error

        if _find_path(
            _installed_edges(),
            source_language,
            target_language,
        ) is None:
            raise RuntimeError(
                "The Argos language model finished installing, but the translation route "
                "is still unavailable. Restart CV-BN and try again."
            )


def translate_text(text, source_language, target_language):
    source = _resolve_source_language(text, source_language)
    target = _normalize_language_code(target_language)
    if not target or target == "auto":
        raise ValueError("Choose a target language code, such as 'tr' for Turkish.")

    if source == target:
        return text

    cache_key = (text, source, target)
    with _cache_lock:
        cached = _translation_cache.get(cache_key)
        if cached is not None:
            _translation_cache.move_to_end(cache_key)
            return cached

    _ensure_translation_models(source, target)

    try:
        translated_text = argos_translate.translate(text, source, target).strip()
    except Exception as error:
        raise RuntimeError(
            f"Argos Translate could not translate from '{source}' to '{target}': {error}"
        ) from error

    if not translated_text:
        raise RuntimeError("Argos Translate returned an empty translation.")

    with _cache_lock:
        _translation_cache[cache_key] = translated_text
        if len(_translation_cache) > MAX_CACHED_TRANSLATIONS:
            _translation_cache.popitem(last=False)
    return translated_text


def translate_region(
    image,
    source_language,
    target_language,
    ocr_language,
    tesseract_cmd=None,
):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    processed = ImageOps.autocontrast(ImageOps.grayscale(image))
    if max(processed.size) < 1400:
        scale = min(3, 1400 / max(processed.size))
        processed = processed.resize(
            (round(processed.width * scale), round(processed.height * scale))
        )

    original_text = pytesseract.image_to_string(processed, lang=ocr_language).strip()
    if not original_text:
        raise ValueError("No text was recognized. Select a larger or clearer region.")

    translated_text = translate_text(
        original_text,
        source_language,
        target_language,
    )
    return original_text, translated_text
