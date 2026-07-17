from __future__ import annotations

from deep_translator import GoogleTranslator


def translate_zh_to_en(text: str) -> str:
    """Translate Traditional Chinese text into English.

    The text is sent to Google Translate through deep-translator.
    """
    value = (text or "").strip()
    if not value:
        return ""

    translator = GoogleTranslator(source="auto", target="en")
    return translator.translate(value)
