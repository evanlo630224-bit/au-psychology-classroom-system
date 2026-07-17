from __future__ import annotations

import re
import time

from deep_translator import GoogleTranslator


_CJK_PATTERN = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
)


def _cjk_ratio(text: str) -> float:
    value = text or ""
    visible = [char for char in value if not char.isspace()]
    if not visible:
        return 0.0
    cjk_count = len(_CJK_PATTERN.findall(value))
    return cjk_count / len(visible)


def _looks_translated(source: str, translated: str) -> bool:
    source_value = (source or "").strip()
    translated_value = (translated or "").strip()

    if not translated_value:
        return False
    if translated_value == source_value:
        return False

    # English translation may retain room numbers, semester codes and names,
    # but it should not remain predominantly Chinese.
    return _cjk_ratio(translated_value) < 0.20


def _translate_line(value: str) -> str:
    """Translate one non-empty line with explicit Traditional Chinese sources."""
    last_error: Exception | None = None

    # Explicit zh-TW is attempted first. Some Google Translate wrappers fail
    # silently with source="auto" and return the original Chinese unchanged.
    for source_language in ("zh-TW", "zh-CN", "auto"):
        try:
            translated = GoogleTranslator(
                source=source_language,
                target="en",
            ).translate(value)

            if _looks_translated(value, translated):
                return translated.strip()
        except Exception as exc:
            last_error = exc

        time.sleep(0.25)

    if last_error:
        raise RuntimeError(
            "The translation service did not return a valid English result."
        ) from last_error

    raise RuntimeError(
        "The translation service returned the original Chinese text."
    )


def translate_zh_to_en(text: str) -> str:
    """Translate Traditional Chinese text into validated English.

    The function translates each line separately to preserve announcement
    formatting. It rejects unchanged or predominantly Chinese output so invalid
    translations are never stored as the English version.
    """
    value = (text or "").strip()
    if not value:
        return ""

    translated_lines: list[str] = []

    for line in value.splitlines():
        stripped = line.strip()
        if not stripped:
            translated_lines.append("")
            continue
        translated_lines.append(_translate_line(stripped))

    result = "\n".join(translated_lines).strip()

    if not _looks_translated(value, result):
        raise RuntimeError(
            "English validation failed because the translated text still "
            "contains too much Chinese."
        )

    return result
